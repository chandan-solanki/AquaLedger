import math
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import PaginatedResponse, PaginationMeta
from app.core.errors import AppException, ConflictError
from app.modules.companies.constants import CompanyStatus
from app.modules.companies.exceptions import CompanyNotFoundError
from app.modules.companies.schemas import CompanyResponse
from app.modules.companies.service import CompanyService
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.exceptions import InvoiceNotFoundError
from app.modules.invoices.schemas import InvoiceResponse
from app.modules.invoices.service import InvoiceService
from app.modules.payments.constants import PAYMENT_NUMBER_PREFIX, PaymentStatus
from app.modules.payments.domain.allocation import (
    AllocationExceedsInvoiceBalanceError,
    AllocationExceedsUnallocatedError,
    calculate_payment_allocation_totals,
    validate_allocation_amount,
)
from app.modules.payments.domain.numbering import fiscal_year_for, format_payment_number
from app.modules.payments.exceptions import (
    PaymentAllocationAmountExceededError,
    PaymentAllocationInvoiceInvalidStatusError,
    PaymentAllocationInvoiceNotFoundError,
    PaymentAllocationNotFoundError,
    PaymentAllocationPaymentNotDraftError,
    PaymentCompanyInactiveError,
    PaymentCompanyNotFoundError,
    PaymentNoAllocationsError,
    PaymentNotDraftError,
    PaymentNotFoundError,
    PaymentNumberConflictError,
    PaymentTotalsInvalidError,
)
from app.modules.payments.models import Payment, PaymentAllocation
from app.modules.payments.repository import PaymentRepository
from app.modules.payments.schemas import (
    PaymentAllocationCreateRequest,
    PaymentAllocationResponse,
    PaymentAllocationUpdateRequest,
    PaymentCreateRequest,
    PaymentListParams,
    PaymentResponse,
    PaymentUpdateRequest,
)

_ALLOCATABLE_INVOICE_STATUSES = frozenset({InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID})

# Sprint 10 Session 4's outstanding engine can push an invoice to PAID as a
# *result* of an allocation - editing/removing the very allocation that did
# that must still be allowed (it can only ever reduce what's owed), so
# updating an allocation against the invoice it already targets accepts PAID
# too. Creating a *new* allocation, or moving an existing one onto a
# *different* invoice, still requires _ALLOCATABLE_INVOICE_STATUSES - that
# invoice must still have an open balance to receive money against.
_ALLOCATION_EDITABLE_INVOICE_STATUSES = _ALLOCATABLE_INVOICE_STATUSES | {InvoiceStatus.PAID}


