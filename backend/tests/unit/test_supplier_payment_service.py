import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.core.errors import ConflictError
from app.modules.purchase.constants import PurchaseStatus
from app.modules.purchase.exceptions import PurchaseBillNotFoundError
from app.modules.purchase.schemas import PurchaseBillResponse
from app.modules.supplier_payments.constants import PaymentMethod, SupplierPaymentStatus
from app.modules.supplier_payments.exceptions import (
    SupplierPaymentAllocationAmountExceededError,
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
from app.modules.supplier_payments.models import (
    SupplierPayment,
    SupplierPaymentAllocation,
    SupplierPaymentSequence,
)
from app.modules.supplier_payments.schemas import (
    SupplierPaymentListParams,
    SupplierPaymentUpdateRequest,
)
from app.modules.supplier_payments.service import SupplierPaymentService
from app.modules.suppliers.constants import SupplierStatus
from app.modules.suppliers.exceptions import SupplierNotFoundError
from app.modules.suppliers.schemas import SupplierResponse


class _FakeConstraintCause(Exception):
    def __init__(self, constraint_name: str) -> None:
        super().__init__("fake constraint violation")
        self.constraint_name = constraint_name


class _FakeDriverError(Exception):
    def __init__(self, constraint_name: str) -> None:
        super().__init__("duplicate key value violates unique constraint")
        self.__cause__ = _FakeConstraintCause(constraint_name)


class _FakeIntegrityError(Exception):
    def __init__(self, constraint_name: str) -> None:
        super().__init__("integrity error")
        self.orig = _FakeDriverError(constraint_name)


class _FakeRepo:
    def __init__(self, rows: list[SupplierPayment], total: int) -> None:
        self.rows = rows
        self.total = total
        self.last_call: dict[str, Any] | None = None

    async def search(
        self, tenant_id: uuid.UUID, **kwargs: Any
    ) -> tuple[list[SupplierPayment], int]:
        self.last_call = {"tenant_id": tenant_id, **kwargs}
        return self.rows, self.total


class _FakeSupplierService:
    """Stands in for SupplierService - SupplierPaymentService must call
    this, never SupplierRepository directly (ARCHITECTURE.md §2, TASKS.md
    Sprint 12 Session 2)."""

    def __init__(
        self,
        *,
        supplier: SupplierResponse | None = None,
        raise_not_found: bool = False,
        name_matches: list[uuid.UUID] | None = None,
    ) -> None:
        self._supplier = supplier
        self._raise_not_found = raise_not_found
        self._name_matches = name_matches or []
        self.get_calls: list[tuple[uuid.UUID, uuid.UUID]] = []
        self.find_ids_by_name_calls: list[tuple[uuid.UUID, str]] = []

    async def get(self, supplier_id: uuid.UUID, *, tenant_id: uuid.UUID) -> SupplierResponse:
        self.get_calls.append((supplier_id, tenant_id))
        if self._raise_not_found:
            raise SupplierNotFoundError("Supplier not found")
        assert self._supplier is not None
        return self._supplier

    async def find_ids_by_name(self, tenant_id: uuid.UUID, q: str) -> list[uuid.UUID]:
        self.find_ids_by_name_calls.append((tenant_id, q))
        return self._name_matches


def _make_supplier_response(**overrides: Any) -> SupplierResponse:
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "code": "SUP-1",
        "name": "Test Supplier",
        "legal_name": None,
        "gstin": None,
        "phone": None,
        "email": None,
        "address": None,
        "city": None,
        "state": None,
        "country": None,
        "contact_person": None,
        "credit_days": 0,
        "opening_balance": Decimal("0"),
        "outstanding_amount": Decimal("0"),
        "status": SupplierStatus.ACTIVE,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return SupplierResponse(**defaults)


def _make_supplier_payment(**overrides: Any) -> SupplierPayment:
    """A SupplierPayment that satisfies SupplierPaymentResponse validation
    without touching the DB - the non-nullable columns normally filled by
    server_default / TimestampMixin need explicit values since this object
    is never flushed."""
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "supplier_id": uuid.uuid4(),
        "payment_number": None,
        "payment_date": date(2026, 7, 23),
        "payment_method": PaymentMethod.CHEQUE,
        "amount": Decimal("150000.00"),
        "allocated_amount": Decimal("0"),
        "unallocated_amount": Decimal("150000.00"),
        "status": SupplierPaymentStatus.DRAFT,
        "posted_at": None,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return SupplierPayment(**defaults)


def _service_with_fakes(
    rows: list[SupplierPayment],
    total: int,
    *,
    supplier_service: _FakeSupplierService | None = None,
) -> tuple[SupplierPaymentService, _FakeRepo, _FakeSupplierService]:
    service = SupplierPaymentService.__new__(SupplierPaymentService)
    fake_repo = _FakeRepo(rows, total)
    fake_supplier_service = supplier_service or _FakeSupplierService(
        supplier=_make_supplier_response()
    )
    service._repo = fake_repo  # type: ignore[assignment]
    service._supplier_service = fake_supplier_service  # type: ignore[assignment]
    return service, fake_repo, fake_supplier_service


class _FakePurchaseService:
    """Stands in for PurchaseService - SupplierPaymentService must call
    this, never PurchaseRepository directly (ARCHITECTURE.md §2, TASKS.md
    Sprint 12 Session 3)."""

    def __init__(
        self,
        *,
        purchase_bill: PurchaseBillResponse | None = None,
        raise_not_found: bool = False,
    ) -> None:
        self._purchase_bill = purchase_bill
        self._raise_not_found = raise_not_found
        self.get_calls: list[tuple[uuid.UUID, uuid.UUID]] = []
        self.recalculate_payment_totals_calls: list[tuple[uuid.UUID, uuid.UUID, Decimal]] = []

    async def get(
        self, purchase_bill_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> PurchaseBillResponse:
        self.get_calls.append((purchase_bill_id, tenant_id))
        if self._raise_not_found:
            raise PurchaseBillNotFoundError("Purchase bill not found")
        assert self._purchase_bill is not None
        return self._purchase_bill

    async def recalculate_payment_totals(
        self, purchase_bill_id: uuid.UUID, *, tenant_id: uuid.UUID, total_allocated: Decimal
    ) -> None:
        self.recalculate_payment_totals_calls.append((purchase_bill_id, tenant_id, total_allocated))


def _make_purchase_bill_response(**overrides: Any) -> PurchaseBillResponse:
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "supplier_id": uuid.uuid4(),
        "bill_number": "PUR/2026-27/00001",
        "bill_date": date(2026, 7, 23),
        "due_date": None,
        "status": PurchaseStatus.POSTED,
        "subtotal": Decimal("23625.00"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("22500.00"),
        "tax_amount": Decimal("1125.00"),
        "transport_charge": Decimal("0"),
        "other_charge": Decimal("0"),
        "round_off": Decimal("0"),
        "total_amount": Decimal("23625.00"),
        "paid_amount": Decimal("0"),
        "balance_amount": Decimal("23625.00"),
        "remarks": None,
        "posted_at": now,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return PurchaseBillResponse(**defaults)


def _make_allocation(**overrides: Any) -> SupplierPaymentAllocation:
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "supplier_payment_id": uuid.uuid4(),
        "purchase_bill_id": uuid.uuid4(),
        "allocated_amount": Decimal("90000.00"),
        "created_at": now,
    }
    defaults.update(overrides)
    return SupplierPaymentAllocation(**defaults)


class TestListSupplierPaymentsPaginationMath:
    async def test_first_page_of_several(self) -> None:
        rows = [_make_supplier_payment() for _ in range(2)]
        service, fake_repo, _ = _service_with_fakes(rows, total=5)

        result = await service.list_supplier_payments(
            tenant_id=uuid.uuid4(), params=SupplierPaymentListParams(page=1, page_size=2)
        )

        assert len(result.data) == 2
        assert result.meta.total_records == 5
        assert result.meta.total_pages == 3
        assert result.meta.current_page == 1
        assert result.meta.has_previous is False
        assert result.meta.has_next is True
        assert fake_repo.last_call is not None

    async def test_last_page_has_no_next(self) -> None:
        rows = [_make_supplier_payment()]
        service, _, _ = _service_with_fakes(rows, total=5)

        result = await service.list_supplier_payments(
            tenant_id=uuid.uuid4(), params=SupplierPaymentListParams(page=3, page_size=2)
        )

        assert result.meta.has_next is False
        assert result.meta.has_previous is True

    async def test_empty_result_gives_zero_pages(self) -> None:
        service, _, _ = _service_with_fakes([], total=0)

        result = await service.list_supplier_payments(
            tenant_id=uuid.uuid4(), params=SupplierPaymentListParams(page=1, page_size=20)
        )

        assert result.data == []
        assert result.meta.total_records == 0
        assert result.meta.total_pages == 0
        assert result.meta.has_next is False
        assert result.meta.has_previous is False

    async def test_q_resolves_supplier_name_matches_before_searching(self) -> None:
        match_id = uuid.uuid4()
        fake_supplier_service = _FakeSupplierService(
            supplier=_make_supplier_response(), name_matches=[match_id]
        )
        service, fake_repo, _ = _service_with_fakes(
            [], total=0, supplier_service=fake_supplier_service
        )
        tenant_id = uuid.uuid4()

        await service.list_supplier_payments(
            tenant_id=tenant_id, params=SupplierPaymentListParams(q="Coastal")
        )

        assert fake_supplier_service.find_ids_by_name_calls == [(tenant_id, "Coastal")]
        assert fake_repo.last_call is not None
        assert fake_repo.last_call["q_supplier_ids"] == [match_id]

    async def test_blank_q_does_not_call_supplier_service(self) -> None:
        fake_supplier_service = _FakeSupplierService(supplier=_make_supplier_response())
        service, fake_repo, _ = _service_with_fakes(
            [], total=0, supplier_service=fake_supplier_service
        )

        await service.list_supplier_payments(
            tenant_id=uuid.uuid4(), params=SupplierPaymentListParams(q=None)
        )

        assert fake_supplier_service.find_ids_by_name_calls == []
        assert fake_repo.last_call is not None
        assert fake_repo.last_call["q_supplier_ids"] is None

    async def test_filters_are_forwarded_to_the_repository_without_a_query(self) -> None:
        service, fake_repo, _ = _service_with_fakes([], total=0)
        tenant_id = uuid.uuid4()
        supplier_id = uuid.uuid4()

        await service.list_supplier_payments(
            tenant_id=tenant_id,
            params=SupplierPaymentListParams(
                status=SupplierPaymentStatus.DRAFT,
                supplier_id=supplier_id,
                payment_method=PaymentMethod.UPI,
                sort="-payment_date",
                page=2,
                page_size=10,
            ),
        )

        assert fake_repo.last_call == {
            "tenant_id": tenant_id,
            "q": None,
            "q_supplier_ids": None,
            "status": SupplierPaymentStatus.DRAFT,
            "supplier_id": supplier_id,
            "payment_method": PaymentMethod.UPI,
            "payment_date_from": None,
            "payment_date_to": None,
            "sort": "-payment_date",
            "page": 2,
            "page_size": 10,
        }


class TestSyncUnallocated:
    def test_recomputes_from_amount_minus_allocated(self) -> None:
        payment = _make_supplier_payment(amount=Decimal("1000.00"), allocated_amount=Decimal("0"))
        payment.amount = Decimal("2000.00")
        SupplierPaymentService._sync_unallocated(payment)
        assert payment.unallocated_amount == Decimal("2000.00")

    def test_accounts_for_a_nonzero_allocated_amount(self) -> None:
        """Only reachable via SupplierPaymentUpdateRequest's own path in
        practice - allocation mutations (Session 3) will recompute both
        fields differently - but the formula itself must stay correct for
        either caller."""
        payment = _make_supplier_payment(
            amount=Decimal("1000.00"), allocated_amount=Decimal("400.00")
        )
        SupplierPaymentService._sync_unallocated(payment)
        assert payment.unallocated_amount == Decimal("600.00")


class TestEnsureDraft:
    def test_draft_payment_passes(self) -> None:
        payment = _make_supplier_payment(status=SupplierPaymentStatus.DRAFT)
        SupplierPaymentService._ensure_draft(payment)  # must not raise

    @pytest.mark.parametrize(
        "status", [SupplierPaymentStatus.POSTED, SupplierPaymentStatus.CANCELLED]
    )
    def test_non_draft_payment_raises(self, status: SupplierPaymentStatus) -> None:
        payment = _make_supplier_payment(status=status)
        with pytest.raises(SupplierPaymentNotDraftError):
            SupplierPaymentService._ensure_draft(payment)


class TestEnsureSupplierActive:
    async def test_returns_the_supplier_when_active(self) -> None:
        supplier = _make_supplier_response(status=SupplierStatus.ACTIVE)
        service, _, fake_supplier_service = _service_with_fakes(
            [], 0, supplier_service=_FakeSupplierService(supplier=supplier)
        )
        tenant_id = uuid.uuid4()

        result = await service._ensure_supplier_active(supplier.id, tenant_id)

        assert result == supplier
        assert fake_supplier_service.get_calls == [(supplier.id, tenant_id)]

    async def test_raises_scoped_not_found_when_supplier_missing(self) -> None:
        service, _, _ = _service_with_fakes(
            [], 0, supplier_service=_FakeSupplierService(raise_not_found=True)
        )

        with pytest.raises(SupplierPaymentSupplierNotFoundError):
            await service._ensure_supplier_active(uuid.uuid4(), uuid.uuid4())

    async def test_raises_scoped_inactive_when_supplier_inactive(self) -> None:
        supplier = _make_supplier_response(status=SupplierStatus.INACTIVE)
        service, _, _ = _service_with_fakes(
            [], 0, supplier_service=_FakeSupplierService(supplier=supplier)
        )

        with pytest.raises(SupplierPaymentSupplierInactiveError):
            await service._ensure_supplier_active(supplier.id, uuid.uuid4())


class _NoOpSession:
    """Stands in for AsyncSession - SupplierPaymentService.update only calls
    commit()/refresh() on it, neither of which this test cares about."""

    async def commit(self) -> None:
        return None

    async def refresh(self, _obj: object) -> None:
        return None


class TestUpdateSupplierRevalidation:
    """SupplierPaymentService.update only re-validates the supplier when
    supplier_id is actually present in the payload AND differs from the
    payment's current supplier - mirrors PurchaseService.update's
    supplier_id handling exactly."""

    async def test_unchanged_supplier_id_does_not_call_supplier_service_again(self) -> None:
        supplier_id = uuid.uuid4()
        payment = _make_supplier_payment(
            status=SupplierPaymentStatus.DRAFT, supplier_id=supplier_id
        )
        fake_supplier_service = _FakeSupplierService(
            supplier=_make_supplier_response(id=supplier_id)
        )

        class _GetByIdRepo(_FakeRepo):
            async def get_by_id(
                self, supplier_payment_id: uuid.UUID, tenant_id: uuid.UUID
            ) -> SupplierPayment | None:
                return payment

        service = SupplierPaymentService.__new__(SupplierPaymentService)
        service._repo = _GetByIdRepo([], 0)  # type: ignore[assignment]
        service._supplier_service = fake_supplier_service  # type: ignore[assignment]
        service._session = _NoOpSession()  # type: ignore[assignment]

        payload = SupplierPaymentUpdateRequest(supplier_id=supplier_id, remarks="Same supplier")
        await service.update(
            payment.id, payload, tenant_id=payment.tenant_id, actor_id=uuid.uuid4()
        )

        assert fake_supplier_service.get_calls == []
        assert payment.remarks == "Same supplier"


class TestTranslateIntegrityError:
    def test_unknown_constraint_falls_back_to_generic_conflict(self) -> None:
        exc = _FakeIntegrityError("some_other_constraint")
        result = SupplierPaymentService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert type(result) is ConflictError

    def test_missing_orig_falls_back_to_generic_conflict(self) -> None:
        class _BareError(Exception):
            orig = None

        result = SupplierPaymentService._translate_integrity_error(  # type: ignore[arg-type]
            _BareError()
        )
        assert type(result) is ConflictError

    def test_payment_number_constraint_maps_to_number_conflict_error(self) -> None:
        """Defensive backstop - _allocate_payment_number's FOR UPDATE
        locking should make this unreachable in normal operation, but the
        constraint firing must still surface a clean 409, not a raw 500."""
        exc = _FakeIntegrityError("ix_supplier_payments_tenant_payment_number")
        result = SupplierPaymentService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert isinstance(result, SupplierPaymentNumberConflictError)


class TestToResponse:
    def test_maps_every_field(self) -> None:
        payment = _make_supplier_payment(remarks="Against pending purchase bills")
        response = SupplierPaymentService._to_response(payment)
        assert response.id == payment.id
        assert response.supplier_id == payment.supplier_id
        assert response.amount == payment.amount
        assert response.remarks == "Against pending purchase bills"
        assert response.status == SupplierPaymentStatus.DRAFT


class TestEnsureDraftForAllocation:
    def test_draft_payment_passes(self) -> None:
        payment = _make_supplier_payment(status=SupplierPaymentStatus.DRAFT)
        SupplierPaymentService._ensure_draft_for_allocation(payment)  # must not raise

    @pytest.mark.parametrize(
        "status", [SupplierPaymentStatus.POSTED, SupplierPaymentStatus.CANCELLED]
    )
    def test_non_draft_payment_raises_the_allocation_specific_error(
        self, status: SupplierPaymentStatus
    ) -> None:
        """Distinct from _ensure_draft's SupplierPaymentNotDraftError -
        allocation endpoints report their own error code (see
        SupplierPaymentAllocationPaymentNotDraftError's docstring)."""
        payment = _make_supplier_payment(status=status)
        with pytest.raises(SupplierPaymentAllocationPaymentNotDraftError):
            SupplierPaymentService._ensure_draft_for_allocation(payment)


class TestEnsurePurchaseBillAllocatable:
    async def test_posted_bill_passes(self) -> None:
        bill = _make_purchase_bill_response(status=PurchaseStatus.POSTED)
        service = SupplierPaymentService.__new__(SupplierPaymentService)
        fake_purchase_service = _FakePurchaseService(purchase_bill=bill)
        service._purchase_service = fake_purchase_service  # type: ignore[assignment]
        tenant_id = uuid.uuid4()

        result = await service._ensure_purchase_bill_allocatable(bill.id, tenant_id)

        assert result == bill
        assert fake_purchase_service.get_calls == [(bill.id, tenant_id)]

    async def test_raises_not_found_when_purchase_bill_missing(self) -> None:
        service = SupplierPaymentService.__new__(SupplierPaymentService)
        service._purchase_service = _FakePurchaseService(  # type: ignore[assignment]
            raise_not_found=True
        )

        with pytest.raises(SupplierPaymentAllocationPurchaseBillNotFoundError):
            await service._ensure_purchase_bill_allocatable(uuid.uuid4(), uuid.uuid4())

    async def test_partially_paid_bill_passes(self) -> None:
        bill = _make_purchase_bill_response(status=PurchaseStatus.PARTIALLY_PAID)
        service = SupplierPaymentService.__new__(SupplierPaymentService)
        service._purchase_service = _FakePurchaseService(  # type: ignore[assignment]
            purchase_bill=bill
        )

        result = await service._ensure_purchase_bill_allocatable(bill.id, uuid.uuid4())

        assert result == bill

    @pytest.mark.parametrize(
        "status", [PurchaseStatus.DRAFT, PurchaseStatus.CANCELLED, PurchaseStatus.PAID]
    )
    async def test_raises_not_allocatable_for_ineligible_statuses(
        self, status: PurchaseStatus
    ) -> None:
        bill = _make_purchase_bill_response(status=status)
        service = SupplierPaymentService.__new__(SupplierPaymentService)
        service._purchase_service = _FakePurchaseService(  # type: ignore[assignment]
            purchase_bill=bill
        )

        with pytest.raises(SupplierPaymentPurchaseBillNotAllocatableError):
            await service._ensure_purchase_bill_allocatable(bill.id, uuid.uuid4())

    async def test_paid_bill_passes_when_allow_paid_is_true(self) -> None:
        """The update_allocation path for editing/removing money from the
        same bill an allocation already targets - see
        _ALLOCATION_EDITABLE_PURCHASE_BILL_STATUSES's docstring."""
        bill = _make_purchase_bill_response(status=PurchaseStatus.PAID)
        service = SupplierPaymentService.__new__(SupplierPaymentService)
        service._purchase_service = _FakePurchaseService(  # type: ignore[assignment]
            purchase_bill=bill
        )

        result = await service._ensure_purchase_bill_allocatable(
            bill.id, uuid.uuid4(), allow_paid=True
        )

        assert result == bill

    @pytest.mark.parametrize("status", [PurchaseStatus.DRAFT, PurchaseStatus.CANCELLED])
    async def test_allow_paid_does_not_widen_draft_or_cancelled(
        self, status: PurchaseStatus
    ) -> None:
        bill = _make_purchase_bill_response(status=status)
        service = SupplierPaymentService.__new__(SupplierPaymentService)
        service._purchase_service = _FakePurchaseService(  # type: ignore[assignment]
            purchase_bill=bill
        )

        with pytest.raises(SupplierPaymentPurchaseBillNotAllocatableError):
            await service._ensure_purchase_bill_allocatable(bill.id, uuid.uuid4(), allow_paid=True)


class TestValidateAllocationCeilings:
    def test_passes_within_both_ceilings(self) -> None:
        SupplierPaymentService._validate_allocation_ceilings(
            allocated_amount=Decimal("500.00"),
            purchase_bill_balance=Decimal("1000.00"),
            payment_unallocated=Decimal("800.00"),
        )  # must not raise

    def test_exceeding_purchase_bill_balance_raises_the_shared_amount_exceeded_error(
        self,
    ) -> None:
        with pytest.raises(SupplierPaymentAllocationAmountExceededError) as exc_info:
            SupplierPaymentService._validate_allocation_ceilings(
                allocated_amount=Decimal("1000.01"),
                purchase_bill_balance=Decimal("1000.00"),
                payment_unallocated=Decimal("5000.00"),
            )
        assert "exceeds the purchase bill's balance" in str(exc_info.value)

    def test_exceeding_payment_unallocated_raises_the_shared_amount_exceeded_error(
        self,
    ) -> None:
        with pytest.raises(SupplierPaymentAllocationAmountExceededError) as exc_info:
            SupplierPaymentService._validate_allocation_ceilings(
                allocated_amount=Decimal("500.01"),
                purchase_bill_balance=Decimal("5000.00"),
                payment_unallocated=Decimal("500.00"),
            )
        assert "exceeds the payment's unallocated amount" in str(exc_info.value)


class TestToAllocationResponse:
    def test_maps_every_field(self) -> None:
        allocation = _make_allocation(allocated_amount=Decimal("500.00"))
        response = SupplierPaymentService._to_allocation_response(allocation)
        assert response.id == allocation.id
        assert response.supplier_payment_id == allocation.supplier_payment_id
        assert response.purchase_bill_id == allocation.purchase_bill_id
        assert response.allocated_amount == Decimal("500.00")


class _FakeAllocationSumRepo:
    def __init__(self, total_allocated: Decimal) -> None:
        self.total_allocated = total_allocated
        self.summed_for: tuple[uuid.UUID, uuid.UUID] | None = None

    async def sum_allocated_amount(
        self, supplier_payment_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Decimal:
        self.summed_for = (supplier_payment_id, tenant_id)
        return self.total_allocated


class TestRecalculateSupplierPaymentAllocationTotals:
    async def test_recomputes_both_fields_from_the_summed_allocations(self) -> None:
        service = SupplierPaymentService.__new__(SupplierPaymentService)
        fake_repo = _FakeAllocationSumRepo(Decimal("60000.00"))
        service._repo = fake_repo  # type: ignore[assignment]
        payment = _make_supplier_payment(amount=Decimal("150000.00"))
        tenant_id = uuid.uuid4()

        await service._recalculate_supplier_payment_allocation_totals(payment, tenant_id)

        assert payment.allocated_amount == Decimal("60000.00")
        assert payment.unallocated_amount == Decimal("90000.00")
        assert fake_repo.summed_for == (payment.id, tenant_id)

    async def test_no_active_allocations_leaves_everything_unallocated(self) -> None:
        service = SupplierPaymentService.__new__(SupplierPaymentService)
        fake_repo = _FakeAllocationSumRepo(Decimal("0"))
        service._repo = fake_repo  # type: ignore[assignment]
        payment = _make_supplier_payment(
            amount=Decimal("150000.00"), allocated_amount=Decimal("60000.00")
        )

        await service._recalculate_supplier_payment_allocation_totals(payment, uuid.uuid4())

        assert payment.allocated_amount == Decimal("0")
        assert payment.unallocated_amount == Decimal("150000.00")


class _FakeAllocationSumByBillRepo:
    def __init__(self, total_allocated: Decimal) -> None:
        self.total_allocated = total_allocated
        self.summed_for: tuple[uuid.UUID, uuid.UUID] | None = None

    async def sum_allocated_amount_by_purchase_bill(
        self, purchase_bill_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Decimal:
        self.summed_for = (purchase_bill_id, tenant_id)
        return self.total_allocated


class TestRecalculatePurchaseBillAndSupplier:
    """SupplierPaymentService._recalculate_purchase_bill_and_supplier -
    Sprint 12 Session 4's outstanding engine cascade. Sums this purchase
    bill's currently-active allocations via its own SupplierPaymentRepository
    (never PurchaseRepository) and hands the total to
    PurchaseService.recalculate_payment_totals."""

    async def test_sums_via_its_own_repository_and_forwards_to_purchase_service(self) -> None:
        service = SupplierPaymentService.__new__(SupplierPaymentService)
        fake_repo = _FakeAllocationSumByBillRepo(Decimal("90000.00"))
        fake_purchase_service = _FakePurchaseService()
        service._repo = fake_repo  # type: ignore[assignment]
        service._purchase_service = fake_purchase_service  # type: ignore[assignment]
        purchase_bill_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        await service._recalculate_purchase_bill_and_supplier(purchase_bill_id, tenant_id)

        assert fake_repo.summed_for == (purchase_bill_id, tenant_id)
        assert fake_purchase_service.recalculate_payment_totals_calls == [
            (purchase_bill_id, tenant_id, Decimal("90000.00"))
        ]


class TestTranslateIntegrityErrorAllocation:
    def test_allocation_unique_constraint_maps_to_conflict_error(self) -> None:
        exc = _FakeIntegrityError("ix_supplier_payment_allocations_payment_bill")
        result = SupplierPaymentService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert type(result) is ConflictError
        assert "already has an allocation" in result.message


class _FakePostRepo:
    """Stands in for SupplierPaymentRepository - only the methods post() calls."""

    def __init__(
        self,
        *,
        locked_payment: SupplierPayment | None,
        has_allocations: bool = True,
        total_allocated: Decimal = Decimal("0"),
    ) -> None:
        self.locked_payment = locked_payment
        self._has_allocations = has_allocations
        self.total_allocated = total_allocated
        self.get_for_update_calls: list[tuple[uuid.UUID, uuid.UUID]] = []
        self.has_allocations_calls: list[tuple[uuid.UUID, uuid.UUID]] = []
        self.sequences: dict[tuple[uuid.UUID, str, str], SupplierPaymentSequence] = {}
        self.ensure_sequence_calls: list[tuple[uuid.UUID, str, str]] = []

    async def get_by_id_for_update(
        self, supplier_payment_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> SupplierPayment | None:
        self.get_for_update_calls.append((supplier_payment_id, tenant_id))
        return self.locked_payment

    async def has_allocations(self, supplier_payment_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        self.has_allocations_calls.append((supplier_payment_id, tenant_id))
        return self._has_allocations

    async def sum_allocated_amount(
        self, supplier_payment_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Decimal:
        return self.total_allocated

    async def ensure_sequence_row(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> None:
        self.ensure_sequence_calls.append((tenant_id, prefix, fiscal_year))
        key = (tenant_id, prefix, fiscal_year)
        if key not in self.sequences:
            self.sequences[key] = SupplierPaymentSequence(
                tenant_id=tenant_id, prefix=prefix, fiscal_year=fiscal_year, last_number=0
            )

    async def get_sequence_for_update(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> SupplierPaymentSequence:
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
    payment: SupplierPayment | None,
    has_allocations: bool = True,
    total_allocated: Decimal = Decimal("0"),
) -> tuple[SupplierPaymentService, _FakePostRepo, _FakePostSession]:
    service = SupplierPaymentService.__new__(SupplierPaymentService)
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
    (tests/integration/test_supplier_payment_post.py)."""

    async def test_raises_not_found_when_payment_missing(self) -> None:
        service, fake_repo, fake_session = _post_service_with_fakes(payment=None)
        supplier_payment_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        with pytest.raises(SupplierPaymentNotFoundError):
            await service.post(supplier_payment_id, tenant_id=tenant_id, actor_id=uuid.uuid4())

        assert fake_repo.get_for_update_calls == [(supplier_payment_id, tenant_id)]
        assert fake_session.rollback_calls == 1

    @pytest.mark.parametrize(
        "status", [SupplierPaymentStatus.POSTED, SupplierPaymentStatus.CANCELLED]
    )
    async def test_raises_not_draft_for_non_draft_statuses(
        self, status: SupplierPaymentStatus
    ) -> None:
        """Covers "cannot post twice" (POSTED) and "cannot post a cancelled
        payment" (CANCELLED) with the same guard."""
        payment = _make_supplier_payment(status=status)
        service, _, fake_session = _post_service_with_fakes(payment=payment)

        with pytest.raises(SupplierPaymentNotDraftError):
            await service.post(payment.id, tenant_id=payment.tenant_id, actor_id=uuid.uuid4())

        assert fake_session.rollback_calls == 1

    async def test_raises_no_allocations_when_the_payment_has_none(self) -> None:
        payment = _make_supplier_payment(status=SupplierPaymentStatus.DRAFT)
        service, fake_repo, fake_session = _post_service_with_fakes(
            payment=payment, has_allocations=False
        )

        with pytest.raises(SupplierPaymentNoAllocationsError):
            await service.post(payment.id, tenant_id=payment.tenant_id, actor_id=uuid.uuid4())

        assert fake_repo.has_allocations_calls == [(payment.id, payment.tenant_id)]
        assert fake_session.rollback_calls == 1

    async def test_raises_totals_invalid_when_the_invariant_is_violated(self) -> None:
        """Not reachable through the real recompute step -
        calculate_supplier_payment_allocation_totals always keeps
        allocated_amount + unallocated_amount == amount true by
        construction, whatever total_allocated is - so this proves the
        defensive check itself fires correctly, by monkey-patching the
        recompute step to simulate a corrupted row (e.g. from a future
        refactor bug)."""
        payment = _make_supplier_payment(
            status=SupplierPaymentStatus.DRAFT, amount=Decimal("1000.00")
        )
        service, _, fake_session = _post_service_with_fakes(payment=payment)

        async def _corrupt_recalculate(target: SupplierPayment, tenant_id: uuid.UUID) -> None:
            target.allocated_amount = Decimal("999.00")
            target.unallocated_amount = Decimal("999.00")

        service._recalculate_supplier_payment_allocation_totals = _corrupt_recalculate  # type: ignore[assignment]

        with pytest.raises(SupplierPaymentTotalsInvalidError):
            await service.post(payment.id, tenant_id=payment.tenant_id, actor_id=uuid.uuid4())

        assert fake_session.rollback_calls == 1

    async def test_locked_lookup_is_scoped_to_the_given_tenant(self) -> None:
        payment = _make_supplier_payment(status=SupplierPaymentStatus.POSTED)
        service, fake_repo, _ = _post_service_with_fakes(payment=payment)
        tenant_id = uuid.uuid4()

        with pytest.raises(SupplierPaymentNotDraftError):
            await service.post(payment.id, tenant_id=tenant_id, actor_id=uuid.uuid4())

        assert fake_repo.get_for_update_calls == [(payment.id, tenant_id)]


class TestAllocatePaymentNumber:
    """SupplierPaymentService._allocate_payment_number - the counter-
    orchestration logic (fiscal year computation, ensure-then-lock,
    increment). The actual concurrency guarantee (SELECT ... FOR UPDATE
    serializing two real transactions) can only be verified against a real
    database - see tests/integration/test_supplier_payment_post.py."""

    async def test_first_allocation_for_a_fiscal_year_starts_at_one(self) -> None:
        service = SupplierPaymentService.__new__(SupplierPaymentService)
        fake_repo = _FakePostRepo(locked_payment=None)
        service._repo = fake_repo  # type: ignore[assignment]
        payment = _make_supplier_payment(payment_date=date(2026, 7, 23))

        number = await service._allocate_payment_number(payment, uuid.uuid4())

        assert number == "SPAY/2026-27/00001"

    async def test_second_allocation_for_the_same_fiscal_year_increments(self) -> None:
        service = SupplierPaymentService.__new__(SupplierPaymentService)
        fake_repo = _FakePostRepo(locked_payment=None)
        service._repo = fake_repo  # type: ignore[assignment]
        payment = _make_supplier_payment(payment_date=date(2026, 7, 23))
        tenant_id = uuid.uuid4()

        await service._allocate_payment_number(payment, tenant_id)
        second = await service._allocate_payment_number(payment, tenant_id)

        assert second == "SPAY/2026-27/00002"

    async def test_different_fiscal_years_get_independent_counters(self) -> None:
        service = SupplierPaymentService.__new__(SupplierPaymentService)
        fake_repo = _FakePostRepo(locked_payment=None)
        service._repo = fake_repo  # type: ignore[assignment]
        tenant_id = uuid.uuid4()
        early_fy = _make_supplier_payment(payment_date=date(2026, 3, 15))  # FY 2025-26
        late_fy = _make_supplier_payment(payment_date=date(2026, 7, 23))  # FY 2026-27

        early_number = await service._allocate_payment_number(early_fy, tenant_id)
        late_number = await service._allocate_payment_number(late_fy, tenant_id)

        assert early_number == "SPAY/2025-26/00001"
        assert late_number == "SPAY/2026-27/00001"

    async def test_different_tenants_get_independent_counters(self) -> None:
        service = SupplierPaymentService.__new__(SupplierPaymentService)
        fake_repo = _FakePostRepo(locked_payment=None)
        service._repo = fake_repo  # type: ignore[assignment]
        payment = _make_supplier_payment(payment_date=date(2026, 7, 23))

        first_tenant_number = await service._allocate_payment_number(payment, uuid.uuid4())
        second_tenant_number = await service._allocate_payment_number(payment, uuid.uuid4())

        assert first_tenant_number == "SPAY/2026-27/00001"
        assert second_tenant_number == "SPAY/2026-27/00001"

    async def test_ensures_sequence_row_before_locking_it(self) -> None:
        service = SupplierPaymentService.__new__(SupplierPaymentService)
        fake_repo = _FakePostRepo(locked_payment=None)
        service._repo = fake_repo  # type: ignore[assignment]
        payment = _make_supplier_payment(payment_date=date(2026, 7, 23))
        tenant_id = uuid.uuid4()

        await service._allocate_payment_number(payment, tenant_id)

        assert fake_repo.ensure_sequence_calls == [(tenant_id, "SPAY", "2026-27")]
