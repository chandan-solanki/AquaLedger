import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.core.errors import ConflictError
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.exceptions import InvoiceNotFoundError
from app.modules.payments.constants import PaymentMethod, PaymentStatus
from app.modules.payments.exceptions import (
    PaymentAllocationAmountExceededError,
    PaymentAllocationInvoiceInvalidStatusError,
    PaymentAllocationInvoiceNotFoundError,
    PaymentAllocationPaymentNotDraftError,
    PaymentNoAllocationsError,
    PaymentNotDraftError,
    PaymentNotFoundError,
    PaymentNumberConflictError,
    PaymentTotalsInvalidError,
)
from app.modules.payments.models import Payment, PaymentAllocation, PaymentSequence
from app.modules.payments.schemas import PaymentListParams
from app.modules.payments.service import PaymentService


class _FakeRepo:
    def __init__(self, rows: list[Payment], total: int) -> None:
        self.rows = rows
        self.total = total
        self.last_call: dict[str, Any] | None = None

    async def search(self, tenant_id: uuid.UUID, **kwargs: Any) -> tuple[list[Payment], int]:
        self.last_call = {"tenant_id": tenant_id, **kwargs}
        return self.rows, self.total


def _make_payment(**overrides: Any) -> Payment:
    """A Payment that satisfies PaymentResponse validation without touching
    the DB - the non-nullable columns normally filled by server_default /
    TimestampMixin need explicit values since this object is never flushed."""
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "company_id": uuid.uuid4(),
        "payment_number": None,
        "payment_date": datetime.now(UTC).date(),
        "payment_method": PaymentMethod.CHEQUE,
        "amount": Decimal("1000.00"),
        "allocated_amount": Decimal("0"),
        "unallocated_amount": Decimal("1000.00"),
        "status": PaymentStatus.DRAFT,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return Payment(**defaults)


def _service_with_fake_repo(rows: list[Payment], total: int) -> tuple[PaymentService, _FakeRepo]:
    service = PaymentService.__new__(PaymentService)
    fake_repo = _FakeRepo(rows, total)
    service._repo = fake_repo  # type: ignore[assignment]
    return service, fake_repo


class TestListPaymentsPaginationMath:
    async def test_first_page_of_several(self) -> None:
        rows = [_make_payment() for _ in range(2)]
        service, fake_repo = _service_with_fake_repo(rows, total=5)

        result = await service.list_payments(
            tenant_id=uuid.uuid4(), params=PaymentListParams(page=1, page_size=2)
        )

        assert len(result.data) == 2
        assert result.meta.total_records == 5
        assert result.meta.total_pages == 3
        assert result.meta.current_page == 1
        assert result.meta.has_previous is False
        assert result.meta.has_next is True
        assert fake_repo.last_call is not None

    async def test_last_page_has_no_next(self) -> None:
        rows = [_make_payment()]
        service, _ = _service_with_fake_repo(rows, total=5)

        result = await service.list_payments(
            tenant_id=uuid.uuid4(), params=PaymentListParams(page=3, page_size=2)
        )

        assert result.meta.has_next is False
        assert result.meta.has_previous is True

    async def test_empty_result_gives_zero_pages(self) -> None:
        service, _ = _service_with_fake_repo([], total=0)

        result = await service.list_payments(
            tenant_id=uuid.uuid4(), params=PaymentListParams(page=1, page_size=20)
        )

        assert result.data == []
        assert result.meta.total_records == 0
        assert result.meta.total_pages == 0
        assert result.meta.has_next is False
        assert result.meta.has_previous is False

    async def test_filters_are_forwarded_to_the_repository_without_a_query(self) -> None:
        service, fake_repo = _service_with_fake_repo([], total=0)
        tenant_id = uuid.uuid4()
        company_id = uuid.uuid4()

        await service.list_payments(
            tenant_id=tenant_id,
            params=PaymentListParams(
                status=PaymentStatus.DRAFT,
                company_id=company_id,
                payment_method=PaymentMethod.UPI,
                sort="-amount",
                page=2,
                page_size=10,
            ),
        )

        assert fake_repo.last_call == {
            "tenant_id": tenant_id,
            "q": None,
            "q_company_ids": None,
            "status": PaymentStatus.DRAFT,
            "company_id": company_id,
            "payment_method": PaymentMethod.UPI,
            "payment_date_from": None,
            "payment_date_to": None,
            "sort": "-amount",
            "page": 2,
            "page_size": 10,
        }