class PaymentService:
    """Sprint 10 Session 2 - draft payment CRUD; Session 3 - the payment
    allocation engine (see the *_allocation methods below); Session 4 - the
    outstanding engine, cascading every allocation mutation into
    Invoice.paid_amount/balance_amount/status and Company.outstanding_amount
    via _recalculate_invoice_and_company; Session 5 - the posting workflow
    (see post()), the one genuine business transaction in this module, the
    same session-by-session build order InvoiceService followed across
    Sprint 9.

    Every mutation keeps `unallocated_amount = amount - allocated_amount`
    true (via _sync_unallocated) - trivial while `allocated_amount` is
    always 0 in Session 2, but from Session 3 on it is kept in sync with the
    sum of active allocations (_recalculate_payment_allocation_totals), the
    same "always recompute the derived field" discipline
    InvoiceService._recalculate_invoice applies to balance_amount.

    Invoice.paid_amount/balance_amount/status are never written here
    directly - only InvoiceService owns those columns
    (recalculate_payment_totals); this module computes the raw allocation
    sum (via its own PaymentRepository) and hands it down, keeping the call
    chain PaymentService -> InvoiceService -> CompanyService
    (ARCHITECTURE.md §2).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PaymentRepository(session)
        # Cross-module reference validation goes through the other module's
        # service, never its repository (ARCHITECTURE.md §2 - modules talk
        # to each other only through service.py).
        self._company_service = CompanyService(session)
        self._invoice_service = InvoiceService(session)

    async def create(
        self, payload: PaymentCreateRequest, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> PaymentResponse:
        await self._ensure_company_active(payload.company_id, tenant_id)

        # payment_number/allocated_amount/status are fixed to NULL/0/DRAFT -
        # none is client-supplied (see PaymentCreateRequest); numbers are
        # assigned only at the Session 5 posting workflow.
        payment = Payment(
            tenant_id=tenant_id,
            company_id=payload.company_id,
            payment_number=None,
            payment_date=payload.payment_date,
            payment_method=payload.payment_method,
            reference_number=payload.reference_number,
            bank_name=payload.bank_name,
            amount=payload.amount,
            allocated_amount=0,
            unallocated_amount=payload.amount,
            remarks=payload.remarks,
            status=PaymentStatus.DRAFT,
            created_by=actor_id,
            updated_by=actor_id,
        )
        await self._repo.add(payment)
        await self._commit_or_raise()
        await self._session.refresh(payment)
        return self._to_response(payment)

    async def get(self, payment_id: uuid.UUID, *, tenant_id: uuid.UUID) -> PaymentResponse:
        payment = await self._get_or_raise(payment_id, tenant_id)
        return self._to_response(payment)

    async def list_payments(
        self, *, tenant_id: uuid.UUID, params: PaymentListParams
    ) -> PaginatedResponse[PaymentResponse]:
        # Company-name search is resolved through CompanyService (not a
        # repository join) - modules never import another module's ORM
        # model directly.
        q_company_ids: list[uuid.UUID] | None = None
        if params.q and params.q.strip():
            q_company_ids = await self._company_service.find_ids_by_name(tenant_id, params.q)

        payments, total = await self._repo.search(
            tenant_id,
            q=params.q,
            q_company_ids=q_company_ids,
            status=params.status,
            company_id=params.company_id,
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
            data=[self._to_response(payment) for payment in payments], meta=meta
        )

    async def update(
        self,
        payment_id: uuid.UUID,
        payload: PaymentUpdateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> PaymentResponse:
        payment = await self._get_or_raise(payment_id, tenant_id)
        self._ensure_draft(payment)
        update_data = payload.model_dump(exclude_unset=True)

        new_company_id = update_data.get("company_id", payment.company_id)
        if "company_id" in update_data and new_company_id != payment.company_id:
            await self._ensure_company_active(new_company_id, tenant_id)

        for field, value in update_data.items():
            setattr(payment, field, value)
        payment.updated_by = actor_id
        # Recomputed unconditionally, not only when `amount` is present in
        # the payload - trivial cost, and it rules out an entire class of
        # "forgot to keep the invariant in sync" bugs (same reasoning
        # InvoiceService.update gives for its unconditional recalculation).
        self._sync_unallocated(payment)
        await self._commit_or_raise()
        await self._session.refresh(payment)
        return self._to_response(payment)

    async def delete(
        self, payment_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        payment = await self._get_or_raise(payment_id, tenant_id)
        self._ensure_draft(payment)
        payment.deleted_at = datetime.now(UTC)
        payment.deleted_by = actor_id
        await self._session.commit()

    async def create_allocation(
        self,
        payment_id: uuid.UUID,
        payload: PaymentAllocationCreateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> PaymentAllocationResponse:
        payment = await self._get_or_raise(payment_id, tenant_id)
        self._ensure_draft_for_allocation(payment)
        invoice = await self._ensure_invoice_allocatable(payload.invoice_id, tenant_id)
        self._validate_allocation_ceilings(
            allocated_amount=payload.allocated_amount,
            invoice_balance=invoice.balance_amount,
            payment_unallocated=payment.unallocated_amount,
        )

        allocation = PaymentAllocation(
            tenant_id=tenant_id,
            payment_id=payment_id,
            invoice_id=payload.invoice_id,
            allocated_amount=payload.allocated_amount,
            created_by=actor_id,
        )
        await self._repo.add_allocation(allocation)
        await self._flush_or_raise()
        await self._recalculate_payment_allocation_totals(payment, tenant_id)
        await self._recalculate_invoice_and_company(payload.invoice_id, tenant_id)
        await self._commit_or_raise()
        await self._session.refresh(allocation)
        return self._to_allocation_response(allocation)

    async def list_allocations(
        self, payment_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> list[PaymentAllocationResponse]:
        # Listing is allowed regardless of payment status - only create/
        # update/delete are DRAFT-only.
        await self._get_or_raise(payment_id, tenant_id)
        allocations = await self._repo.list_allocations(payment_id, tenant_id)
        return [self._to_allocation_response(allocation) for allocation in allocations]

    async def update_allocation(
        self,
        payment_id: uuid.UUID,
        allocation_id: uuid.UUID,
        payload: PaymentAllocationUpdateRequest,
        *,
        tenant_id: uuid.UUID,
    ) -> PaymentAllocationResponse:
        payment = await self._get_or_raise(payment_id, tenant_id)
        self._ensure_draft_for_allocation(payment)
        allocation = await self._get_allocation_or_raise(allocation_id, payment_id, tenant_id)
        update_data = payload.model_dump(exclude_unset=True)

        old_invoice_id = allocation.invoice_id
        new_invoice_id = update_data.get("invoice_id", old_invoice_id)
        new_allocated_amount = update_data.get("allocated_amount", allocation.allocated_amount)
        invoice_unchanged = new_invoice_id == old_invoice_id

        # Editing (or removing money from) the same invoice this allocation
        # already targets must stay possible even if that invoice is now
        # PAID - possibly *because* this very allocation filled it (see
        # _ALLOCATION_EDITABLE_INVOICE_STATUSES's docstring). Retargeting
        # onto a different invoice is treated as attaching new money to it,
        # so that invoice must still be open.
        invoice = await self._ensure_invoice_allocatable(
            new_invoice_id, tenant_id, allow_paid=invoice_unchanged
        )

        # The amount currently locked in by *this* allocation is already
        # reflected in payment.unallocated_amount - and, if the invoice is
        # unchanged, in that invoice's balance_amount too - as spent. Add it
        # back before validating the new amount against each ceiling (see
        # validate_allocation_amount's docstring).
        effective_unallocated = payment.unallocated_amount + allocation.allocated_amount
        effective_invoice_balance = invoice.balance_amount + (
            allocation.allocated_amount if invoice_unchanged else Decimal("0")
        )
        self._validate_allocation_ceilings(
            allocated_amount=new_allocated_amount,
            invoice_balance=effective_invoice_balance,
            payment_unallocated=effective_unallocated,
        )

        allocation.invoice_id = new_invoice_id
        allocation.allocated_amount = new_allocated_amount
        await self._flush_or_raise()
        await self._recalculate_payment_allocation_totals(payment, tenant_id)
        await self._recalculate_invoice_and_company(new_invoice_id, tenant_id)
        if not invoice_unchanged:
            await self._recalculate_invoice_and_company(old_invoice_id, tenant_id)
        await self._commit_or_raise()
        await self._session.refresh(allocation)
        return self._to_allocation_response(allocation)

    async def delete_allocation(
        self, payment_id: uuid.UUID, allocation_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> None:
        payment = await self._get_or_raise(payment_id, tenant_id)
        self._ensure_draft_for_allocation(payment)
        allocation = await self._get_allocation_or_raise(allocation_id, payment_id, tenant_id)
        invoice_id = allocation.invoice_id
        await self._repo.delete_allocation(allocation)
        await self._session.flush()
        await self._recalculate_payment_allocation_totals(payment, tenant_id)
        await self._recalculate_invoice_and_company(invoice_id, tenant_id)
        await self._session.commit()

    async def post(
        self, payment_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> PaymentResponse:
        """Sprint 10 Session 5 - the payment posting workflow (TASKS.md).
        The one genuine business transaction in this module (as opposed to
        CRUD), the payments-module counterpart to InvoiceService.issue().
        Draft -> Posted is irreversible: both this payment
        (_ensure_draft, reused below) and its allocations
        (_ensure_draft_for_allocation, already checked by every allocation
        mutation) become immutable the moment status stops being DRAFT - no
        separate immutability flag or check is needed.

        Invoice.paid_amount/balance_amount/status and Company.
        outstanding_amount are deliberately NOT touched here - Session 4's
        outstanding engine already keeps them correct as of every
        allocation create/update/delete while this payment was still
        DRAFT, so posting has nothing left to recalculate on that side.

        Everything below runs inside one transaction, committed only at the
        very end; any failure at any step rolls back all of it together,
        the same explicit-rollback discipline InvoiceService.issue uses.

        1. Lock the payment row (`SELECT ... FOR UPDATE`) - this alone is
           what makes a concurrent double-post impossible, not just the
           DRAFT check below (two requests both reading status == draft
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
           fail (same reasoning InvoiceService.issue gives).
        9. Mark POSTED.
        10. Commit.

        Extension points intentionally left unimplemented (TASKS.md:
        "prepare extension points only"):
          - Ledger: INSERT ledger_entries (credit = payment.amount).
          - Receipt: generate_payment_receipt, queued for a Celery worker.
          - Outbox/events: INSERT outbox_events(PaymentPosted) for the
            dispatcher to notify/reconcile from.
          - Bank reconciliation: cheque_status/cleared_at tracking.
        """
        try:
            payment = await self._repo.get_by_id_for_update(payment_id, tenant_id)
            if payment is None:
                raise PaymentNotFoundError("Payment not found")
            self._ensure_draft(payment)

            if not await self._repo.has_allocations(payment.id, tenant_id):
                raise PaymentNoAllocationsError(
                    "A payment must have at least one allocation to be posted"
                )

            await self._recalculate_payment_allocation_totals(payment, tenant_id)
            if payment.allocated_amount + payment.unallocated_amount != payment.amount:
                raise PaymentTotalsInvalidError(
                    "Payment totals are inconsistent and cannot be posted"
                )

            payment.payment_number = await self._allocate_payment_number(payment, tenant_id)
            payment.status = PaymentStatus.POSTED
            payment.updated_by = actor_id

            # TODO(Sprint 11): INSERT ledger_entries (credit = payment.amount).
            # See ARCHITECTURE.md §14.2.
            # TODO(Sprint 11): generate_payment_receipt(payment.id), queued for a Celery worker.
            # TODO(Sprint 11): INSERT outbox_events(PaymentPosted) for downstream notification.
            # TODO(future sprint): bank reconciliation - cheque_status/cleared_at tracking.
        except Exception:
            await self._session.rollback()
            raise

        await self._commit_or_raise()
        await self._session.refresh(payment)
        return self._to_response(payment)

    async def _allocate_payment_number(self, payment: Payment, tenant_id: uuid.UUID) -> str:
        """Concurrency-safe sequential number allocation (ARCHITECTURE.md
        §13.1, mirroring InvoiceService._allocate_invoice_number exactly):
        `INSERT ... ON CONFLICT DO NOTHING` guarantees the per-tenant/
        prefix/fiscal-year counter row exists without racing a concurrent
        first allocation for that fiscal year, then `SELECT ... FOR UPDATE`
        locks it so the increment below can never be lost to a concurrent
        post. Only called from post(), already inside its transaction - the
        row lock is held until that transaction commits or rolls back,
        serializing concurrent posts within one tenant/prefix/fiscal-year.
        """
        fiscal_year = fiscal_year_for(payment.payment_date)
        await self._repo.ensure_sequence_row(tenant_id, PAYMENT_NUMBER_PREFIX, fiscal_year)
        sequence = await self._repo.get_sequence_for_update(
            tenant_id, PAYMENT_NUMBER_PREFIX, fiscal_year
        )
        sequence.last_number += 1
        return format_payment_number(PAYMENT_NUMBER_PREFIX, fiscal_year, sequence.last_number)

    @staticmethod
    def _sync_unallocated(payment: Payment) -> None:
        payment.unallocated_amount = payment.amount - payment.allocated_amount

    async def _ensure_company_active(
        self, company_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> CompanyResponse:
        # CompanyService.get() is already tenant-scoped, so a company
        # belonging to another tenant surfaces as "not found" here too -
        # that's the correct behaviour for the "company must belong to the
        # current tenant" rule.
        try:
            company = await self._company_service.get(company_id, tenant_id=tenant_id)
        except CompanyNotFoundError as exc:
            raise PaymentCompanyNotFoundError("The specified company does not exist") from exc
        if company.status != CompanyStatus.ACTIVE:
            raise PaymentCompanyInactiveError("The specified company is not active")
        return company

    @staticmethod
    def _ensure_draft(payment: Payment) -> None:
        if payment.status != PaymentStatus.DRAFT:
            raise PaymentNotDraftError("Only draft payments can be edited or deleted")

    @staticmethod
    def _ensure_draft_for_allocation(payment: Payment) -> None:
        # The allocation-specific counterpart of _ensure_draft - kept
        # separate so allocation endpoints raise their own error code
        # (PaymentAllocationPaymentNotDraftError) rather than the CRUD
        # endpoints' PaymentNotDraftError.
        if payment.status != PaymentStatus.DRAFT:
            raise PaymentAllocationPaymentNotDraftError(
                "Only draft payments can receive, update or remove allocations"
            )

    async def _ensure_invoice_allocatable(
        self, invoice_id: uuid.UUID, tenant_id: uuid.UUID, *, allow_paid: bool = False
    ) -> InvoiceResponse:
        # InvoiceService.get() is already tenant-scoped, so an invoice
        # belonging to another tenant surfaces as "not found" here too -
        # the same "must belong to the current tenant" rule
        # _ensure_company_active applies to companies.
        try:
            invoice = await self._invoice_service.get(invoice_id, tenant_id=tenant_id)
        except InvoiceNotFoundError as exc:
            raise PaymentAllocationInvoiceNotFoundError(
                "The specified invoice does not exist"
            ) from exc
        allowed_statuses = (
            _ALLOCATION_EDITABLE_INVOICE_STATUSES if allow_paid else _ALLOCATABLE_INVOICE_STATUSES
        )
        if invoice.status not in allowed_statuses:
            raise PaymentAllocationInvoiceInvalidStatusError(
                "The specified invoice must be issued or partially paid to receive an allocation"
            )
        return invoice

    @staticmethod
    def _validate_allocation_ceilings(
        *,
        allocated_amount: Decimal,
        invoice_balance: Decimal,
        payment_unallocated: Decimal,
    ) -> None:
        """Thin translation wrapper around
        app.modules.payments.domain.allocation.validate_allocation_amount:
        both of its domain-level exceptions map to the same application-
        layer PaymentAllocationAmountExceededError (one shared error code
        for both ceilings - see that exception's docstring), so create_
        allocation and update_allocation share this instead of each
        duplicating the except clauses."""
        try:
            validate_allocation_amount(
                allocated_amount=allocated_amount,
                invoice_balance=invoice_balance,
                payment_unallocated=payment_unallocated,
            )
        except (AllocationExceedsInvoiceBalanceError, AllocationExceedsUnallocatedError) as exc:
            raise PaymentAllocationAmountExceededError(str(exc)) from exc

    async def _get_allocation_or_raise(
        self, allocation_id: uuid.UUID, payment_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PaymentAllocation:
        allocation = await self._repo.get_allocation_by_id(allocation_id, payment_id, tenant_id)
        if allocation is None:
            raise PaymentAllocationNotFoundError("Payment allocation not found")
        return allocation

    async def _recalculate_payment_allocation_totals(
        self, payment: Payment, tenant_id: uuid.UUID
    ) -> None:
        """Recomputes Payment.allocated_amount/unallocated_amount from the
        sum of this payment's currently-active allocations
        (app.modules.payments.domain.allocation) - never inline here.
        Called after every allocation mutation: created, updated or
        deleted.

        Callers must stage their own change first (an `add`, a field
        assignment, or `repo.delete_allocation`) and `await
        self._session.flush()` before calling this - this app's session
        factory sets `autoflush=False` (app.db.session), so without an
        explicit flush this method's SUM query would miss whatever the
        caller just added/changed/removed.
        """
        total_allocated = await self._repo.sum_allocated_amount(payment.id, tenant_id)
        totals = calculate_payment_allocation_totals(
            payment_amount=payment.amount, total_allocated=total_allocated
        )
        payment.allocated_amount = totals.allocated_amount
        payment.unallocated_amount = totals.unallocated_amount

    async def _recalculate_invoice_and_company(
        self, invoice_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        """Sprint 10 Session 4 outstanding engine: sums this invoice's
        currently-active allocations across every payment (this module's own
        PaymentRepository - never InvoiceRepository, ARCHITECTURE.md §2) and
        hands the total to InvoiceService.recalculate_payment_totals, which
        applies the formula, persists it, and cascades into
        CompanyService.recalculate_outstanding for the invoice's billed
        company - the full PaymentService -> InvoiceService -> CompanyService
        chain. Called after every allocation mutation (created, updated or
        deleted) that touches this invoice.

        Callers must stage their own change first and flush before calling
        this, same requirement as _recalculate_payment_allocation_totals -
        this app's session factory sets `autoflush=False` (app.db.session).
        """
        total_allocated = await self._repo.sum_allocated_amount_by_invoice(invoice_id, tenant_id)
        await self._invoice_service.recalculate_payment_totals(
            invoice_id, tenant_id=tenant_id, total_allocated=total_allocated
        )

    @staticmethod
    def _to_allocation_response(allocation: PaymentAllocation) -> PaymentAllocationResponse:
        return PaymentAllocationResponse.model_validate(allocation)

    async def _get_or_raise(self, payment_id: uuid.UUID, tenant_id: uuid.UUID) -> Payment:
        payment = await self._repo.get_by_id(payment_id, tenant_id)
        if payment is None:
            raise PaymentNotFoundError("Payment not found")
        return payment

    async def _flush_or_raise(self) -> None:
        """Flush, translating an integrity violation into a clean error -
        the create_allocation/update_allocation counterpart of
        _commit_or_raise. A unique-constraint violation on
        `ix_payment_allocations_payment_invoice` surfaces here, at flush
        time, not at the later commit: _recalculate_payment_allocation_totals
        needs to read back the just-staged row via a SUM query first
        (autoflush is disabled - app.db.session), which forces the flush -
        and Postgres evaluates the unique index during that same statement,
        before COMMIT is ever reached. Without this, the raw IntegrityError
        would propagate straight out of the request instead of the clean
        409 _commit_or_raise's callers expect.
        """
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise self._translate_integrity_error(exc) from exc

    async def _commit_or_raise(self) -> None:
        """Commit, translating an integrity violation into a clean error.

        `ix_payment_allocations_payment_invoice` (ARCHITECTURE.md §5.2:
        "UNIQUE(payment_id, invoice_id)") is reachable if a second
        allocation is created against an invoice a payment already
        allocates to - update_allocation could reassign an allocation's
        invoice_id onto one already used by a sibling allocation the same
        way. `ix_payments_tenant_payment_number` (Session 5's posting
        workflow) should be unreachable given
        _allocate_payment_number's `SELECT ... FOR UPDATE` locking of the
        per-tenant/prefix/fiscal-year counter row, but is translated here
        as a defensive backstop too, the same posture
        InvoiceService._commit_or_raise takes for invoice_number. Caught
        here rather than pre-checked with a SELECT, the same race-avoidance
        rationale CompanyService gives for its own unique constraints.
        """
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise self._translate_integrity_error(exc) from exc

    @staticmethod
    def _translate_integrity_error(exc: IntegrityError) -> AppException:
        driver_error = getattr(exc.orig, "__cause__", None)
        constraint = getattr(driver_error, "constraint_name", None) or ""
        if constraint == "ix_payment_allocations_payment_invoice":
            return ConflictError("This payment already has an allocation against that invoice")
        if constraint == "ix_payments_tenant_payment_number":
            return PaymentNumberConflictError(
                "This payment number is already in use for this tenant"
            )
        return ConflictError("This operation conflicts with existing data")

    @staticmethod
    def _to_response(payment: Payment) -> PaymentResponse:
        return PaymentResponse.model_validate(payment)
