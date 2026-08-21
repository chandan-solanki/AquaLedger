import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import Row, case, func, or_, select
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

# Sprint 15 Session 6: every status that can plausibly explain a stock
# conflict - a DRAFT that merely references the catch, or an
# ISSUED/PARTIALLY_PAID/PAID invoice that has already consumed it.
# CANCELLED is deliberately excluded - TASKS.md: "Cancelled invoices must
# never be presented as active conflicts."
_CONFLICT_INVOICE_STATUSES = (
    InvoiceStatus.DRAFT,
    InvoiceStatus.ISSUED,
    InvoiceStatus.PARTIALLY_PAID,
    InvoiceStatus.PAID,
)


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

    async def sum_other_draft_quantity(
        self,
        trip_catch_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        exclude_invoice_id: uuid.UUID | None,
    ) -> Decimal:
        """Sprint 15 Session 5: sum of `quantity` across every OTHER tenant's
        DRAFT invoice item referencing this trip catch - the "other draft
        demand" a competing draft could still claim before this one is
        issued. One aggregate query, mirroring
        `TripCatchRepository.aggregate_stock_by_fish`'s style
        (`app/modules/trip_catches/repository.py`), not a per-invoice loop.

        Status lives on `Invoice`, not `InvoiceItem`, so this must join -
        unlike every other query in this file, which reads `InvoiceItem`
        alone. `Invoice.deleted_at.is_(None)` is required in addition to
        `status == DRAFT`: deleting an invoice only sets `deleted_at`, it
        never flips `status`, so a soft-deleted draft's items would
        otherwise still count (see `Invoice`/`InvoiceItem` model docstrings).
        `exclude_invoice_id` is the invoice currently being viewed/edited -
        its own items are demand from THIS invoice, not "other" demand, and
        must never be counted here regardless of which specific item is
        being added or edited (Sprint 15 Session 5 TASKS.md: exclusion is by
        invoice, not by item)."""
        conditions = [
            InvoiceItem.trip_catch_id == trip_catch_id,
            InvoiceItem.tenant_id == tenant_id,
            InvoiceItem.deleted_at.is_(None),
            Invoice.status == InvoiceStatus.DRAFT,
            Invoice.deleted_at.is_(None),
        ]
        if exclude_invoice_id is not None:
            conditions.append(Invoice.id != exclude_invoice_id)

        result = await self._session.execute(
            select(func.coalesce(func.sum(InvoiceItem.quantity), 0))
            .select_from(InvoiceItem)
            .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
            .where(*conditions)
        )
        return result.scalar_one()

    async def list_invoices_referencing_trip_catch(
        self,
        trip_catch_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        exclude_invoice_id: uuid.UUID | None,
    ) -> Sequence[Row[Any]]:
        """Sprint 15 Session 6: every OTHER non-cancelled, non-deleted
        invoice referencing this trip catch, one row per invoice (not per
        item - an invoice with two items against the same catch would
        otherwise appear twice with a misleadingly split quantity). Unlike
        `sum_other_draft_quantity` (a scalar aggregate that deliberately
        throws away row identity), this returns each invoice's own id/
        number/status/date/company_id/quantity - a genuinely different
        query shape, not a parameter tweak to the same one.

        Ordered with actual stock consumers (ISSUED/PARTIALLY_PAID/PAID)
        before pending DRAFTs, most recent first within each group - the
        UI wants to show "what likely consumed this stock" ahead of "what
        else merely wants it." `company_id` is returned, not a name -
        resolving names in bulk is CompanyService's job (ARCHITECTURE.md
        §2), avoiding an N+1 here."""
        conditions = [
            InvoiceItem.trip_catch_id == trip_catch_id,
            InvoiceItem.tenant_id == tenant_id,
            InvoiceItem.deleted_at.is_(None),
            Invoice.status.in_(_CONFLICT_INVOICE_STATUSES),
            Invoice.deleted_at.is_(None),
        ]
        if exclude_invoice_id is not None:
            conditions.append(Invoice.id != exclude_invoice_id)

        is_draft = case((Invoice.status == InvoiceStatus.DRAFT, 1), else_=0)

        result = await self._session.execute(
            select(
                Invoice.id,
                Invoice.invoice_number,
                Invoice.status,
                Invoice.invoice_date,
                Invoice.company_id,
                func.sum(InvoiceItem.quantity).label("quantity"),
            )
            .select_from(InvoiceItem)
            .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
            .where(*conditions)
            .group_by(
                Invoice.id,
                Invoice.invoice_number,
                Invoice.status,
                Invoice.invoice_date,
                Invoice.company_id,
            )
            .order_by(is_draft.asc(), Invoice.invoice_date.desc())
        )
        return result.all()

    async def get_trip_catch_invoice_usage(
        self,
        trip_catch_ids: Sequence[uuid.UUID],
        tenant_id: uuid.UUID,
        *,
        exclude_invoice_id: uuid.UUID | None = None,
    ) -> Sequence[Row[Any]]:
        """Sprint 15 Session 7: batched invoice-usage summary for the Fish
        Stock detail page's Contributing Catches table - one query for every
        trip catch shown on that page, never one request per row (N+1).
        Returns a row only for a trip catch with at least one qualifying
        invoice; a trip catch absent from the result has zero usage - the
        same "missing means none" contract FishService.get_many_by_ids and
        CompanyService.get_names_by_ids already use for bulk lookups, so
        callers must not treat an absent id as an error.

        Same status/soft-delete filtering as
        list_invoices_referencing_trip_catch (_CONFLICT_INVOICE_STATUSES,
        excluding CANCELLED and soft-deleted), but grouped by trip_catch_id
        rather than by invoice - the Fish Stock page only needs a count and
        two quantity totals per catch, never per-invoice identity, so this
        is a distinct aggregate query, not a variation of that one.
        `invoice_count` counts distinct invoices (not items) - an invoice
        with two items against the same catch must still count once.

        `exclude_invoice_id` (Sprint 15 Session 8): when given, that
        invoice's own items are excluded from every count/sum entirely -
        reused by InvoiceService.get_invoice_trip_catch_conflicts so the
        Invoice Detail page's "Other Invoice Usage" indicator never counts
        the invoice being viewed as its own conflict. Session 7's Fish Stock
        callers never pass this, leaving their behavior unchanged."""
        if not trip_catch_ids:
            return []

        conditions = [
            InvoiceItem.trip_catch_id.in_(trip_catch_ids),
            InvoiceItem.tenant_id == tenant_id,
            InvoiceItem.deleted_at.is_(None),
            Invoice.status.in_(_CONFLICT_INVOICE_STATUSES),
            Invoice.deleted_at.is_(None),
        ]
        if exclude_invoice_id is not None:
            conditions.append(Invoice.id != exclude_invoice_id)

        result = await self._session.execute(
            select(
                InvoiceItem.trip_catch_id,
                func.count(func.distinct(Invoice.id)).label("invoice_count"),
                func.coalesce(
                    func.sum(
                        case(
                            (Invoice.status == InvoiceStatus.DRAFT, InvoiceItem.quantity),
                            else_=0,
                        )
                    ),
                    0,
                ).label("draft_quantity"),
                func.coalesce(
                    func.sum(
                        case(
                            (Invoice.status != InvoiceStatus.DRAFT, InvoiceItem.quantity),
                            else_=0,
                        )
                    ),
                    0,
                ).label("consumed_quantity"),
            )
            .select_from(InvoiceItem)
            .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
            .where(*conditions)
            .group_by(InvoiceItem.trip_catch_id)
        )
        return result.all()

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
