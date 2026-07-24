import math
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import PaginatedResponse, PaginationMeta
from app.core.errors import AppException, ConflictError
from app.modules.purchase.constants import PurchaseStatus
from app.modules.purchase.exceptions import PurchaseBillNotFoundError
from app.modules.purchase.schemas import PurchaseBillResponse
from app.modules.purchase.service import PurchaseService
from app.modules.supplier_payments.constants import (
    SUPPLIER_PAYMENT_NUMBER_PREFIX,
    SupplierPaymentStatus,
)
from app.modules.supplier_payments.domain.allocation import (
    AllocationExceedsPurchaseBillBalanceError,
    AllocationExceedsUnallocatedError,
    calculate_supplier_payment_allocation_totals,
    validate_allocation_amount,
)
from app.modules.supplier_payments.domain.numbering import (
    fiscal_year_for,
    format_supplier_payment_number,
)
from app.modules.supplier_payments.exceptions import (
    SupplierPaymentAllocationAmountExceededError,
    SupplierPaymentAllocationNotFoundError,
    SupplierPaymentAllocationPaymentNotDraftError,
    SupplierPaymentAllocationPurchaseBillNotFoundError,
    SupplierPaymentNoAllocationsError,
    SupplierPaymentNotDraftError,
    SupplierPaymentNotFoundError,
    SupplierPaymentNumberConflictError,
    SupplierPaymentPurchaseBillNotAllocatableError,
    SupplierPaymentSupplierInactiveError,
    SupplierPaymentSupplierNotFoundError,
    SupplierPaymentTotalsInvalidError,
)
from app.modules.supplier_payments.models import SupplierPayment, SupplierPaymentAllocation
from app.modules.supplier_payments.repository import SupplierPaymentRepository
from app.modules.supplier_payments.schemas import (
    SupplierPaymentAllocationCreateRequest,
    SupplierPaymentAllocationResponse,
    SupplierPaymentAllocationUpdateRequest,
    SupplierPaymentCreateRequest,
    SupplierPaymentListParams,
    SupplierPaymentResponse,
    SupplierPaymentUpdateRequest,
)
from app.modules.suppliers.constants import SupplierStatus
from app.modules.suppliers.exceptions import SupplierNotFoundError
from app.modules.suppliers.schemas import SupplierResponse
from app.modules.suppliers.service import SupplierService

_ALLOCATABLE_PURCHASE_BILL_STATUSES = frozenset(
    {PurchaseStatus.POSTED, PurchaseStatus.PARTIALLY_PAID}
)

# Sprint 12 Session 4's outstanding engine can push a purchase bill to PAID
# as a *result* of an allocation - editing/removing the very allocation that
# did that must still be allowed (it can only ever reduce what's owed), so
# updating an allocation against the bill it already targets accepts PAID
# too. Creating a *new* allocation, or moving an existing one onto a
# *different* bill, still requires _ALLOCATABLE_PURCHASE_BILL_STATUSES - that
# bill must still have an open balance to receive money against. Mirrors
# payments/service.py's _ALLOCATION_EDITABLE_INVOICE_STATUSES exactly.
_ALLOCATION_EDITABLE_PURCHASE_BILL_STATUSES = _ALLOCATABLE_PURCHASE_BILL_STATUSES | {
    PurchaseStatus.PAID
}