class TestSyncUnallocated:
    def test_recomputes_from_amount_minus_allocated(self) -> None:
        payment = _make_payment(amount=Decimal("1000.00"), allocated_amount=Decimal("0"))
        payment.amount = Decimal("2000.00")
        PaymentService._sync_unallocated(payment)
        assert payment.unallocated_amount == Decimal("2000.00")

    def test_accounts_for_a_nonzero_allocated_amount(self) -> None:
        """Only reachable via PaymentUpdateRequest's own path in practice -
        allocation mutations recompute both fields via
        _recalculate_payment_allocation_totals instead - but the formula
        itself must stay correct for either caller."""
        payment = _make_payment(amount=Decimal("1000.00"), allocated_amount=Decimal("400.00"))
        PaymentService._sync_unallocated(payment)
        assert payment.unallocated_amount == Decimal("600.00")


class TestEnsureDraft:
    def test_draft_payment_passes(self) -> None:
        payment = _make_payment(status=PaymentStatus.DRAFT)
        PaymentService._ensure_draft(payment)  # must not raise

    @pytest.mark.parametrize("status", [PaymentStatus.POSTED, PaymentStatus.CANCELLED])
    def test_non_draft_payment_raises(self, status: PaymentStatus) -> None:
        payment = _make_payment(status=status)
        with pytest.raises(PaymentNotDraftError):
            PaymentService._ensure_draft(payment)


class TestEnsureDraftForAllocation:
    def test_draft_payment_passes(self) -> None:
        payment = _make_payment(status=PaymentStatus.DRAFT)
        PaymentService._ensure_draft_for_allocation(payment)  # must not raise

    @pytest.mark.parametrize("status", [PaymentStatus.POSTED, PaymentStatus.CANCELLED])
    def test_non_draft_payment_raises_the_allocation_specific_error(
        self, status: PaymentStatus
    ) -> None:
        """Distinct from _ensure_draft's PaymentNotDraftError - allocation
        endpoints report their own error code (see
        PaymentAllocationPaymentNotDraftError's docstring)."""
        payment = _make_payment(status=status)
        with pytest.raises(PaymentAllocationPaymentNotDraftError):
            PaymentService._ensure_draft_for_allocation(payment)


class TestValidateAllocationCeilings:
    def test_passes_within_both_ceilings(self) -> None:
        PaymentService._validate_allocation_ceilings(
            allocated_amount=Decimal("500.00"),
            invoice_balance=Decimal("1000.00"),
            payment_unallocated=Decimal("800.00"),
        )  # must not raise

    def test_exceeding_invoice_balance_raises_the_shared_amount_exceeded_error(self) -> None:
        with pytest.raises(PaymentAllocationAmountExceededError) as exc_info:
            PaymentService._validate_allocation_ceilings(
                allocated_amount=Decimal("1000.01"),
                invoice_balance=Decimal("1000.00"),
                payment_unallocated=Decimal("5000.00"),
            )
        assert "exceeds the invoice's balance" in str(exc_info.value)

    def test_exceeding_payment_unallocated_raises_the_shared_amount_exceeded_error(self) -> None:
        with pytest.raises(PaymentAllocationAmountExceededError) as exc_info:
            PaymentService._validate_allocation_ceilings(
                allocated_amount=Decimal("500.01"),
                invoice_balance=Decimal("5000.00"),
                payment_unallocated=Decimal("500.00"),
            )
        assert "exceeds the payment's unallocated amount" in str(exc_info.value)


