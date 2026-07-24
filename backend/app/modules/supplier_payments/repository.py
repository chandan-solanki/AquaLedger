import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.supplier_payments.constants import PaymentMethod, SupplierPaymentStatus
from app.modules.supplier_payments.models import (
    SupplierPayment,
    SupplierPaymentAllocation,
    SupplierPaymentSequence,
)

_SORT_COLUMNS: dict[str, Any] = {
    "payment_date": SupplierPayment.payment_date,
    "payment_number": SupplierPayment.payment_number,
    "created_at": SupplierPayment.created_at,
}


class SupplierPaymentRepository:
    """All raw queries for the supplier_payments module live here - services
    never build SQL (ARCHITECTURE.md §3.2).

    Sprint 12 Session 2 - draft CRUD queries; Session 3 - allocation
    queries; Session 4 - outstanding-reconciliation aggregation; Session 5 -
    numbering/posting queries (TASKS.md), mirroring PaymentRepository's own
    session-by-session shape throughout.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, supplier_payment_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> SupplierPayment | None:
        result = await self._session.execute(
            select(SupplierPayment).where(
                SupplierPayment.id == supplier_payment_id,
                SupplierPayment.tenant_id == tenant_id,
                SupplierPayment.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self, supplier_payment_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> SupplierPayment | None:
        """Same lookup as get_by_id, but takes a row-level lock (`SELECT ...
        FOR UPDATE`) so the Session 5 posting workflow can validate-then-
        mutate without a concurrent post attempt on the same payment racing
        it (ARCHITECTURE.md §13.3, mirroring
        PaymentRepository.get_by_id_for_update) - this is what makes
        double-posting impossible under concurrency, not just the DRAFT
        status check alone."""
        result = await self._session.execute(
            select(SupplierPayment)
            .where(
                SupplierPayment.id == supplier_payment_id,
                SupplierPayment.tenant_id == tenant_id,
                SupplierPayment.deleted_at.is_(None),
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
        status: SupplierPaymentStatus | None,
        supplier_id: uuid.UUID | None,
        payment_method: PaymentMethod | None,
        payment_date_from: date | None,
        payment_date_to: date | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> tuple[list[SupplierPayment], int]:
        """Filtered, sorted, paginated supplier payment list plus the total
        match count.

        `q_supplier_ids` is pre-resolved by the service (via SupplierService)
        rather than joined here - repositories never import another
        module's ORM model directly (ARCHITECTURE.md §2). `q` also matches
        this table's own payment_number/reference_number columns directly,
        the same hybrid approach PaymentRepository.search/
        PurchaseRepository.search use for their own number + name pairs.
        Two queries (count + page), not N+1. Tie-broken by id in the same
        direction as the primary sort.
        """
        conditions = [
            SupplierPayment.tenant_id == tenant_id,
            SupplierPayment.deleted_at.is_(None),
        ]
        if status is not None:
            conditions.append(SupplierPayment.status == status)
        if supplier_id is not None:
            conditions.append(SupplierPayment.supplier_id == supplier_id)
        if payment_method is not None:
            conditions.append(SupplierPayment.payment_method == payment_method)
        if payment_date_from is not None:
            conditions.append(SupplierPayment.payment_date >= payment_date_from)
        if payment_date_to is not None:
            conditions.append(SupplierPayment.payment_date <= payment_date_to)
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            q_conditions = [
                SupplierPayment.payment_number.ilike(pattern),
                SupplierPayment.reference_number.ilike(pattern),
            ]
            if q_supplier_ids:
                q_conditions.append(SupplierPayment.supplier_id.in_(q_supplier_ids))
            conditions.append(or_(*q_conditions))

        total = (
            await self._session.execute(
                select(func.count()).select_from(SupplierPayment).where(*conditions)
            )
        ).scalar_one()

        sort_field = sort[1:] if sort.startswith("-") else sort
        column = _SORT_COLUMNS[sort_field]
        descending = sort.startswith("-")
        order = column.desc() if descending else column.asc()
        tie_break = SupplierPayment.id.desc() if descending else SupplierPayment.id.asc()

        rows = (
            (
                await self._session.execute(
                    select(SupplierPayment)
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

    async def add(self, supplier_payment: SupplierPayment) -> SupplierPayment:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits as a single, deliberate
        step."""
        self._session.add(supplier_payment)
        return supplier_payment

    async def get_allocation_by_id(
        self, allocation_id: uuid.UUID, supplier_payment_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> SupplierPaymentAllocation | None:
        """Scoped to both supplier_payment_id and tenant_id - an allocation
        id that exists but belongs to a different payment (or a different
        tenant) is indistinguishable from "does not exist", mirroring
        PaymentRepository.get_allocation_by_id."""
        result = await self._session.execute(
            select(SupplierPaymentAllocation).where(
                SupplierPaymentAllocation.id == allocation_id,
                SupplierPaymentAllocation.supplier_payment_id == supplier_payment_id,
                SupplierPaymentAllocation.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_allocations(
        self, supplier_payment_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[SupplierPaymentAllocation]:
        """Every allocation on one supplier payment, oldest first - no
        soft-delete filter, SupplierPaymentAllocation is append-only/
        hard-deleted (see its own docstring), unlike SupplierPayment
        itself."""
        rows = (
            (
                await self._session.execute(
                    select(SupplierPaymentAllocation)
                    .where(
                        SupplierPaymentAllocation.supplier_payment_id == supplier_payment_id,
                        SupplierPaymentAllocation.tenant_id == tenant_id,
                    )
                    .order_by(SupplierPaymentAllocation.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        return list(rows)

    async def add_allocation(
        self, allocation: SupplierPaymentAllocation
    ) -> SupplierPaymentAllocation:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits as a single, deliberate
        step."""
        self._session.add(allocation)
        return allocation

    async def delete_allocation(self, allocation: SupplierPaymentAllocation) -> None:
        """Hard delete, not soft: SupplierPaymentAllocation carries no
        deleted_at - removing an allocation from a still-DRAFT (unposted)
        payment is undoing a draft-state association, not erasing a posted
        financial event, so there's nothing here for CLAUDE.md's "ledger
        entries are append-only" rule to protect yet. That protection
        begins at posting (a future session), once an allocation has
        actually affected a purchase bill's paid_amount."""
        await self._session.delete(allocation)

    async def sum_allocated_amount(
        self, supplier_payment_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Decimal:
        """Sum of every currently-active allocation's allocated_amount for
        one supplier payment - the source SupplierPaymentService recomputes
        SupplierPayment.allocated_amount/unallocated_amount from
        (app.modules.supplier_payments.domain.allocation.
        calculate_supplier_payment_allocation_totals), the same
        recompute-from-source discipline
        PaymentService._recalculate_payment_allocation_totals applies."""
        result = await self._session.execute(
            select(func.coalesce(func.sum(SupplierPaymentAllocation.allocated_amount), 0)).where(
                SupplierPaymentAllocation.supplier_payment_id == supplier_payment_id,
                SupplierPaymentAllocation.tenant_id == tenant_id,
            )
        )
        return result.scalar_one()

    async def sum_allocated_amount_by_purchase_bill(
        self, purchase_bill_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Decimal:
        """Sum of every currently-active allocation's allocated_amount
        against one purchase bill, across *every* supplier payment that
        allocates to it - the source SupplierPaymentService passes into
        PurchaseService.recalculate_payment_totals (Sprint 12 Session 4's
        outstanding engine, TASKS.md: "paid_amount = SUM(all allocations)").
        Unlike sum_allocated_amount (scoped to one supplier payment), this is
        scoped to one purchase bill - a single bill can be settled by
        several payments. Mirrors PaymentRepository.sum_allocated_amount_by_invoice
        exactly."""
        result = await self._session.execute(
            select(func.coalesce(func.sum(SupplierPaymentAllocation.allocated_amount), 0)).where(
                SupplierPaymentAllocation.purchase_bill_id == purchase_bill_id,
                SupplierPaymentAllocation.tenant_id == tenant_id,
            )
        )
        return result.scalar_one()

    async def has_allocations(self, supplier_payment_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        """Whether this supplier payment has at least one allocation - the
        Session 5 posting workflow's "must contain at least one allocation"
        guard (TASKS.md). A `LIMIT 1` existence check, not a full count -
        cheaper than sum_allocated_amount for a question that only needs a
        boolean answer. Mirrors PaymentRepository.has_allocations exactly."""
        result = await self._session.execute(
            select(SupplierPaymentAllocation.id)
            .where(
                SupplierPaymentAllocation.supplier_payment_id == supplier_payment_id,
                SupplierPaymentAllocation.tenant_id == tenant_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def ensure_sequence_row(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> None:
        """Guarantees a `supplier_payment_sequences` row exists for this
        (tenant_id, prefix, fiscal_year) via `INSERT ... ON CONFLICT DO
        NOTHING` - mirrors PaymentRepository.ensure_sequence_row exactly,
        safe against two transactions racing to allocate the first number of
        a fiscal year. Must be followed by get_sequence_for_update in the
        same transaction to actually lock and read the row."""
        stmt = (
            pg_insert(SupplierPaymentSequence)
            .values(tenant_id=tenant_id, prefix=prefix, fiscal_year=fiscal_year, last_number=0)
            .on_conflict_do_nothing(index_elements=["tenant_id", "prefix", "fiscal_year"])
        )
        await self._session.execute(stmt)

    async def get_sequence_for_update(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> SupplierPaymentSequence:
        """Locks (`SELECT ... FOR UPDATE`) the counter row for this
        (tenant_id, prefix, fiscal_year) - callers must call
        ensure_sequence_row first in the same transaction so the row is
        guaranteed to exist."""
        result = await self._session.execute(
            select(SupplierPaymentSequence)
            .where(
                SupplierPaymentSequence.tenant_id == tenant_id,
                SupplierPaymentSequence.prefix == prefix,
                SupplierPaymentSequence.fiscal_year == fiscal_year,
            )
            .with_for_update()
        )
        return result.scalar_one()
