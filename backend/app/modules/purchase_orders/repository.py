import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.purchase_orders.constants import PurchaseOrderStatus
from app.modules.purchase_orders.models import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderSequence,
)

_SORT_COLUMNS: dict[str, Any] = {
    "order_date": PurchaseOrder.order_date,
    "po_number": PurchaseOrder.po_number,
    "created_at": PurchaseOrder.created_at,
}
_ITEM_SORT_COLUMNS: dict[str, Any] = {
    "line_number": PurchaseOrderItem.line_number,
    "description": PurchaseOrderItem.description,
    "created_at": PurchaseOrderItem.created_at,
}


class PurchaseOrderRepository:
    """All raw queries for the purchase_orders module live here - services
    never build SQL (ARCHITECTURE.md §3.2). Unlike PurchaseRepository, there
    is no outstanding-balance query: a purchase order never contributes to
    Supplier.outstanding_amount, so there is nothing to sum."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, purchase_order_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PurchaseOrder | None:
        result = await self._session.execute(
            select(PurchaseOrder).where(
                PurchaseOrder.id == purchase_order_id,
                PurchaseOrder.tenant_id == tenant_id,
                PurchaseOrder.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self, purchase_order_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PurchaseOrder | None:
        """Same lookup as get_by_id, but takes a row-level lock (`SELECT ...
        FOR UPDATE`) so confirm/cancel/fulfill can validate-then-mutate
        without a concurrent transition on the same order racing it -
        mirrors PurchaseRepository.get_by_id_for_update."""
        result = await self._session.execute(
            select(PurchaseOrder)
            .where(
                PurchaseOrder.id == purchase_order_id,
                PurchaseOrder.tenant_id == tenant_id,
                PurchaseOrder.deleted_at.is_(None),
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        tenant_id: uuid.UUID,
        *,
        q: str | None,
        q_supplier_ids: list[uuid.UUID] | None,
        status: PurchaseOrderStatus | None,
        supplier_id: uuid.UUID | None,
        billable: bool | None = None,
        order_date_from: date | None,
        order_date_to: date | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> tuple[list[PurchaseOrder], int]:
        """Filtered, sorted, paginated purchase order list plus the total
        match count.

        `q_supplier_ids` is pre-resolved by the service (via
        SupplierService) rather than joined here - repositories never
        import another module's ORM model directly (ARCHITECTURE.md §2).
        `q` also matches this table's own po_number column directly, the
        same hybrid approach PurchaseRepository.search uses. Two queries
        (count + page), not N+1. Tie-broken by id in the same direction as
        the primary sort.

        `billable=True` restricts to CONFIRMED/FULFILLED - the set eligible
        for Purchase Bill linkage (mirrors PurchaseService's own
        `_validate_purchase_order_link` billable check) - so a PO picker can
        filter server-side instead of fetching a page and filtering it in
        the browser.
        """
        conditions = [PurchaseOrder.tenant_id == tenant_id, PurchaseOrder.deleted_at.is_(None)]
        if status is not None:
            conditions.append(PurchaseOrder.status == status)
        if supplier_id is not None:
            conditions.append(PurchaseOrder.supplier_id == supplier_id)
        if billable:
            conditions.append(
                PurchaseOrder.status.in_(
                    (PurchaseOrderStatus.CONFIRMED, PurchaseOrderStatus.FULFILLED)
                )
            )
        if order_date_from is not None:
            conditions.append(PurchaseOrder.order_date >= order_date_from)
        if order_date_to is not None:
            conditions.append(PurchaseOrder.order_date <= order_date_to)
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            q_conditions = [PurchaseOrder.po_number.ilike(pattern)]
            if q_supplier_ids:
                q_conditions.append(PurchaseOrder.supplier_id.in_(q_supplier_ids))
            conditions.append(or_(*q_conditions))

        total = (
            await self._session.execute(
                select(func.count()).select_from(PurchaseOrder).where(*conditions)
            )
        ).scalar_one()

        sort_field = sort[1:] if sort.startswith("-") else sort
        column = _SORT_COLUMNS[sort_field]
        descending = sort.startswith("-")
        order = column.desc() if descending else column.asc()
        tie_break = PurchaseOrder.id.desc() if descending else PurchaseOrder.id.asc()

        rows = (
            (
                await self._session.execute(
                    select(PurchaseOrder)
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

    async def add(self, purchase_order: PurchaseOrder) -> PurchaseOrder:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits as a single, deliberate
        step."""
        self._session.add(purchase_order)
        return purchase_order

    async def get_item_by_id(
        self, item_id: uuid.UUID, purchase_order_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PurchaseOrderItem | None:
        """Scoped to both purchase_order_id and tenant_id - an item id that
        exists but belongs to a different order (or a different tenant) is
        indistinguishable from "does not exist". No deleted_at filter -
        items are hard-deleted (PurchaseOrderItem carries no soft-delete
        columns)."""
        result = await self._session.execute(
            select(PurchaseOrderItem).where(
                PurchaseOrderItem.id == item_id,
                PurchaseOrderItem.purchase_order_id == purchase_order_id,
                PurchaseOrderItem.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def allocate_next_line_number(
        self, purchase_order_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> int:
        """Atomically claims the next line_number for a new item on this
        order and advances the counter in one round trip - the UPDATE
        acquires the row lock and commits the increment together, so two
        concurrent item-adds on the same order can never claim the same
        number, and a hard-deleted item's number is never reused."""
        result = await self._session.execute(
            update(PurchaseOrder)
            .where(PurchaseOrder.id == purchase_order_id, PurchaseOrder.tenant_id == tenant_id)
            .values(next_item_line_number=PurchaseOrder.next_item_line_number + 1)
            .returning(PurchaseOrder.next_item_line_number)
        )
        allocated_next: int = result.scalar_one()
        return allocated_next - 1

    async def search_items(
        self,
        purchase_order_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        q: str | None,
        sort: str,
    ) -> list[PurchaseOrderItem]:
        """Every item on one purchase order, filtered by description and
        sorted per the whitelisted `sort` param. No pagination - an order's
        line count is small and bounded, and no deleted_at filter since
        items are hard-deleted."""
        conditions = [
            PurchaseOrderItem.purchase_order_id == purchase_order_id,
            PurchaseOrderItem.tenant_id == tenant_id,
        ]
        if q and q.strip():
            conditions.append(PurchaseOrderItem.description.ilike(f"%{q.strip()}%"))

        sort_field = sort[1:] if sort.startswith("-") else sort
        column = _ITEM_SORT_COLUMNS[sort_field]
        descending = sort.startswith("-")
        order = column.desc() if descending else column.asc()
        tie_break = PurchaseOrderItem.id.desc() if descending else PurchaseOrderItem.id.asc()

        rows = (
            (
                await self._session.execute(
                    select(PurchaseOrderItem).where(*conditions).order_by(order, tie_break)
                )
            )
            .scalars()
            .all()
        )
        return list(rows)

    async def add_item(self, item: PurchaseOrderItem) -> PurchaseOrderItem:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits as a single, deliberate
        step."""
        self._session.add(item)
        return item

    async def delete_item(self, item: PurchaseOrderItem) -> None:
        """Hard delete - PurchaseOrderItem carries no deleted_at/deleted_by
        columns. line_number non-reuse is guaranteed by the counter on
        PurchaseOrder, not by leaving the row behind."""
        await self._session.delete(item)

    async def ensure_sequence_row(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> None:
        """Guarantees a `purchase_order_sequences` row exists for this
        (tenant_id, prefix, fiscal_year) via `INSERT ... ON CONFLICT DO
        NOTHING` - safe against two transactions racing to allocate the
        first number of a fiscal year. Must be followed by
        get_sequence_for_update in the same transaction to actually lock
        and read the row. Mirrors PurchaseRepository.ensure_sequence_row
        exactly."""
        stmt = (
            pg_insert(PurchaseOrderSequence)
            .values(tenant_id=tenant_id, prefix=prefix, fiscal_year=fiscal_year, last_number=0)
            .on_conflict_do_nothing(index_elements=["tenant_id", "prefix", "fiscal_year"])
        )
        await self._session.execute(stmt)

    async def get_sequence_for_update(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> PurchaseOrderSequence:
        """Locks (`SELECT ... FOR UPDATE`) the counter row for this
        (tenant_id, prefix, fiscal_year) - callers must call
        ensure_sequence_row first in the same transaction so the row is
        guaranteed to exist."""
        result = await self._session.execute(
            select(PurchaseOrderSequence)
            .where(
                PurchaseOrderSequence.tenant_id == tenant_id,
                PurchaseOrderSequence.prefix == prefix,
                PurchaseOrderSequence.fiscal_year == fiscal_year,
            )
            .with_for_update()
        )
        return result.scalar_one()