class TestToAllocationResponse:
    def test_maps_every_field(self) -> None:
        allocation = PaymentAllocation(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            payment_id=uuid.uuid4(),
            invoice_id=uuid.uuid4(),
            allocated_amount=Decimal("500.00"),
            created_at=datetime.now(UTC),
        )
        response = PaymentService._to_allocation_response(allocation)
        assert response.id == allocation.id
        assert response.payment_id == allocation.payment_id
        assert response.invoice_id == allocation.invoice_id
        assert response.allocated_amount == Decimal("500.00")


class _FakeAllocationRepo:
    def __init__(self, total_allocated: Decimal) -> None:
        self.total_allocated = total_allocated
        self.summed_for: tuple[uuid.UUID, uuid.UUID] | None = None

    async def sum_allocated_amount(self, payment_id: uuid.UUID, tenant_id: uuid.UUID) -> Decimal:
        self.summed_for = (payment_id, tenant_id)
        return self.total_allocated


class TestRecalculatePaymentAllocationTotals:
    async def test_recomputes_both_fields_from_the_summed_allocations(self) -> None:
        service = PaymentService.__new__(PaymentService)
        fake_repo = _FakeAllocationRepo(Decimal("600.00"))
        service._repo = fake_repo  # type: ignore[assignment]
        payment = _make_payment(amount=Decimal("1000.00"))
        tenant_id = uuid.uuid4()

        await service._recalculate_payment_allocation_totals(payment, tenant_id)

        assert payment.allocated_amount == Decimal("600.00")
        assert payment.unallocated_amount == Decimal("400.00")
        assert fake_repo.summed_for == (payment.id, tenant_id)

    async def test_no_active_allocations_leaves_everything_unallocated(self) -> None:
        service = PaymentService.__new__(PaymentService)
        fake_repo = _FakeAllocationRepo(Decimal("0"))
        service._repo = fake_repo  # type: ignore[assignment]
        payment = _make_payment(amount=Decimal("1000.00"), allocated_amount=Decimal("600.00"))

        await service._recalculate_payment_allocation_totals(payment, uuid.uuid4())

        assert payment.allocated_amount == Decimal("0")
        assert payment.unallocated_amount == Decimal("1000.00")


class _InvoiceStub:
    """Stands in for an InvoiceResponse - only .status/.balance_amount are
    read by PaymentService's allocation validation."""

    def __init__(
        self,
        invoice_id: uuid.UUID | None = None,
        *,
        status: InvoiceStatus = InvoiceStatus.ISSUED,
        balance_amount: Decimal = Decimal("1000.00"),
    ) -> None:
        self.id = invoice_id or uuid.uuid4()
        self.status = status
        self.balance_amount = balance_amount


class _FakeInvoiceService:
    """Stands in for InvoiceService.get - the only entry point
    _ensure_invoice_allocatable calls on it (ARCHITECTURE.md §2 -
    cross-module access goes through the other module's service, never its
    repository)."""

    def __init__(self, *, invoice: _InvoiceStub | None = None, raises: bool = False) -> None:
        self.invoice = invoice
        self.raises = raises
        self.get_calls: list[tuple[uuid.UUID, uuid.UUID]] = []

    async def get(self, invoice_id: uuid.UUID, *, tenant_id: uuid.UUID) -> _InvoiceStub:
        self.get_calls.append((invoice_id, tenant_id))
        if self.raises:
            raise InvoiceNotFoundError("Invoice not found")
        assert self.invoice is not None
        return self.invoice


