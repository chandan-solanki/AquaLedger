import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.models import Invoice, InvoiceItem, InvoiceSequence

_SORT_COLUMNS: dict[str, Any] = {
    "invoice_date": Invoice.invoice_date,
    "invoice_number": Invoice.invoice_number,
    "created_at": Invoice.created_at,
}

# Sprint 10 Session 4 outstanding engine: only ISSUED/PARTIALLY_PAID
# invoices count toward a company's outstanding_amount. PAID invoices are
# excluded too - their balance_amount is already 0 so including them
# wouldn't change the sum - but leaving them out keeps the query's intent
# ("still-open invoices") explicit rather than incidental.
_OPEN_INVOICE_STATUSES = (InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID)


class InvoiceRepository:
    """All raw queries for the invoices module live here - services never build SQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> Invoice | None:
        result = await self._session.execute(
            select(Invoice).where(
                Invoice.id == invoice_id,
                Invoice.tenant_id == tenant_id,
                Invoice.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self, invoice_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Invoice | None:
        """Same lookup as get_by_id, but takes a row-level lock (`SELECT ...
        FOR UPDATE`) so the Session 5 issue workflow can validate-then-mutate
        without a concurrent issue attempt on the same invoice racing it
        (ARCHITECTURE.md §13.3) - this is what makes double-issue
        impossible under concurrency, not just the DRAFT status check alone."""
        result = await self._session.execute(
            select(Invoice)
            .where(
                Invoice.id == invoice_id,
                Invoice.tenant_id == tenant_id,
                Invoice.deleted_at.is_(None),
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        tenant_id: uuid.UUID,
        *,
        q: str | None,
        q_company_ids: list[uuid.UUID] | None,
        status: InvoiceStatus | None,
        company_id: uuid.UUID | None,
        invoice_date_from: date | None,
        invoice_date_to: date | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> tuple[list[Invoice], int]:
        """Filtered, sorted, paginated invoice list plus the total match count.

        `q_company_ids` is pre-resolved by the service (via CompanyService)
        rather than joined here - repositories never import another module's
        ORM model directly (ARCHITECTURE.md §2). `q` also matches this
        table's own invoice_number column directly, the same hybrid approach
        trips' search uses for trip_number + boat name. Two queries (count +
        page), not N+1. Tie-broken by id *in the same direction as the
        primary sort* - two rows created in the same instant (or with equal
        created_at) would otherwise always break ascending regardless of
        whether the caller asked for `-created_at`, silently contradicting
        the requested order.
        """
        conditions = [Invoice.tenant_id == tenant_id, Invoice.deleted_at.is_(None)]
        if status is not None:
            conditions.append(Invoice.status == status)
        if company_id is not None:
            conditions.append(Invoice.company_id == company_id)
        if invoice_date_from is not None:
            conditions.append(Invoice.invoice_date >= invoice_date_from)
        if invoice_date_to is not None:
            conditions.append(Invoice.invoice_date <= invoice_date_to)
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            q_conditions = [Invoice.invoice_number.ilike(pattern)]
            if q_company_ids:
                q_conditions.append(Invoice.company_id.in_(q_company_ids))
            conditions.append(or_(*q_conditions))

        total = (
            await self._session.execute(
                select(func.count()).select_from(Invoice).where(*conditions)
            )
        ).scalar_one()

        sort_field = sort[1:] if sort.startswith("-") else sort
        column = _SORT_COLUMNS[sort_field]
        descending = sort.startswith("-")
        order = column.desc() if descending else column.asc()
        tie_break = Invoice.id.desc() if descending else Invoice.id.asc()

        rows = (
            (
                await self._session.execute(
                    select(Invoice)
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

    async def add(self, invoice: Invoice) -> Invoice:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits as a single, deliberate
        step."""
        self._session.add(invoice)
        return invoice

    async def sum_open_balance_by_company(
        self, company_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Decimal:
        """Sum of balance_amount across every open (see
        _OPEN_INVOICE_STATUSES) invoice for one company - the source
        InvoiceService.recalculate_payment_totals recomputes
        Company.outstanding_amount from
        (app.modules.payments.domain.reconciliation.calculate_company_outstanding),
        never patched incrementally (TASKS.md Sprint 10 Session 4: "Do NOT
        increment/decrement. Recompute.")."""
        result = await self._session.execute(
            select(func.coalesce(func.sum(Invoice.balance_amount), 0)).where(
                Invoice.company_id == company_id,
                Invoice.tenant_id == tenant_id,
                Invoice.deleted_at.is_(None),
                Invoice.status.in_(_OPEN_INVOICE_STATUSES),
            )
        )
        return result.scalar_one()

    async def get_item_by_id(
        self, item_id: uuid.UUID, invoice_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> InvoiceItem | None:
        """Scoped to both invoice_id and tenant_id - an item id that exists
        but belongs to a different invoice (or a different tenant) is
        indistinguishable from "does not exist", the same tenant-isolation
        rule every other get_by_id in this codebase follows."""
        result = await self._session.execute(
            select(InvoiceItem).where(
                InvoiceItem.id == item_id,
                InvoiceItem.invoice_id == invoice_id,
                InvoiceItem.tenant_id == tenant_id,
                InvoiceItem.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def next_line_number(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> int:
        """Next line_number for a new item on this invoice. Not filtered by
        deleted_at, so numbers are monotonically increasing and never
        reused - the same gap-tolerant philosophy ARCHITECTURE.md §13.1
        applies to invoice_number sequences."""
        result = await self._session.execute(
            select(func.coalesce(func.max(InvoiceItem.line_number), 0)).where(
                InvoiceItem.invoice_id == invoice_id,
                InvoiceItem.tenant_id == tenant_id,
            )
        )
        return result.scalar_one() + 1

    async def search_items(
        self,
        invoice_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        q: str | None,
        q_fish_ids: list[uuid.UUID] | None,
    ) -> list[InvoiceItem]:
        """Every non-deleted item on one invoice, ordered by line_number.

        `q_fish_ids` is pre-resolved by the service (via FishService) rather
        than joined here - repositories never import another module's ORM
        model directly (ARCHITECTURE.md §2). `q` also matches this table's
        own description column directly, the same hybrid approach trips'
        search uses for trip_number + boat name. No pagination - an
        invoice's line count is small and bounded, unlike the top-level
        invoice list.
        """
        conditions = [
            InvoiceItem.invoice_id == invoice_id,
            InvoiceItem.tenant_id == tenant_id,
            InvoiceItem.deleted_at.is_(None),
        ]
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            q_conditions = [InvoiceItem.description.ilike(pattern)]
            if q_fish_ids:
                q_conditions.append(InvoiceItem.fish_id.in_(q_fish_ids))
            conditions.append(or_(*q_conditions))

        rows = (
            (
                await self._session.execute(
                    select(InvoiceItem).where(*conditions).order_by(InvoiceItem.line_number.asc())
                )
            )
            .scalars()
            .all()
        )
        return list(rows)

    async def add_item(self, item: InvoiceItem) -> InvoiceItem:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits as a single, deliberate
        step."""
        self._session.add(item)
        return item

    async def ensure_sequence_row(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> None:
        """Guarantees an `invoice_sequences` row exists for this
        (tenant_id, prefix, fiscal_year) via `INSERT ... ON CONFLICT DO
        NOTHING` - safe against two transactions racing to allocate the
        first number of a fiscal year, unlike a plain "SELECT then INSERT
        if missing" which would deadlock/duplicate-key one of them. Must be
        followed by get_sequence_for_update in the same transaction to
        actually lock and read the row."""
        stmt = (
            pg_insert(InvoiceSequence)
            .values(tenant_id=tenant_id, prefix=prefix, fiscal_year=fiscal_year, last_number=0)
            .on_conflict_do_nothing(index_elements=["tenant_id", "prefix", "fiscal_year"])
        )
        await self._session.execute(stmt)

    async def get_sequence_for_update(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> InvoiceSequence:
        """Locks (`SELECT ... FOR UPDATE`) the counter row for this (tenant_id,
        prefix, fiscal_year) - callers must call ensure_sequence_row first in
        the same transaction so the row is guaranteed to exist."""
        result = await self._session.execute(
            select(InvoiceSequence)
            .where(
                InvoiceSequence.tenant_id == tenant_id,
                InvoiceSequence.prefix == prefix,
                InvoiceSequence.fiscal_year == fiscal_year,
            )
            .with_for_update()
        )
        return result.scalar_one()