class SupplierPaymentService:
    """Sprint 12 Session 2 - draft supplier payment CRUD; Session 3 - the
    payment allocation engine; Session 4 - the outstanding reconciliation
    engine; Session 5 - the posting workflow (see post() below), mirroring
    PaymentService's own session-by-session build order (Sprint 10).

    Supplier validation goes through SupplierService only - never
    SupplierRepository directly (ARCHITECTURE.md §2, TASKS.md's explicit
    instruction for Session 2), mirroring PurchaseService's own
    _ensure_supplier_active. Purchase bill validation goes through
    PurchaseService only - never PurchaseRepository directly (ARCHITECTURE.md
    §2, TASKS.md's explicit instruction for Session 3), the same rule applied
    on the other side of the allocation.

    Every mutation keeps `unallocated_amount = amount - allocated_amount`
    true (via _sync_unallocated for plain field edits, and from Session 3 on
    via _recalculate_supplier_payment_allocation_totals for allocation
    mutations, kept in sync with the sum of active allocations) - the same
    "always recompute the derived field" discipline PaymentService applies.

    PurchaseBill.paid_amount/balance_amount/status and
    Supplier.outstanding_amount are recalculated by
    _recalculate_purchase_bill_and_supplier (Session 4), called after every
    allocation create/update/delete - this module never writes those columns
    directly, only PurchaseService/SupplierService own them
    (ARCHITECTURE.md §2's cross-module-through-services rule, and the same
    "recompute from source, never patch incrementally" discipline
    PaymentService's own outstanding-engine cascade applies).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SupplierPaymentRepository(session)
        # Cross-module reference validation goes through the other module's
        # service, never its repository (ARCHITECTURE.md §2).
        self._supplier_service = SupplierService(session)
        self._purchase_service = PurchaseService(session)

    async def create(
        self,
        payload: SupplierPaymentCreateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> SupplierPaymentResponse:
        await self._ensure_supplier_active(payload.supplier_id, tenant_id)

        # payment_number/posted_at stay NULL and allocated_amount/status are
        # fixed - none is client-supplied (see SupplierPaymentCreateRequest);
        # numbers are assigned only at the Session 5 posting workflow.
        supplier_payment = SupplierPayment(
            tenant_id=tenant_id,
            supplier_id=payload.supplier_id,
            payment_number=None,
            payment_date=payload.payment_date,
            payment_method=payload.payment_method,
            reference_number=payload.reference_number,
            bank_name=payload.bank_name,
            amount=payload.amount,
            allocated_amount=0,
            unallocated_amount=payload.amount,
            remarks=payload.remarks,
            status=SupplierPaymentStatus.DRAFT,
            posted_at=None,
            created_by=actor_id,
            updated_by=actor_id,
        )
        await self._repo.add(supplier_payment)
        await self._commit_or_raise()
        await self._session.refresh(supplier_payment)
        return self._to_response(supplier_payment)

    async def get(
        self, supplier_payment_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> SupplierPaymentResponse:
        supplier_payment = await self._get_or_raise(supplier_payment_id, tenant_id)
        return self._to_response(supplier_payment)

    async def list_supplier_payments(
        self, *, tenant_id: uuid.UUID, params: SupplierPaymentListParams
    ) -> PaginatedResponse[SupplierPaymentResponse]:
        # Supplier-name search is resolved through SupplierService (not a
        # repository join) - modules never import another module's ORM
        # model directly.
        q_supplier_ids: list[uuid.UUID] | None = None
        if params.q and params.q.strip():
            q_supplier_ids = await self._supplier_service.find_ids_by_name(tenant_id, params.q)

        supplier_payments, total = await self._repo.search(
            tenant_id,
            q=params.q,
            q_supplier_ids=q_supplier_ids,
            status=params.status,
            supplier_id=params.supplier_id,
            payment_method=params.payment_method,
            payment_date_from=params.payment_date_from,
            payment_date_to=params.payment_date_to,
            sort=params.sort,
            page=params.page,
            page_size=params.page_size,
        )
        total_pages = math.ceil(total / params.page_size) if total else 0
        meta = PaginationMeta(
            total_records=total,
            total_pages=total_pages,
            current_page=params.page,
            page_size=params.page_size,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )
        return PaginatedResponse(
            data=[self._to_response(supplier_payment) for supplier_payment in supplier_payments],
            meta=meta,
        )

    async def update(
        self,
        supplier_payment_id: uuid.UUID,
        payload: SupplierPaymentUpdateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> SupplierPaymentResponse:
        supplier_payment = await self._get_or_raise(supplier_payment_id, tenant_id)
        self._ensure_draft(supplier_payment)
        update_data = payload.model_dump(exclude_unset=True)

        new_supplier_id = update_data.get("supplier_id", supplier_payment.supplier_id)
        if "supplier_id" in update_data and new_supplier_id != supplier_payment.supplier_id:
            await self._ensure_supplier_active(new_supplier_id, tenant_id)

        for field, value in update_data.items():
            setattr(supplier_payment, field, value)
        supplier_payment.updated_by = actor_id
        # Recomputed unconditionally, not only when `amount` is present in
        # the payload - trivial cost, and it rules out an entire class of
        # "forgot to keep the invariant in sync" bugs (same reasoning
        # PaymentService.update gives for its own unconditional recalc).
        self._sync_unallocated(supplier_payment)
        await self._commit_or_raise()
        await self._session.refresh(supplier_payment)
        return self._to_response(supplier_payment)

    async def delete(
        self, supplier_payment_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        supplier_payment = await self._get_or_raise(supplier_payment_id, tenant_id)
        self._ensure_draft(supplier_payment)
        supplier_payment.deleted_at = datetime.now(UTC)
        supplier_payment.deleted_by = actor_id
        await self._session.commit()

    async def create_allocation(
        self,
        supplier_payment_id: uuid.UUID,
        payload: SupplierPaymentAllocationCreateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> SupplierPaymentAllocationResponse:
        supplier_payment = await self._get_or_raise(supplier_payment_id, tenant_id)
        self._ensure_draft_for_allocation(supplier_payment)
        purchase_bill = await self._ensure_purchase_bill_allocatable(
            payload.purchase_bill_id, tenant_id
        )
        self._validate_allocation_ceilings(
            allocated_amount=payload.allocated_amount,
            purchase_bill_balance=purchase_bill.balance_amount,
            payment_unallocated=supplier_payment.unallocated_amount,
        )

        allocation = SupplierPaymentAllocation(
            tenant_id=tenant_id,
            supplier_payment_id=supplier_payment_id,
            purchase_bill_id=payload.purchase_bill_id,
            allocated_amount=payload.allocated_amount,
            created_by=actor_id,
        )
        await self._repo.add_allocation(allocation)
        await self._flush_or_raise()
        await self._recalculate_supplier_payment_allocation_totals(supplier_payment, tenant_id)
        await self._recalculate_purchase_bill_and_supplier(payload.purchase_bill_id, tenant_id)
        await self._commit_or_raise()
        await self._session.refresh(allocation)
        return self._to_allocation_response(allocation)

    async def list_allocations(
        self, supplier_payment_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> list[SupplierPaymentAllocationResponse]:
        # Listing is allowed regardless of payment status - only create/
        # update/delete are DRAFT-only.
        await self._get_or_raise(supplier_payment_id, tenant_id)
        allocations = await self._repo.list_allocations(supplier_payment_id, tenant_id)
        return [self._to_allocation_response(allocation) for allocation in allocations]

    async def update_allocation(
        self,
        supplier_payment_id: uuid.UUID,
        allocation_id: uuid.UUID,
        payload: SupplierPaymentAllocationUpdateRequest,
        *,
        tenant_id: uuid.UUID,
    ) -> SupplierPaymentAllocationResponse:
        supplier_payment = await self._get_or_raise(supplier_payment_id, tenant_id)
        self._ensure_draft_for_allocation(supplier_payment)
        allocation = await self._get_allocation_or_raise(
            allocation_id, supplier_payment_id, tenant_id
        )
        update_data = payload.model_dump(exclude_unset=True)

        old_purchase_bill_id = allocation.purchase_bill_id
        new_purchase_bill_id = update_data.get("purchase_bill_id", old_purchase_bill_id)
        new_allocated_amount = update_data.get("allocated_amount", allocation.allocated_amount)
        bill_unchanged = new_purchase_bill_id == old_purchase_bill_id

        # Editing (or removing money from) the same bill this allocation
        # already targets must stay possible even if that bill is now PAID -
        # possibly *because* this very allocation filled it (see
        # _ALLOCATION_EDITABLE_PURCHASE_BILL_STATUSES's docstring).
        # Retargeting onto a different bill is treated as attaching new
        # money to it, so that bill must still be open.
        purchase_bill = await self._ensure_purchase_bill_allocatable(
            new_purchase_bill_id, tenant_id, allow_paid=bill_unchanged
        )

        # The amount currently locked in by *this* allocation is already
        # reflected in payment.unallocated_amount - and, if the bill is
        # unchanged, in that bill's balance_amount too - as spent. Add it
        # back before validating the new amount against each ceiling (see
        # validate_allocation_amount's docstring).
        effective_unallocated = supplier_payment.unallocated_amount + allocation.allocated_amount
        effective_bill_balance = purchase_bill.balance_amount + (
            allocation.allocated_amount if bill_unchanged else Decimal("0")
        )
        self._validate_allocation_ceilings(
            allocated_amount=new_allocated_amount,
            purchase_bill_balance=effective_bill_balance,
            payment_unallocated=effective_unallocated,
        )

        allocation.purchase_bill_id = new_purchase_bill_id
        allocation.allocated_amount = new_allocated_amount
        await self._flush_or_raise()
        await self._recalculate_supplier_payment_allocation_totals(supplier_payment, tenant_id)
        await self._recalculate_purchase_bill_and_supplier(new_purchase_bill_id, tenant_id)
        if not bill_unchanged:
            await self._recalculate_purchase_bill_and_supplier(old_purchase_bill_id, tenant_id)
        await self._commit_or_raise()
        await self._session.refresh(allocation)
        return self._to_allocation_response(allocation)

    async def delete_allocation(
        self, supplier_payment_id: uuid.UUID, allocation_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> None:
        supplier_payment = await self._get_or_raise(supplier_payment_id, tenant_id)
        self._ensure_draft_for_allocation(supplier_payment)
        allocation = await self._get_allocation_or_raise(
            allocation_id, supplier_payment_id, tenant_id
        )
        purchase_bill_id = allocation.purchase_bill_id
        await self._repo.delete_allocation(allocation)
        await self._session.flush()
        await self._recalculate_supplier_payment_allocation_totals(supplier_payment, tenant_id)
        await self._recalculate_purchase_bill_and_supplier(purchase_bill_id, tenant_id)
        await self._session.commit()

    async def post(
        self, supplier_payment_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> SupplierPaymentResponse:
        """Sprint 12 Session 5 - the supplier payment posting workflow
        (TASKS.md). The core business transaction of this module, mirroring
        PaymentService.post()/PurchaseService.post() exactly. Draft ->
        Posted is irreversible: both this payment (_ensure_draft, reused
        below) and its allocations (_ensure_draft_for_allocation, already
        checked by every allocation mutation) become immutable the moment
        status stops being DRAFT - no separate immutability flag or check is
        needed.

        PurchaseBill.paid_amount/balance_amount/status and
        Supplier.outstanding_amount are deliberately NOT touched here -
        Session 4's outstanding engine already keeps them correct as of
        every allocation create/update/delete while this payment was still
        DRAFT, so posting has nothing left to recalculate on that side.

        Everything below runs inside one transaction, committed only at the
        very end; any failure at any step rolls back all of it together,
        the same explicit-rollback discipline PurchaseService.post/
        PaymentService.post use.

        1. Lock the supplier payment row (`SELECT ... FOR UPDATE`) - this
           alone is what makes a concurrent double-post impossible, not just
           the DRAFT check below (two requests both reading status == draft
           before either writes would otherwise both proceed).
        2/3. get_by_id_for_update already scopes by tenant_id, so "does not
           exist" and "belongs to another tenant" are the same 404.
        4. Must be DRAFT - this single check also covers "cannot post
           twice" (status is already POSTED) and "cannot post a cancelled
           payment" (status is CANCELLED).
        5. Must have at least one allocation - an entirely unallocated
           payment is still on-account credit, not yet something to lock
           into a numbered financial record.
        6. Recalculate allocated_amount/unallocated_amount from the sum of
           this payment's currently-active allocations immediately before
           posting (never trust whatever was last persisted) - the same
           recompute-from-source helper every allocation mutation uses.
        7. Verify allocated_amount + unallocated_amount == amount - a
           defensive invariant check that should be unreachable given step
           6's recompute always keeps this true by construction, but a
           corrupted row fails loudly here rather than silently posting.
        8. Generate the payment number only after every validation passes -
           avoids burning a number on an attempt that was always going to
           fail (same reasoning PurchaseService.post/InvoiceService.issue
           give).
        9. Mark POSTED, stamp posted_at.
        10. Commit.

        Extension points intentionally left unimplemented (TASKS.md: "Do
        NOT implement"):
          - Ledger/journal entries.
          - PDF receipt generation.
          - Notifications/outbox events.
          - Bank reconciliation, cheque bounce, receipt printing.
        """
        try:
            supplier_payment = await self._repo.get_by_id_for_update(supplier_payment_id, tenant_id)
            if supplier_payment is None:
                raise SupplierPaymentNotFoundError("Supplier payment not found")
            self._ensure_draft(supplier_payment)

            if not await self._repo.has_allocations(supplier_payment.id, tenant_id):
                raise SupplierPaymentNoAllocationsError(
                    "A supplier payment must have at least one allocation to be posted"
                )

            await self._recalculate_supplier_payment_allocation_totals(supplier_payment, tenant_id)
            if (
                supplier_payment.allocated_amount + supplier_payment.unallocated_amount
                != supplier_payment.amount
            ):
                raise SupplierPaymentTotalsInvalidError(
                    "Supplier payment totals are inconsistent and cannot be posted"
                )

            supplier_payment.payment_number = await self._allocate_payment_number(
                supplier_payment, tenant_id
            )
            supplier_payment.status = SupplierPaymentStatus.POSTED
            supplier_payment.posted_at = datetime.now(UTC)
            supplier_payment.updated_by = actor_id

            # TODO(future sprint): INSERT ledger_entries (credit = supplier_payment.amount).
            # TODO(future sprint): generate_supplier_payment_receipt, queued for a Celery worker.
            # TODO(future sprint): INSERT outbox_events(SupplierPaymentPosted) for notification.
            # TODO(future sprint): bank reconciliation - cheque_status/cleared_at tracking.
        except Exception:
            await self._session.rollback()
            raise

        await self._commit_or_raise()
        await self._session.refresh(supplier_payment)
        return self._to_response(supplier_payment)

    async def _allocate_payment_number(
        self, supplier_payment: SupplierPayment, tenant_id: uuid.UUID
    ) -> str:
        """Concurrency-safe sequential number allocation (ARCHITECTURE.md
        §13.1, mirroring PaymentService._allocate_payment_number/
        PurchaseService._allocate_purchase_number exactly): `INSERT ... ON
        CONFLICT DO NOTHING` guarantees the per-tenant/prefix/fiscal-year
        counter row exists without racing a concurrent first allocation for
        that fiscal year, then `SELECT ... FOR UPDATE` locks it so the
        increment below can never be lost to a concurrent post. Only called
        from post(), already inside its transaction - the row lock is held
        until that transaction commits or rolls back, serializing
        concurrent posts within one tenant/prefix/fiscal-year.
        """
        fiscal_year = fiscal_year_for(supplier_payment.payment_date)
        await self._repo.ensure_sequence_row(tenant_id, SUPPLIER_PAYMENT_NUMBER_PREFIX, fiscal_year)
        sequence = await self._repo.get_sequence_for_update(
            tenant_id, SUPPLIER_PAYMENT_NUMBER_PREFIX, fiscal_year
        )
        sequence.last_number += 1
        return format_supplier_payment_number(
            SUPPLIER_PAYMENT_NUMBER_PREFIX, fiscal_year, sequence.last_number
        )

    @staticmethod
    def _sync_unallocated(supplier_payment: SupplierPayment) -> None:
        supplier_payment.unallocated_amount = (
            supplier_payment.amount - supplier_payment.allocated_amount
        )

    async def _ensure_supplier_active(
        self, supplier_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> SupplierResponse:
        # SupplierService.get() is already tenant-scoped, so a supplier
        # belonging to another tenant surfaces as "not found" here too -
        # that's the correct behaviour for the "supplier must belong to the
        # current tenant" rule (mirrors PurchaseService._ensure_supplier_active).
        try:
            supplier = await self._supplier_service.get(supplier_id, tenant_id=tenant_id)
        except SupplierNotFoundError as exc:
            raise SupplierPaymentSupplierNotFoundError(
                "The specified supplier does not exist"
            ) from exc
        if supplier.status != SupplierStatus.ACTIVE:
            raise SupplierPaymentSupplierInactiveError("The specified supplier is not active")
        return supplier

    @staticmethod
    def _ensure_draft(supplier_payment: SupplierPayment) -> None:
        if supplier_payment.status != SupplierPaymentStatus.DRAFT:
            raise SupplierPaymentNotDraftError(
                "Only draft supplier payments can be edited or deleted"
            )

    @staticmethod
    def _ensure_draft_for_allocation(supplier_payment: SupplierPayment) -> None:
        # The allocation-specific counterpart of _ensure_draft - kept
        # separate so allocation endpoints raise their own error code
        # (SupplierPaymentAllocationPaymentNotDraftError) rather than the
        # CRUD endpoints' SupplierPaymentNotDraftError.
        if supplier_payment.status != SupplierPaymentStatus.DRAFT:
            raise SupplierPaymentAllocationPaymentNotDraftError(
                "Only draft supplier payments can receive, update or remove allocations"
            )

    async def _ensure_purchase_bill_allocatable(
        self, purchase_bill_id: uuid.UUID, tenant_id: uuid.UUID, *, allow_paid: bool = False
    ) -> PurchaseBillResponse:
        # PurchaseService.get() is already tenant-scoped, so a purchase bill
        # belonging to another tenant surfaces as "not found" here too - the
        # same "must belong to the current tenant" rule
        # _ensure_supplier_active applies to suppliers.
        try:
            purchase_bill = await self._purchase_service.get(purchase_bill_id, tenant_id=tenant_id)
        except PurchaseBillNotFoundError as exc:
            raise SupplierPaymentAllocationPurchaseBillNotFoundError(
                "The specified purchase bill does not exist"
            ) from exc
        # TASKS.md Session 3: "Purchase Bill status POSTED, PARTIALLY_PAID".
        # DRAFT/CANCELLED are always excluded; PAID is excluded too unless
        # `allow_paid` (update_allocation editing the same bill it already
        # targets - see _ALLOCATION_EDITABLE_PURCHASE_BILL_STATUSES's
        # docstring), mirroring PaymentService._ensure_invoice_allocatable's
        # own allowed-status set exactly.
        allowed_statuses = (
            _ALLOCATION_EDITABLE_PURCHASE_BILL_STATUSES
            if allow_paid
            else _ALLOCATABLE_PURCHASE_BILL_STATUSES
        )
        if purchase_bill.status not in allowed_statuses:
            raise SupplierPaymentPurchaseBillNotAllocatableError(
                "The specified purchase bill must be posted or partially paid to receive "
                "an allocation"
            )
        return purchase_bill

    @staticmethod
    def _validate_allocation_ceilings(
        *,
        allocated_amount: Decimal,
        purchase_bill_balance: Decimal,
        payment_unallocated: Decimal,
    ) -> None:
        """Thin translation wrapper around
        app.modules.supplier_payments.domain.allocation.validate_allocation_amount:
        both of its domain-level exceptions map to the same
        application-layer SupplierPaymentAllocationAmountExceededError (one
        shared error code for both ceilings - see that exception's
        docstring), so create_allocation and update_allocation share this
        instead of each duplicating the except clauses."""
        try:
            validate_allocation_amount(
                allocated_amount=allocated_amount,
                purchase_bill_balance=purchase_bill_balance,
                payment_unallocated=payment_unallocated,
            )
        except (
            AllocationExceedsPurchaseBillBalanceError,
            AllocationExceedsUnallocatedError,
        ) as exc:
            raise SupplierPaymentAllocationAmountExceededError(str(exc)) from exc

    async def _get_allocation_or_raise(
        self, allocation_id: uuid.UUID, supplier_payment_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> SupplierPaymentAllocation:
        allocation = await self._repo.get_allocation_by_id(
            allocation_id, supplier_payment_id, tenant_id
        )
        if allocation is None:
            raise SupplierPaymentAllocationNotFoundError("Supplier payment allocation not found")
        return allocation

    async def _recalculate_supplier_payment_allocation_totals(
        self, supplier_payment: SupplierPayment, tenant_id: uuid.UUID
    ) -> None:
        """Recomputes SupplierPayment.allocated_amount/unallocated_amount
        from the sum of this payment's currently-active allocations
        (app.modules.supplier_payments.domain.allocation) - never inline
        here. Called after every allocation mutation: created, updated or
        deleted.

        Callers must stage their own change first (an `add`, a field
        assignment, or `repo.delete_allocation`) and `await
        self._session.flush()` before calling this - this app's session
        factory sets `autoflush=False` (app.db.session), so without an
        explicit flush this method's SUM query would miss whatever the
        caller just added/changed/removed.
        """
        total_allocated = await self._repo.sum_allocated_amount(supplier_payment.id, tenant_id)
        totals = calculate_supplier_payment_allocation_totals(
            payment_amount=supplier_payment.amount, total_allocated=total_allocated
        )
        supplier_payment.allocated_amount = totals.allocated_amount
        supplier_payment.unallocated_amount = totals.unallocated_amount

    async def _recalculate_purchase_bill_and_supplier(
        self, purchase_bill_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        """Sprint 12 Session 4 outstanding engine: sums this purchase bill's
        currently-active allocations across every supplier payment (this
        module's own SupplierPaymentRepository - never PurchaseRepository,
        ARCHITECTURE.md §2) and hands the total to
        PurchaseService.recalculate_payment_totals, which applies the
        formula, persists it, and cascades into
        SupplierService.recalculate_outstanding for the bill's supplier - the
        full SupplierPaymentService -> PurchaseService -> SupplierService
        chain. Called after every allocation mutation (created, updated or
        deleted) that touches this purchase bill.

        Callers must stage their own change first and flush before calling
        this, same requirement as _recalculate_supplier_payment_allocation_totals -
        this app's session factory sets `autoflush=False` (app.db.session).
        Mirrors PaymentService._recalculate_invoice_and_company exactly.
        """
        total_allocated = await self._repo.sum_allocated_amount_by_purchase_bill(
            purchase_bill_id, tenant_id
        )
        await self._purchase_service.recalculate_payment_totals(
            purchase_bill_id, tenant_id=tenant_id, total_allocated=total_allocated
        )

    async def _get_or_raise(
        self, supplier_payment_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> SupplierPayment:
        supplier_payment = await self._repo.get_by_id(supplier_payment_id, tenant_id)
        if supplier_payment is None:
            raise SupplierPaymentNotFoundError("Supplier payment not found")
        return supplier_payment

    async def _flush_or_raise(self) -> None:
        """Flush, translating an integrity violation into a clean error -
        the create_allocation/update_allocation counterpart of
        _commit_or_raise. A unique-constraint violation on
        `ix_supplier_payment_allocations_payment_bill` surfaces here, at
        flush time, not at the later commit:
        _recalculate_supplier_payment_allocation_totals needs to read back
        the just-staged row via a SUM query first (autoflush is disabled -
        app.db.session), which forces the flush - and Postgres evaluates
        the unique index during that same statement, before COMMIT is ever
        reached. Without this, the raw IntegrityError would propagate
        straight out of the request instead of the clean 409
        _commit_or_raise's callers expect. Mirrors
        PaymentService._flush_or_raise exactly.
        """
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise self._translate_integrity_error(exc) from exc

    async def _commit_or_raise(self) -> None:
        """Commit, translating an integrity violation into a clean error.
        `ix_supplier_payments_tenant_payment_number` (Session 5's posting
        workflow) should be unreachable given _allocate_payment_number's
        `SELECT ... FOR UPDATE` locking of the per-tenant/prefix/fiscal-year
        counter row, but is translated here as a defensive backstop too,
        the same posture PaymentService._commit_or_raise takes for
        payment_number."""
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise self._translate_integrity_error(exc) from exc

    @staticmethod
    def _translate_integrity_error(exc: IntegrityError) -> AppException:
        """`ix_supplier_payment_allocations_payment_bill` (this module's own
        `UNIQUE(supplier_payment_id, purchase_bill_id)`) is reachable if a
        second allocation is created against a purchase bill a payment
        already allocates to - update_allocation could reassign an
        allocation's purchase_bill_id onto one already used by a sibling
        allocation the same way. `ix_supplier_payments_tenant_payment_number`
        should be unreachable given _allocate_payment_number's `SELECT ...
        FOR UPDATE` locking, but is translated here as a defensive backstop
        too, the same posture PaymentService._translate_integrity_error
        takes for `ix_payment_allocations_payment_invoice`/
        `ix_payments_tenant_payment_number`."""
        driver_error = getattr(exc.orig, "__cause__", None)
        constraint = getattr(driver_error, "constraint_name", None) or ""
        if constraint == "ix_supplier_payment_allocations_payment_bill":
            return ConflictError(
                "This supplier payment already has an allocation against that purchase bill"
            )
        if constraint == "ix_supplier_payments_tenant_payment_number":
            return SupplierPaymentNumberConflictError(
                "This payment number is already in use for this tenant"
            )
        return ConflictError("This operation conflicts with existing data")

    @staticmethod
    def _to_allocation_response(
        allocation: SupplierPaymentAllocation,
    ) -> SupplierPaymentAllocationResponse:
        return SupplierPaymentAllocationResponse.model_validate(allocation)

    @staticmethod
    def _to_response(supplier_payment: SupplierPayment) -> SupplierPaymentResponse:
        return SupplierPaymentResponse.model_validate(supplier_payment)