class TestEnsureInvoiceAllocatable:
    """PaymentService._ensure_invoice_allocatable - shared by create_allocation
    (always allow_paid=False) and update_allocation (allow_paid depending on
    whether the invoice is being retargeted, see its docstring)."""

    async def test_issued_invoice_passes_without_allow_paid(self) -> None:
        invoice = _InvoiceStub(status=InvoiceStatus.ISSUED)
        service = PaymentService.__new__(PaymentService)
        service._invoice_service = _FakeInvoiceService(invoice=invoice)  # type: ignore[assignment]

        result = await service._ensure_invoice_allocatable(invoice.id, uuid.uuid4())

        assert result is invoice  # type: ignore[comparison-overlap]

    async def test_partially_paid_invoice_passes_without_allow_paid(self) -> None:
        invoice = _InvoiceStub(status=InvoiceStatus.PARTIALLY_PAID)
        service = PaymentService.__new__(PaymentService)
        service._invoice_service = _FakeInvoiceService(invoice=invoice)  # type: ignore[assignment]

        await service._ensure_invoice_allocatable(invoice.id, uuid.uuid4())  # must not raise

    @pytest.mark.parametrize(
        "status", [InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED, InvoiceStatus.PAID]
    )
    async def test_other_statuses_raise_without_allow_paid(self, status: InvoiceStatus) -> None:
        invoice = _InvoiceStub(status=status)
        service = PaymentService.__new__(PaymentService)
        service._invoice_service = _FakeInvoiceService(invoice=invoice)  # type: ignore[assignment]

        with pytest.raises(PaymentAllocationInvoiceInvalidStatusError):
            await service._ensure_invoice_allocatable(invoice.id, uuid.uuid4())

    async def test_paid_invoice_passes_with_allow_paid(self) -> None:
        """The update_allocation case: editing/removing money from an
        invoice this allocation already fully paid must stay possible."""
        invoice = _InvoiceStub(status=InvoiceStatus.PAID)
        service = PaymentService.__new__(PaymentService)
        service._invoice_service = _FakeInvoiceService(invoice=invoice)  # type: ignore[assignment]

        await service._ensure_invoice_allocatable(
            invoice.id, uuid.uuid4(), allow_paid=True
        )  # must not raise

    @pytest.mark.parametrize("status", [InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED])
    async def test_draft_and_cancelled_still_raise_with_allow_paid(
        self, status: InvoiceStatus
    ) -> None:
        invoice = _InvoiceStub(status=status)
        service = PaymentService.__new__(PaymentService)
        service._invoice_service = _FakeInvoiceService(invoice=invoice)  # type: ignore[assignment]

        with pytest.raises(PaymentAllocationInvoiceInvalidStatusError):
            await service._ensure_invoice_allocatable(invoice.id, uuid.uuid4(), allow_paid=True)

    async def test_raises_not_found_when_invoice_missing(self) -> None:
        service = PaymentService.__new__(PaymentService)
        service._invoice_service = _FakeInvoiceService(raises=True)  # type: ignore[assignment]

        with pytest.raises(PaymentAllocationInvoiceNotFoundError):
            await service._ensure_invoice_allocatable(uuid.uuid4(), uuid.uuid4())


