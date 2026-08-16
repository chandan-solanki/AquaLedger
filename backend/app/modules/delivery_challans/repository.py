import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.delivery_challans.constants import DeliveryChallanStatus
from app.modules.delivery_challans.models import (
    DeliveryChallan,
    DeliveryChallanItem,
    DeliveryChallanSequence,
)

_SORT_COLUMNS: dict[str, Any] = {
    "challan_date": DeliveryChallan.challan_date,
    "challan_number": DeliveryChallan.challan_number,
    "created_at": DeliveryChallan.created_at,
}
_ITEM_SORT_COLUMNS: dict[str, Any] = {
    "line_number": DeliveryChallanItem.line_number,
    "created_at": DeliveryChallanItem.created_at,
}


class DeliveryChallanRepository:
    """All raw queries for the delivery_challans module live here - services
    never build SQL (ARCHITECTURE.md §3.2). There is no outstanding-balance
    query and no financial aggregation of any kind: a delivery challan never
    contributes to Company.outstanding_amount or Invoice.balance_amount, so
    there is nothing to sum on that front."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, delivery_challan_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> DeliveryChallan | None:
        result = await self._session.execute(
            select(DeliveryChallan).where(
                DeliveryChallan.id == delivery_challan_id,
                DeliveryChallan.tenant_id == tenant_id,
                DeliveryChallan.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self, delivery_challan_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> DeliveryChallan | None:
        """Same lookup as get_by_id, but takes a row-level lock (`SELECT ...
        FOR UPDATE`) so dispatch/deliver/cancel can validate-then-mutate
        without a concurrent transition on the same challan racing it -
        mirrors PurchaseOrderRepository.get_by_id_for_update."""
        result = await self._session.execute(
            select(DeliveryChallan)
            .where(
                DeliveryChallan.id == delivery_challan_id,
                DeliveryChallan.tenant_id == tenant_id,
                DeliveryChallan.deleted_at.is_(None),
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        tenant_id: uuid.UUID,
        *,
        q: str | None,
        status: DeliveryChallanStatus | None,
        invoice_id: uuid.UUID | None,
        challan_date_from: date | None,
        challan_date_to: date | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> tuple[list[DeliveryChallan], int]:
        """Filtered, sorted, paginated delivery challan list plus the total
        match count. Two queries (count + page), not N+1. Tie-broken by id
        in the same direction as the primary sort. Unlike
        PurchaseOrderRepository.search, `q` only ever matches this table's
        own challan_number column - there is no company/customer column on
        this table to search (see DeliveryChallan's own docstring)."""
        conditions = [
            DeliveryChallan.tenant_id == tenant_id,
            DeliveryChallan.deleted_at.is_(None),
        ]
        if status is not None:
            conditions.append(DeliveryChallan.status == status)
        if invoice_id is not None:
            conditions.append(DeliveryChallan.invoice_id == invoice_id)
        if challan_date_from is not None:
            conditions.append(DeliveryChallan.challan_date >= challan_date_from)
        if challan_date_to is not None:
            conditions.append(DeliveryChallan.challan_date <= challan_date_to)
        if q and q.strip():
            conditions.append(DeliveryChallan.challan_number.ilike(f"%{q.strip()}%"))

        total = (
            await self._session.execute(
                select(func.count()).select_from(DeliveryChallan).where(*conditions)
            )
        ).scalar_one()

        sort_field = sort[1:] if sort.startswith("-") else sort
        column = _SORT_COLUMNS[sort_field]
        descending = sort.startswith("-")
        order = column.desc() if descending else column.asc()
        tie_break = DeliveryChallan.id.desc() if descending else DeliveryChallan.id.asc()

        rows = (
            (
                await self._session.execute(
                    select(DeliveryChallan)
                    .where(*conditions)
                    .order_by(order, tie_break)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def add(self, delivery_challan: DeliveryChallan) -> DeliveryChallan:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits as a single, deliberate
        step."""
        self._session.add(delivery_challan)
        return delivery_challan

    async def get_item_by_id(
        self, item_id: uuid.UUID, delivery_challan_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> DeliveryChallanItem | None:
        """Scoped to both delivery_challan_id and tenant_id - an item id
        that exists but belongs to a different challan (or a different
        tenant) is indistinguishable from "does not exist"."""
        result = await self._session.execute(
            select(DeliveryChallanItem).where(
                DeliveryChallanItem.id == item_id,
                DeliveryChallanItem.delivery_challan_id == delivery_challan_id,
                DeliveryChallanItem.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def allocate_next_line_number(
        self, delivery_challan_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> int:
        """Atomically claims the next line_number for a new item on this
        challan and advances the counter in one round trip - the UPDATE
        acquires the row lock and commits the increment together, so two
        concurrent item-adds on the same challan can never claim the same
        number, and a hard-deleted item's number is never reused."""
        result = await self._session.execute(
            update(DeliveryChallan)
            .where(
                DeliveryChallan.id == delivery_challan_id,
                DeliveryChallan.tenant_id == tenant_id,
            )
            .values(next_item_line_number=DeliveryChallan.next_item_line_number + 1)
            .returning(DeliveryChallan.next_item_line_number)
        )
        allocated_next: int = result.scalar_one()
        return allocated_next - 1

    async def search_items(
        self, delivery_challan_id: uuid.UUID, tenant_id: uuid.UUID, *, sort: str
    ) -> list[DeliveryChallanItem]:
        """Every item on one delivery challan, sorted per the whitelisted
        `sort` param. No pagination - a challan's line count is small and
        bounded, and no deleted_at filter since items are hard-deleted."""
        conditions = [
            DeliveryChallanItem.delivery_challan_id == delivery_challan_id,
            DeliveryChallanItem.tenant_id == tenant_id,
        ]

        sort_field = sort[1:] if sort.startswith("-") else sort
        column = _ITEM_SORT_COLUMNS[sort_field]
        descending = sort.startswith("-")
        order = column.desc() if descending else column.asc()
        tie_break = DeliveryChallanItem.id.desc() if descending else DeliveryChallanItem.id.asc()

        rows = (
            (
                await self._session.execute(
                    select(DeliveryChallanItem).where(*conditions).order_by(order, tie_break)
                )
            )
            .scalars()
            .all()
        )
        return list(rows)

    async def add_item(self, item: DeliveryChallanItem) -> DeliveryChallanItem:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits as a single, deliberate
        step."""
        self._session.add(item)
        return item

    async def delete_item(self, item: DeliveryChallanItem) -> None:
        """Hard delete - DeliveryChallanItem carries no deleted_at/deleted_by
        columns. line_number non-reuse is guaranteed by the counter on
        DeliveryChallan, not by leaving the row behind."""
        await self._session.delete(item)

    async def ensure_sequence_row(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> None:
        """Guarantees a `delivery_challan_sequences` row exists for this
        (tenant_id, prefix, fiscal_year) via `INSERT ... ON CONFLICT DO
        NOTHING` - safe against two transactions racing to allocate the
        first number of a fiscal year. Must be followed by
        get_sequence_for_update in the same transaction to actually lock and
        read the row. Mirrors PurchaseOrderRepository.ensure_sequence_row
        exactly."""
        stmt = (
            pg_insert(DeliveryChallanSequence)
            .values(tenant_id=tenant_id, prefix=prefix, fiscal_year=fiscal_year, last_number=0)
            .on_conflict_do_nothing(index_elements=["tenant_id", "prefix", "fiscal_year"])
        )
        await self._session.execute(stmt)

    async def get_sequence_for_update(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> DeliveryChallanSequence:
        """Locks (`SELECT ... FOR UPDATE`) the counter row for this
        (tenant_id, prefix, fiscal_year) - callers must call
        ensure_sequence_row first in the same transaction so the row is
        guaranteed to exist."""
        result = await self._session.execute(
            select(DeliveryChallanSequence)
            .where(
                DeliveryChallanSequence.tenant_id == tenant_id,
                DeliveryChallanSequence.prefix == prefix,
                DeliveryChallanSequence.fiscal_year == fiscal_year,
            )
            .with_for_update()
        )
        return result.scalar_one()

    async def sum_delivered_quantity_for_invoice_item(
        self,
        invoice_item_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        exclude_item_id: uuid.UUID | None = None,
    ) -> Decimal:
        """Total quantity already delivered against one invoice item, across
        every valid (non-deleted-challan, non-CANCELLED-challan)
        DeliveryChallanItem that references it - the single-item form used
        by DeliveryChallanService's over-delivery check in add_item/
        update_item. `exclude_item_id` lets update_item exclude the item's
        own prior contribution before comparing against its proposed new
        quantity. Deliberately includes DRAFT challans' items, not just
        DISPATCHED/DELIVERED ones - mirrors
        PurchaseRepository.sum_billed_quantity_for_po_item's own reservation
        model exactly (immediate, at-entry-time over-delivery feedback
        rather than a race that only surfaces at dispatch time)."""
        conditions = [
            DeliveryChallanItem.invoice_item_id == invoice_item_id,
            DeliveryChallanItem.tenant_id == tenant_id,
            DeliveryChallan.deleted_at.is_(None),
            DeliveryChallan.status != DeliveryChallanStatus.CANCELLED,
        ]
        if exclude_item_id is not None:
            conditions.append(DeliveryChallanItem.id != exclude_item_id)
        result = await self._session.execute(
            select(func.coalesce(func.sum(DeliveryChallanItem.quantity), 0))
            .select_from(DeliveryChallanItem)
            .join(DeliveryChallan, DeliveryChallan.id == DeliveryChallanItem.delivery_challan_id)
            .where(*conditions)
        )
        return result.scalar_one()

    async def sum_delivered_by_invoice_items(
        self, invoice_item_ids: list[uuid.UUID], tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, Decimal]:
        """Batched form of the same aggregation - one query for an entire
        invoice's items regardless of how many there are (no N+1), `GROUP BY
        invoice_item_id`. Mirrors
        PurchaseRepository.sum_billed_by_po_items exactly. Items with
        nothing delivered at all are simply absent from the returned dict."""
        if not invoice_item_ids:
            return {}
        rows = (
            await self._session.execute(
                select(
                    DeliveryChallanItem.invoice_item_id,
                    func.coalesce(func.sum(DeliveryChallanItem.quantity), 0),
                )
                .select_from(DeliveryChallanItem)
                .join(
                    DeliveryChallan,
                    DeliveryChallan.id == DeliveryChallanItem.delivery_challan_id,
                )
                .where(
                    DeliveryChallanItem.invoice_item_id.in_(invoice_item_ids),
                    DeliveryChallanItem.tenant_id == tenant_id,
                    DeliveryChallan.deleted_at.is_(None),
                    DeliveryChallan.status != DeliveryChallanStatus.CANCELLED,
                )
                .group_by(DeliveryChallanItem.invoice_item_id)
            )
        ).all()
        return {invoice_item_id: delivered for invoice_item_id, delivered in rows}  # noqa: C416
