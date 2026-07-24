import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.purchase.constants import PurchaseStatus
from app.modules.purchase.models import PurchaseBill, PurchaseBillItem, PurchaseSequence

_SORT_COLUMNS: dict[str, Any] = {
    "bill_date": PurchaseBill.bill_date,
    "bill_number": PurchaseBill.bill_number,
    "created_at": PurchaseBill.created_at,
}

# Bills outside these two statuses (draft, cancelled, paid) don't contribute
# to a supplier's outstanding balance - draft/cancelled were never posted,
# and paid's balance_amount is already 0 so including it wouldn't change the
# sum - but leaving it out keeps the query's intent ("still-open bills")
# explicit rather than incidental. Mirrors invoices/repository.py's
# _OPEN_INVOICE_STATUSES exactly.
_OPEN_PURCHASE_BILL_STATUSES = (PurchaseStatus.POSTED, PurchaseStatus.PARTIALLY_PAID)
_ITEM_SORT_COLUMNS: dict[str, Any] = {
    "line_number": PurchaseBillItem.line_number,
    "description": PurchaseBillItem.description,
    "created_at": PurchaseBillItem.created_at,
}


class PurchaseRepository:
    """All raw queries for the purchase module live here - services never
    build SQL (ARCHITECTURE.md §3.2)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, purchase_bill_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PurchaseBill | None:
        result = await self._session.execute(
            select(PurchaseBill).where(
                PurchaseBill.id == purchase_bill_id,
                PurchaseBill.tenant_id == tenant_id,
                PurchaseBill.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self, purchase_bill_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PurchaseBill | None:
        """Same lookup as get_by_id, but takes a row-level lock (`SELECT ...
        FOR UPDATE`) so the Session 5 posting workflow can validate-then-
        mutate without a concurrent post attempt on the same bill racing it
        (mirrors InvoiceRepository.get_by_id_for_update) - this is what
        makes double-posting impossible under concurrency, not just the
        DRAFT status check alone."""
        result = await self._session.execute(
            select(PurchaseBill)
            .where(
                PurchaseBill.id == purchase_bill_id,
                PurchaseBill.tenant_id == tenant_id,
                PurchaseBill.deleted_at.is_(None),
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
        status: PurchaseStatus | None,
        supplier_id: uuid.UUID | None,
        bill_date_from: date | None,
        bill_date_to: date | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> tuple[list[PurchaseBill], int]:
        """Filtered, sorted, paginated purchase bill list plus the total
        match count.

        `q_supplier_ids` is pre-resolved by the service (via
        SupplierService) rather than joined here - repositories never
        import another module's ORM model directly (ARCHITECTURE.md §2).
        `q` also matches this table's own bill_number column directly, the
        same hybrid approach PaymentRepository.search uses for
        payment_number + company name. Two queries (count + page), not
        N+1. Tie-broken by id in the same direction as the primary sort.
        """
        conditions = [PurchaseBill.tenant_id == tenant_id, PurchaseBill.deleted_at.is_(None)]
        if status is not None:
            conditions.append(PurchaseBill.status == status)
        if supplier_id is not None:
            conditions.append(PurchaseBill.supplier_id == supplier_id)
        if bill_date_from is not None:
            conditions.append(PurchaseBill.bill_date >= bill_date_from)
        if bill_date_to is not None:
            conditions.append(PurchaseBill.bill_date <= bill_date_to)
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            q_conditions = [PurchaseBill.bill_number.ilike(pattern)]
            if q_supplier_ids:
                q_conditions.append(PurchaseBill.supplier_id.in_(q_supplier_ids))
            conditions.append(or_(*q_conditions))

        total = (
            await self._session.execute(
                select(func.count()).select_from(PurchaseBill).where(*conditions)
            )
        ).scalar_one()

        sort_field = sort[1:] if sort.startswith("-") else sort
        column = _SORT_COLUMNS[sort_field]
        descending = sort.startswith("-")
        order = column.desc() if descending else column.asc()
        tie_break = PurchaseBill.id.desc() if descending else PurchaseBill.id.asc()

        rows = (
            (
                await self._session.execute(
                    select(PurchaseBill)
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

    async def add(self, purchase_bill: PurchaseBill) -> PurchaseBill:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits as a single, deliberate
        step."""
        self._session.add(purchase_bill)
        return purchase_bill

    async def get_item_by_id(
        self, item_id: uuid.UUID, purchase_bill_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PurchaseBillItem | None:
        """Scoped to both purchase_bill_id and tenant_id - an item id that
        exists but belongs to a different bill (or a different tenant) is
        indistinguishable from "does not exist", mirroring
        InvoiceRepository.get_item_by_id. No deleted_at filter - items are
        hard-deleted (PurchaseBillItem carries no soft-delete columns)."""
        result = await self._session.execute(
            select(PurchaseBillItem).where(
                PurchaseBillItem.id == item_id,
                PurchaseBillItem.purchase_bill_id == purchase_bill_id,
                PurchaseBillItem.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def allocate_next_line_number(
        self, purchase_bill_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> int:
        """Atomically claims the next line_number for a new item on this
        bill and advances the counter in one round trip - the UPDATE
        acquires the row lock and commits the increment together, so two
        concurrent item-adds on the same bill can never claim the same
        number, and a hard-deleted item's number is never reused (see
        PurchaseBill.next_item_line_number's docstring)."""
        result = await self._session.execute(
            update(PurchaseBill)
            .where(PurchaseBill.id == purchase_bill_id, PurchaseBill.tenant_id == tenant_id)
            .values(next_item_line_number=PurchaseBill.next_item_line_number + 1)
            .returning(PurchaseBill.next_item_line_number)
        )
        allocated_next: int = result.scalar_one()
        return allocated_next - 1

    async def search_items(
        self,
        purchase_bill_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        q: str | None,
        sort: str,
    ) -> list[PurchaseBillItem]:
        """Every item on one purchase bill, filtered by description and
        sorted per the whitelisted `sort` param - mirrors
        InvoiceRepository.search_items but with its own sort support
        (TASKS.md Session 3's explicit SORT section) since purchase items
        have no fish/trip-catch join to search across. No pagination - a
        bill's line count is small and bounded, and no deleted_at filter
        since items are hard-deleted."""
        conditions = [
            PurchaseBillItem.purchase_bill_id == purchase_bill_id,
            PurchaseBillItem.tenant_id == tenant_id,
        ]
        if q and q.strip():
            conditions.append(PurchaseBillItem.description.ilike(f"%{q.strip()}%"))

        sort_field = sort[1:] if sort.startswith("-") else sort
        column = _ITEM_SORT_COLUMNS[sort_field]
        descending = sort.startswith("-")
        order = column.desc() if descending else column.asc()
        tie_break = PurchaseBillItem.id.desc() if descending else PurchaseBillItem.id.asc()

        rows = (
            (
                await self._session.execute(
                    select(PurchaseBillItem).where(*conditions).order_by(order, tie_break)
                )
            )
            .scalars()
            .all()
        )
        return list(rows)

    async def add_item(self, item: PurchaseBillItem) -> PurchaseBillItem:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits as a single, deliberate
        step."""
        self._session.add(item)
        return item

    async def delete_item(self, item: PurchaseBillItem) -> None:
        """Hard delete - PurchaseBillItem carries no deleted_at/deleted_by
        columns (see its model docstring), unlike InvoiceItem's soft
        delete. line_number non-reuse is guaranteed by the counter on
        PurchaseBill, not by leaving the row behind."""
        await self._session.delete(item)

    async def ensure_sequence_row(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> None:
        """Guarantees a `purchase_sequences` row exists for this
        (tenant_id, prefix, fiscal_year) via `INSERT ... ON CONFLICT DO
        NOTHING` - safe against two transactions racing to allocate the
        first number of a fiscal year, unlike a plain "SELECT then INSERT
        if missing" which would deadlock/duplicate-key one of them. Must be
        followed by get_sequence_for_update in the same transaction to
        actually lock and read the row. Mirrors
        InvoiceRepository.ensure_sequence_row exactly."""
        stmt = (
            pg_insert(PurchaseSequence)
            .values(tenant_id=tenant_id, prefix=prefix, fiscal_year=fiscal_year, last_number=0)
            .on_conflict_do_nothing(index_elements=["tenant_id", "prefix", "fiscal_year"])
        )
        await self._session.execute(stmt)

    async def get_sequence_for_update(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> PurchaseSequence:
        """Locks (`SELECT ... FOR UPDATE`) the counter row for this
        (tenant_id, prefix, fiscal_year) - callers must call
        ensure_sequence_row first in the same transaction so the row is
        guaranteed to exist."""
        result = await self._session.execute(
            select(PurchaseSequence)
            .where(
                PurchaseSequence.tenant_id == tenant_id,
                PurchaseSequence.prefix == prefix,
                PurchaseSequence.fiscal_year == fiscal_year,
            )
            .with_for_update()
        )
        return result.scalar_one()

    async def sum_open_balance_by_supplier(
        self, supplier_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Decimal:
        """Sum of balance_amount across every open (see
        _OPEN_PURCHASE_BILL_STATUSES) purchase bill for one supplier - the
        source PurchaseService.recalculate_payment_totals recomputes
        Supplier.outstanding_amount from
        (app.modules.supplier_payments.domain.reconciliation.calculate_supplier_outstanding),
        never patched incrementally (TASKS.md Sprint 12 Session 4: "Never
        increment. Always recompute from source."). Mirrors
        InvoiceRepository.sum_open_balance_by_company exactly."""
        result = await self._session.execute(
            select(func.coalesce(func.sum(PurchaseBill.balance_amount), 0)).where(
                PurchaseBill.supplier_id == supplier_id,
                PurchaseBill.tenant_id == tenant_id,
                PurchaseBill.deleted_at.is_(None),
                PurchaseBill.status.in_(_OPEN_PURCHASE_BILL_STATUSES),
            )
        )
        return result.scalar_one()