class _FakeRecalcAllocationRepo:
    """Stands in for PaymentRepository.sum_allocated_amount_by_invoice - the
    only repository method _recalculate_invoice_and_company calls."""

    def __init__(self, total_allocated: Decimal) -> None:
        self.total_allocated = total_allocated
        self.summed_for: tuple[uuid.UUID, uuid.UUID] | None = None

    async def sum_allocated_amount_by_invoice(
        self, invoice_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Decimal:
        self.summed_for = (invoice_id, tenant_id)
        return self.total_allocated


class _FakeReconciliationInvoiceService:
    """Stands in for InvoiceService.recalculate_payment_totals - the only
    entry point _recalculate_invoice_and_company calls."""

    def __init__(self) -> None:
        self.recalculate_calls: list[tuple[uuid.UUID, uuid.UUID, Decimal]] = []

    async def recalculate_payment_totals(
        self, invoice_id: uuid.UUID, *, tenant_id: uuid.UUID, total_allocated: Decimal
    ) -> None:
        self.recalculate_calls.append((invoice_id, tenant_id, total_allocated))


class TestRecalculateInvoiceAndCompany:
    """PaymentService._recalculate_invoice_and_company - Sprint 10 Session 4's
    entry point into the outstanding engine, called after every allocation
    mutation. It sums this invoice's allocations via its own
    PaymentRepository (never InvoiceRepository) and hands the total to
    InvoiceService."""

    async def test_sums_via_its_own_repository_and_forwards_to_invoice_service(self) -> None:
        service = PaymentService.__new__(PaymentService)
        fake_repo = _FakeRecalcAllocationRepo(Decimal("750.00"))
        fake_invoice_service = _FakeReconciliationInvoiceService()
        service._repo = fake_repo  # type: ignore[assignment]
        service._invoice_service = fake_invoice_service  # type: ignore[assignment]
        invoice_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        await service._recalculate_invoice_and_company(invoice_id, tenant_id)

        assert fake_repo.summed_for == (invoice_id, tenant_id)
        assert fake_invoice_service.recalculate_calls == [
            (invoice_id, tenant_id, Decimal("750.00"))
        ]


class _FakeIntegrityError(Exception):
    """Stands in for sqlalchemy.exc.IntegrityError - only `.orig` is read.
    Mirrors InvoiceService/CompanyService's test-suite fakes of the same
    shape."""

    def __init__(self, constraint_name: str) -> None:
        super().__init__("integrity error")

        class _FakeDriverError(Exception):
            def __init__(self, constraint_name: str) -> None:
                super().__init__("duplicate key value violates unique constraint")
                self.__cause__ = self._FakeConstraintCause(constraint_name)

            class _FakeConstraintCause(Exception):
                def __init__(self, constraint_name: str) -> None:
                    super().__init__("fake constraint violation")
                    self.constraint_name = constraint_name

        self.orig = _FakeDriverError(constraint_name)


class TestTranslateIntegrityError:
    def test_allocation_unique_constraint_maps_to_conflict_error(self) -> None:
        exc = _FakeIntegrityError("ix_payment_allocations_payment_invoice")
        result = PaymentService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert type(result) is ConflictError
        assert "already has an allocation" in result.message

    def test_payment_number_unique_constraint_maps_to_number_conflict_error(self) -> None:
        """Defensive backstop - _allocate_payment_number's FOR UPDATE
        locking should make this unreachable in normal operation, but the
        constraint firing must still surface a clean 409, not a raw 500."""
        exc = _FakeIntegrityError("ix_payments_tenant_payment_number")
        result = PaymentService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert isinstance(result, PaymentNumberConflictError)

    def test_unknown_constraint_falls_back_to_generic_conflict(self) -> None:
        exc = _FakeIntegrityError("some_other_constraint")
        result = PaymentService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert type(result) is ConflictError

    def test_missing_orig_falls_back_to_generic_conflict(self) -> None:
        class _BareError(Exception):
            orig = None

        result = PaymentService._translate_integrity_error(_BareError())  # type: ignore[arg-type]
        assert type(result) is ConflictError


class _FakePostRepo:
    """Stands in for PaymentRepository - only the methods post() calls."""

    def __init__(
        self,
        *,
        locked_payment: Payment | None,
        has_allocations: bool = True,
        total_allocated: Decimal = Decimal("0"),
    ) -> None:
        self.locked_payment = locked_payment
        self._has_allocations = has_allocations
        self.total_allocated = total_allocated
        self.get_for_update_calls: list[tuple[uuid.UUID, uuid.UUID]] = []
        self.has_allocations_calls: list[tuple[uuid.UUID, uuid.UUID]] = []
        self.sequences: dict[tuple[uuid.UUID, str, str], PaymentSequence] = {}
        self.ensure_sequence_calls: list[tuple[uuid.UUID, str, str]] = []

    async def get_by_id_for_update(
        self, payment_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Payment | None:
        self.get_for_update_calls.append((payment_id, tenant_id))
        return self.locked_payment

    async def has_allocations(self, payment_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        self.has_allocations_calls.append((payment_id, tenant_id))
        return self._has_allocations

    async def sum_allocated_amount(self, payment_id: uuid.UUID, tenant_id: uuid.UUID) -> Decimal:
        return self.total_allocated

    async def ensure_sequence_row(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> None:
        self.ensure_sequence_calls.append((tenant_id, prefix, fiscal_year))
        key = (tenant_id, prefix, fiscal_year)
        if key not in self.sequences:
            self.sequences[key] = PaymentSequence(
                tenant_id=tenant_id, prefix=prefix, fiscal_year=fiscal_year, last_number=0
            )

    async def get_sequence_for_update(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> PaymentSequence:
        return self.sequences[(tenant_id, prefix, fiscal_year)]


class _FakePostSession:
    """Stands in for AsyncSession - post() only ever calls .rollback() on it
    along the validation-failure paths these unit tests cover (the happy
    path's flush/commit/refresh is integration-tested instead)."""

    def __init__(self) -> None:
        self.rollback_calls = 0

    async def rollback(self) -> None:
        self.rollback_calls += 1


def _post_service_with_fakes(
    *,
    payment: Payment | None,
    has_allocations: bool = True,
    total_allocated: Decimal = Decimal("0"),
) -> tuple[PaymentService, _FakePostRepo, _FakePostSession]:
    service = PaymentService.__new__(PaymentService)
    fake_repo = _FakePostRepo(
        locked_payment=payment, has_allocations=has_allocations, total_allocated=total_allocated
    )
    fake_session = _FakePostSession()
    service._repo = fake_repo  # type: ignore[assignment]
    service._session = fake_session  # type: ignore[assignment]
    return service, fake_repo, fake_session


class TestPostValidation:
    """Unit-level coverage for post()'s validation steps that raise before
    any real database commit is needed (not-found, not-draft, no-
    allocations, and the totals-invariant defensive check). The full happy
    path - session flush/commit/refresh, real FOR UPDATE locking, actual
    payment numbering - is integration-tested instead
    (tests/integration/test_payment_post.py)."""

    async def test_raises_not_found_when_payment_missing(self) -> None:
        service, fake_repo, fake_session = _post_service_with_fakes(payment=None)
        payment_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        with pytest.raises(PaymentNotFoundError):
            await service.post(payment_id, tenant_id=tenant_id, actor_id=uuid.uuid4())

        assert fake_repo.get_for_update_calls == [(payment_id, tenant_id)]
        assert fake_session.rollback_calls == 1

    @pytest.mark.parametrize("status", [PaymentStatus.POSTED, PaymentStatus.CANCELLED])
    async def test_raises_not_draft_for_non_draft_statuses(self, status: PaymentStatus) -> None:
        """Covers "cannot post twice" (POSTED) and "cannot post a cancelled
        payment" (CANCELLED) with the same guard."""
        payment = _make_payment(status=status)
        service, _, fake_session = _post_service_with_fakes(payment=payment)

        with pytest.raises(PaymentNotDraftError):
            await service.post(payment.id, tenant_id=payment.tenant_id, actor_id=uuid.uuid4())

        assert fake_session.rollback_calls == 1

    async def test_raises_no_allocations_when_the_payment_has_none(self) -> None:
        payment = _make_payment(status=PaymentStatus.DRAFT)
        service, fake_repo, fake_session = _post_service_with_fakes(
            payment=payment, has_allocations=False
        )

        with pytest.raises(PaymentNoAllocationsError):
            await service.post(payment.id, tenant_id=payment.tenant_id, actor_id=uuid.uuid4())

        assert fake_repo.has_allocations_calls == [(payment.id, payment.tenant_id)]
        assert fake_session.rollback_calls == 1

    async def test_raises_totals_invalid_when_the_invariant_is_violated(self) -> None:
        """Not reachable through the real recompute step -
        calculate_payment_allocation_totals always keeps
        allocated_amount + unallocated_amount == amount true by
        construction, whatever total_allocated is - so this proves the
        defensive check itself fires correctly, by monkey-patching the
        recompute step to simulate a corrupted row (e.g. from a future
        refactor bug)."""
        payment = _make_payment(status=PaymentStatus.DRAFT, amount=Decimal("1000.00"))
        service, _, fake_session = _post_service_with_fakes(payment=payment)

        async def _corrupt_recalculate(target: Payment, tenant_id: uuid.UUID) -> None:
            target.allocated_amount = Decimal("999.00")
            target.unallocated_amount = Decimal("999.00")

        service._recalculate_payment_allocation_totals = _corrupt_recalculate  # type: ignore[assignment]

        with pytest.raises(PaymentTotalsInvalidError):
            await service.post(payment.id, tenant_id=payment.tenant_id, actor_id=uuid.uuid4())

        assert fake_session.rollback_calls == 1

    async def test_locked_lookup_is_scoped_to_the_given_tenant(self) -> None:
        payment = _make_payment(status=PaymentStatus.POSTED)
        service, fake_repo, _ = _post_service_with_fakes(payment=payment)
        tenant_id = uuid.uuid4()

        with pytest.raises(PaymentNotDraftError):
            await service.post(payment.id, tenant_id=tenant_id, actor_id=uuid.uuid4())

        assert fake_repo.get_for_update_calls == [(payment.id, tenant_id)]


class TestAllocatePaymentNumber:
    """PaymentService._allocate_payment_number - the counter-orchestration
    logic (fiscal year computation, ensure-then-lock, increment). The
    actual concurrency guarantee (SELECT ... FOR UPDATE serializing two real
    transactions) can only be verified against a real database - see
    tests/integration/test_payment_post.py."""

    async def test_first_allocation_for_a_fiscal_year_starts_at_one(self) -> None:
        service = PaymentService.__new__(PaymentService)
        fake_repo = _FakePostRepo(locked_payment=None)
        service._repo = fake_repo  # type: ignore[assignment]
        payment = _make_payment(payment_date=date(2026, 7, 23))

        number = await service._allocate_payment_number(payment, uuid.uuid4())

        assert number == "PAY/2026-27/00001"

    async def test_second_allocation_for_the_same_fiscal_year_increments(self) -> None:
        service = PaymentService.__new__(PaymentService)
        fake_repo = _FakePostRepo(locked_payment=None)
        service._repo = fake_repo  # type: ignore[assignment]
        payment = _make_payment(payment_date=date(2026, 7, 23))
        tenant_id = uuid.uuid4()

        await service._allocate_payment_number(payment, tenant_id)
        second = await service._allocate_payment_number(payment, tenant_id)

        assert second == "PAY/2026-27/00002"

    async def test_different_fiscal_years_get_independent_counters(self) -> None:
        service = PaymentService.__new__(PaymentService)
        fake_repo = _FakePostRepo(locked_payment=None)
        service._repo = fake_repo  # type: ignore[assignment]
        tenant_id = uuid.uuid4()
        early_fy = _make_payment(payment_date=date(2026, 3, 15))  # FY 2025-26
        late_fy = _make_payment(payment_date=date(2026, 7, 23))  # FY 2026-27

        early_number = await service._allocate_payment_number(early_fy, tenant_id)
        late_number = await service._allocate_payment_number(late_fy, tenant_id)

        assert early_number == "PAY/2025-26/00001"
        assert late_number == "PAY/2026-27/00001"

    async def test_different_tenants_get_independent_counters(self) -> None:
        service = PaymentService.__new__(PaymentService)
        fake_repo = _FakePostRepo(locked_payment=None)
        service._repo = fake_repo  # type: ignore[assignment]
        payment = _make_payment(payment_date=date(2026, 7, 23))

        first_tenant_number = await service._allocate_payment_number(payment, uuid.uuid4())
        second_tenant_number = await service._allocate_payment_number(payment, uuid.uuid4())

        assert first_tenant_number == "PAY/2026-27/00001"
        assert second_tenant_number == "PAY/2026-27/00001"

    async def test_ensures_sequence_row_before_locking_it(self) -> None:
        service = PaymentService.__new__(PaymentService)
        fake_repo = _FakePostRepo(locked_payment=None)
        service._repo = fake_repo  # type: ignore[assignment]
        payment = _make_payment(payment_date=date(2026, 7, 23))
        tenant_id = uuid.uuid4()

        await service._allocate_payment_number(payment, tenant_id)

        assert fake_repo.ensure_sequence_calls == [(tenant_id, "PAY", "2026-27")]
