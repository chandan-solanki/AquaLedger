import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.core.errors import ConflictError
from app.modules.purchase.constants import PurchaseStatus
from app.modules.purchase.exceptions import (
    PurchaseBillEmptyError,
    PurchaseBillItemNotFoundError,
    PurchaseBillNotDraftError,
    PurchaseBillNotFoundError,
    PurchaseBillSupplierInactiveError,
    PurchaseBillSupplierNotFoundError,
    PurchaseNumberConflictError,
)
from app.modules.purchase.models import PurchaseBill, PurchaseBillItem, PurchaseSequence
from app.modules.purchase.schemas import PurchaseBillListParams, PurchaseBillUpdateRequest
from app.modules.purchase.service import PurchaseService
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
    def __init__(self, rows: list[PurchaseBill], total: int) -> None:
        self.rows = rows
        self.total = total
        self.last_call: dict[str, Any] | None = None

    async def search(self, tenant_id: uuid.UUID, **kwargs: Any) -> tuple[list[PurchaseBill], int]:
        self.last_call = {"tenant_id": tenant_id, **kwargs}
        return self.rows, self.total


class _FakeSupplierService:
    """Stands in for SupplierService - PurchaseService must call this, never
    SupplierRepository directly (ARCHITECTURE.md §2, TASKS.md Sprint 11
    Session 2)."""

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


def _make_purchase_bill(**overrides: Any) -> PurchaseBill:
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "supplier_id": uuid.uuid4(),
        "bill_number": None,
        "bill_date": date(2026, 7, 23),
        "status": PurchaseStatus.DRAFT,
        "subtotal": Decimal("0"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("0"),
        "tax_amount": Decimal("0"),
        "transport_charge": Decimal("0"),
        "other_charge": Decimal("0"),
        "round_off": Decimal("0"),
        "total_amount": Decimal("0"),
        "paid_amount": Decimal("0"),
        "balance_amount": Decimal("0"),
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return PurchaseBill(**defaults)


def _make_purchase_bill_item(**overrides: Any) -> PurchaseBillItem:
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "purchase_bill_id": uuid.uuid4(),
        "line_number": 1,
        "description": "Item",
        "quantity": Decimal("1"),
        "unit": "KG",
        "rate": Decimal("1"),
        "discount_percent": Decimal("0"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("0"),
        "tax_rate": Decimal("0"),
        "tax_amount": Decimal("0"),
        "line_total": Decimal("0"),
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return PurchaseBillItem(**defaults)


def _service_with_fakes(
    rows: list[PurchaseBill],
    total: int,
    *,
    supplier_service: _FakeSupplierService | None = None,
) -> tuple[PurchaseService, _FakeRepo, _FakeSupplierService]:
    service = PurchaseService.__new__(PurchaseService)
    fake_repo = _FakeRepo(rows, total)
    fake_supplier_service = supplier_service or _FakeSupplierService(
        supplier=_make_supplier_response()
    )
    service._repo = fake_repo  # type: ignore[assignment]
    service._supplier_service = fake_supplier_service  # type: ignore[assignment]
    return service, fake_repo, fake_supplier_service


class TestTranslateIntegrityError:
    def test_bill_number_constraint_maps_to_duplicate_error(self) -> None:
        exc = _FakeIntegrityError("ix_purchase_bills_tenant_bill_number")
        result = PurchaseService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert isinstance(result, PurchaseNumberConflictError)

    def test_unknown_constraint_falls_back_to_generic_conflict(self) -> None:
        exc = _FakeIntegrityError("some_other_constraint")
        result = PurchaseService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert type(result) is ConflictError

    def test_missing_orig_falls_back_to_generic_conflict(self) -> None:
        class _BareError(Exception):
            orig = None

        result = PurchaseService._translate_integrity_error(_BareError())  # type: ignore[arg-type]
        assert type(result) is ConflictError


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

    async def test_raises_purchase_scoped_not_found_when_supplier_missing(self) -> None:
        service, _, _ = _service_with_fakes(
            [], 0, supplier_service=_FakeSupplierService(raise_not_found=True)
        )

        with pytest.raises(PurchaseBillSupplierNotFoundError):
            await service._ensure_supplier_active(uuid.uuid4(), uuid.uuid4())

    async def test_raises_purchase_scoped_inactive_when_supplier_inactive(self) -> None:
        supplier = _make_supplier_response(status=SupplierStatus.INACTIVE)
        service, _, _ = _service_with_fakes(
            [], 0, supplier_service=_FakeSupplierService(supplier=supplier)
        )

        with pytest.raises(PurchaseBillSupplierInactiveError):
            await service._ensure_supplier_active(supplier.id, uuid.uuid4())


class TestEnsureDraft:
    def test_draft_bill_passes(self) -> None:
        bill = _make_purchase_bill(status=PurchaseStatus.DRAFT)
        PurchaseService._ensure_draft(bill)  # does not raise

    @pytest.mark.parametrize("status", [PurchaseStatus.POSTED, PurchaseStatus.CANCELLED])
    def test_non_draft_bill_raises(self, status: PurchaseStatus) -> None:
        bill = _make_purchase_bill(status=status)
        with pytest.raises(PurchaseBillNotDraftError):
            PurchaseService._ensure_draft(bill)


class TestListPurchaseBillsPaginationMath:
    async def test_first_page_of_several(self) -> None:
        rows = [_make_purchase_bill() for _ in range(2)]
        service, fake_repo, _ = _service_with_fakes(rows, total=5)

        result = await service.list_purchase_bills(
            tenant_id=uuid.uuid4(), params=PurchaseBillListParams(page=1, page_size=2)
        )

        assert len(result.data) == 2
        assert result.meta.total_records == 5
        assert result.meta.total_pages == 3
        assert result.meta.has_next is True
        assert result.meta.has_previous is False
        assert fake_repo.last_call is not None

    async def test_empty_result_gives_zero_pages(self) -> None:
        service, _, _ = _service_with_fakes([], total=0)

        result = await service.list_purchase_bills(
            tenant_id=uuid.uuid4(), params=PurchaseBillListParams(page=1, page_size=20)
        )

        assert result.data == []
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

        await service.list_purchase_bills(
            tenant_id=tenant_id, params=PurchaseBillListParams(q="Coastal")
        )

        assert fake_supplier_service.find_ids_by_name_calls == [(tenant_id, "Coastal")]
        assert fake_repo.last_call is not None
        assert fake_repo.last_call["q_supplier_ids"] == [match_id]

    async def test_blank_q_does_not_call_supplier_service(self) -> None:
        fake_supplier_service = _FakeSupplierService(supplier=_make_supplier_response())
        service, fake_repo, _ = _service_with_fakes(
            [], total=0, supplier_service=fake_supplier_service
        )

        await service.list_purchase_bills(
            tenant_id=uuid.uuid4(), params=PurchaseBillListParams(q=None)
        )

        assert fake_supplier_service.find_ids_by_name_calls == []
        assert fake_repo.last_call is not None
        assert fake_repo.last_call["q_supplier_ids"] is None

    async def test_filters_are_forwarded_to_the_repository(self) -> None:
        service, fake_repo, _ = _service_with_fakes([], total=0)
        tenant_id = uuid.uuid4()
        supplier_id = uuid.uuid4()

        await service.list_purchase_bills(
            tenant_id=tenant_id,
            params=PurchaseBillListParams(
                status=PurchaseStatus.DRAFT,
                supplier_id=supplier_id,
                bill_date_from=date(2026, 1, 1),
                bill_date_to=date(2026, 12, 31),
                sort="-bill_date",
                page=2,
                page_size=10,
            ),
        )

        assert fake_repo.last_call == {
            "tenant_id": tenant_id,
            "q": None,
            "q_supplier_ids": None,
            "status": PurchaseStatus.DRAFT,
            "supplier_id": supplier_id,
            "bill_date_from": date(2026, 1, 1),
            "bill_date_to": date(2026, 12, 31),
            "sort": "-bill_date",
            "page": 2,
            "page_size": 10,
        }


class TestUpdateSupplierRevalidation:
    """PurchaseService.update only re-validates the supplier when
    supplier_id is actually present in the payload AND differs from the
    bill's current supplier - mirrors PaymentService.update's
    company_id handling exactly."""

    async def test_unchanged_supplier_id_does_not_call_supplier_service_again(self) -> None:
        supplier_id = uuid.uuid4()
        bill = _make_purchase_bill(status=PurchaseStatus.DRAFT, supplier_id=supplier_id)
        fake_supplier_service = _FakeSupplierService(
            supplier=_make_supplier_response(id=supplier_id)
        )

        class _GetByIdRepo(_FakeRepo):
            async def get_by_id(
                self, purchase_bill_id: uuid.UUID, tenant_id: uuid.UUID
            ) -> PurchaseBill | None:
                return bill

        service = PurchaseService.__new__(PurchaseService)
        service._repo = _GetByIdRepo([], 0)  # type: ignore[assignment]
        service._supplier_service = fake_supplier_service  # type: ignore[assignment]
        service._session = _NoOpSession()  # type: ignore[assignment]

        payload = PurchaseBillUpdateRequest(supplier_id=supplier_id, remarks="Same supplier")
        await service.update(bill.id, payload, tenant_id=bill.tenant_id, actor_id=uuid.uuid4())

        assert fake_supplier_service.get_calls == []
        assert bill.remarks == "Same supplier"


class _NoOpSession:
    """Stands in for AsyncSession - PurchaseService.update only calls
    commit()/refresh() on it, neither of which this test cares about."""

    async def commit(self) -> None:
        return None

    async def refresh(self, _obj: object) -> None:
        return None


class _FakeItemRepo:
    def __init__(self, item: PurchaseBillItem | None) -> None:
        self._item = item
        self.get_item_calls: list[tuple[uuid.UUID, uuid.UUID, uuid.UUID]] = []

    async def get_item_by_id(
        self, item_id: uuid.UUID, purchase_bill_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PurchaseBillItem | None:
        self.get_item_calls.append((item_id, purchase_bill_id, tenant_id))
        return self._item


class TestGetItemOrRaise:
    """PurchaseService._get_item_or_raise - the same "item id exists but on
    a different bill/tenant is not found" scoping InvoiceService's
    equivalent helper relies on, delegated entirely to
    PurchaseRepository.get_item_by_id (already scoped by both ids)."""

    async def test_returns_the_item_when_found(self) -> None:
        item = PurchaseBillItem(
            tenant_id=uuid.uuid4(),
            purchase_bill_id=uuid.uuid4(),
            line_number=1,
            quantity=Decimal("1.000"),
            unit="KG",
            rate=Decimal("1.0000"),
        )
        service = PurchaseService.__new__(PurchaseService)
        fake_repo = _FakeItemRepo(item)
        service._repo = fake_repo  # type: ignore[assignment]

        result = await service._get_item_or_raise(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())

        assert result is item

    async def test_raises_when_repository_returns_none(self) -> None:
        service = PurchaseService.__new__(PurchaseService)
        service._repo = _FakeItemRepo(None)  # type: ignore[assignment]

        with pytest.raises(PurchaseBillItemNotFoundError):
            await service._get_item_or_raise(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())


class _FakePostRepo:
    """Stands in for PurchaseRepository across post()'s full call surface -
    the locked lookup, item search, and sequence counter orchestration."""

    def __init__(self) -> None:
        self.locked_bill: PurchaseBill | None = None
        self.get_for_update_calls: list[tuple[uuid.UUID, uuid.UUID]] = []
        self.items_by_bill: dict[uuid.UUID, list[PurchaseBillItem]] = {}
        self.sequences: dict[tuple[uuid.UUID, str, str], PurchaseSequence] = {}
        self.ensure_sequence_calls: list[tuple[uuid.UUID, str, str]] = []

    async def get_by_id_for_update(
        self, purchase_bill_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PurchaseBill | None:
        self.get_for_update_calls.append((purchase_bill_id, tenant_id))
        return self.locked_bill

    async def search_items(
        self, purchase_bill_id: uuid.UUID, tenant_id: uuid.UUID, **kwargs: Any
    ) -> list[PurchaseBillItem]:
        return self.items_by_bill.get(purchase_bill_id, [])

    async def ensure_sequence_row(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> None:
        self.ensure_sequence_calls.append((tenant_id, prefix, fiscal_year))
        key = (tenant_id, prefix, fiscal_year)
        if key not in self.sequences:
            self.sequences[key] = PurchaseSequence(
                tenant_id=tenant_id, prefix=prefix, fiscal_year=fiscal_year, last_number=0
            )

    async def get_sequence_for_update(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> PurchaseSequence:
        return self.sequences[(tenant_id, prefix, fiscal_year)]


class _FakeSupplierServiceForPost:
    def __init__(self) -> None:
        self.increase_calls: list[tuple[uuid.UUID, Decimal, uuid.UUID]] = []

    async def increase_outstanding(
        self, supplier_id: uuid.UUID, amount: Decimal, *, tenant_id: uuid.UUID
    ) -> None:
        self.increase_calls.append((supplier_id, amount, tenant_id))


class _FakePostSession:
    """Stands in for AsyncSession - post() only ever calls .rollback()/
    .commit()/.refresh() on it (no .flush() - post() doesn't mutate items
    itself, so there's nothing _recalculate_purchase_bill's query would
    otherwise miss)."""

    def __init__(self) -> None:
        self.rollback_calls = 0
        self.commit_calls = 0
        self.refresh_calls: list[object] = []

    async def rollback(self) -> None:
        self.rollback_calls += 1

    async def commit(self) -> None:
        self.commit_calls += 1

    async def refresh(self, obj: object) -> None:
        self.refresh_calls.append(obj)


def _post_service_with_fakes(
    bill: PurchaseBill | None, items: list[PurchaseBillItem]
) -> tuple[PurchaseService, _FakePostRepo, _FakeSupplierServiceForPost, _FakePostSession]:
    service = PurchaseService.__new__(PurchaseService)
    fake_repo = _FakePostRepo()
    fake_repo.locked_bill = bill
    if bill is not None:
        fake_repo.items_by_bill[bill.id] = items
    fake_supplier_service = _FakeSupplierServiceForPost()
    fake_session = _FakePostSession()
    service._repo = fake_repo  # type: ignore[assignment]
    service._supplier_service = fake_supplier_service  # type: ignore[assignment]
    service._session = fake_session  # type: ignore[assignment]
    return service, fake_repo, fake_supplier_service, fake_session


class TestPostSuccess:
    async def test_assigns_number_status_posted_at_and_credits_supplier(self) -> None:
        bill = _make_purchase_bill(
            status=PurchaseStatus.DRAFT, bill_date=date(2026, 7, 22), bill_number=None
        )
        item = _make_purchase_bill_item(
            purchase_bill_id=bill.id,
            tenant_id=bill.tenant_id,
            quantity=Decimal("10"),
            rate=Decimal("100"),
        )
        service, fake_repo, fake_supplier_service, fake_session = _post_service_with_fakes(
            bill, [item]
        )

        result = await service.post(bill.id, tenant_id=bill.tenant_id, actor_id=uuid.uuid4())

        assert result.status == PurchaseStatus.POSTED
        assert result.bill_number == "PUR/2026-27/00001"
        assert bill.posted_at is not None
        assert result.total_amount == Decimal("1000.00")
        assert result.balance_amount == Decimal("1000.00")
        assert fake_supplier_service.increase_calls == [
            (bill.supplier_id, Decimal("1000.00"), bill.tenant_id)
        ]
        assert fake_session.commit_calls == 1
        assert fake_session.rollback_calls == 0

    async def test_locks_the_bill_row_via_for_update_lookup(self) -> None:
        bill = _make_purchase_bill(status=PurchaseStatus.DRAFT, bill_date=date(2026, 7, 22))
        item = _make_purchase_bill_item(purchase_bill_id=bill.id, tenant_id=bill.tenant_id)
        service, fake_repo, _, _ = _post_service_with_fakes(bill, [item])

        await service.post(bill.id, tenant_id=bill.tenant_id, actor_id=uuid.uuid4())

        assert fake_repo.get_for_update_calls == [(bill.id, bill.tenant_id)]


class TestPostRollback:
    async def test_unknown_bill_rolls_back_and_raises_not_found(self) -> None:
        service, _, _, fake_session = _post_service_with_fakes(None, [])

        with pytest.raises(PurchaseBillNotFoundError):
            await service.post(uuid.uuid4(), tenant_id=uuid.uuid4(), actor_id=uuid.uuid4())

        assert fake_session.rollback_calls == 1
        assert fake_session.commit_calls == 0

    async def test_already_posted_bill_rolls_back_and_raises_not_draft(self) -> None:
        bill = _make_purchase_bill(status=PurchaseStatus.POSTED)
        service, _, _, fake_session = _post_service_with_fakes(bill, [])

        with pytest.raises(PurchaseBillNotDraftError):
            await service.post(bill.id, tenant_id=bill.tenant_id, actor_id=uuid.uuid4())

        assert fake_session.rollback_calls == 1
        assert fake_session.commit_calls == 0

    async def test_cancelled_bill_rolls_back_and_raises_not_draft(self) -> None:
        bill = _make_purchase_bill(status=PurchaseStatus.CANCELLED)
        service, _, _, fake_session = _post_service_with_fakes(bill, [])

        with pytest.raises(PurchaseBillNotDraftError):
            await service.post(bill.id, tenant_id=bill.tenant_id, actor_id=uuid.uuid4())

        assert fake_session.rollback_calls == 1

    async def test_empty_bill_rolls_back_and_raises_empty(self) -> None:
        bill = _make_purchase_bill(status=PurchaseStatus.DRAFT)
        service, _, fake_supplier_service, fake_session = _post_service_with_fakes(bill, [])

        with pytest.raises(PurchaseBillEmptyError):
            await service.post(bill.id, tenant_id=bill.tenant_id, actor_id=uuid.uuid4())

        assert fake_session.rollback_calls == 1
        assert fake_session.commit_calls == 0
        # Supplier outstanding must never be touched on a failed attempt.
        assert fake_supplier_service.increase_calls == []

    async def test_bill_is_not_mutated_after_a_failed_empty_post(self) -> None:
        bill = _make_purchase_bill(status=PurchaseStatus.DRAFT, bill_number=None)
        service, _, _, _ = _post_service_with_fakes(bill, [])

        with pytest.raises(PurchaseBillEmptyError):
            await service.post(bill.id, tenant_id=bill.tenant_id, actor_id=uuid.uuid4())

        assert bill.status == PurchaseStatus.DRAFT
        assert bill.bill_number is None
        assert bill.posted_at is None


class TestAllocatePurchaseNumber:
    """PurchaseService._allocate_purchase_number - the counter-orchestration
    logic (fiscal year computation, ensure-then-lock, increment). The actual
    concurrency guarantee (SELECT ... FOR UPDATE serializing two real
    transactions) can only be verified against a real database - see
    tests/integration/test_purchase_repository.py."""

    async def test_first_allocation_for_a_fiscal_year_starts_at_one(self) -> None:
        service = PurchaseService.__new__(PurchaseService)
        fake_repo = _FakePostRepo()
        service._repo = fake_repo  # type: ignore[assignment]
        bill = _make_purchase_bill(bill_date=date(2026, 7, 22))

        number = await service._allocate_purchase_number(bill, uuid.uuid4())

        assert number == "PUR/2026-27/00001"

    async def test_second_allocation_for_the_same_fiscal_year_increments(self) -> None:
        service = PurchaseService.__new__(PurchaseService)
        fake_repo = _FakePostRepo()
        service._repo = fake_repo  # type: ignore[assignment]
        bill = _make_purchase_bill(bill_date=date(2026, 7, 22))
        tenant_id = uuid.uuid4()

        await service._allocate_purchase_number(bill, tenant_id)
        second = await service._allocate_purchase_number(bill, tenant_id)

        assert second == "PUR/2026-27/00002"

    async def test_different_fiscal_years_get_independent_counters(self) -> None:
        service = PurchaseService.__new__(PurchaseService)
        fake_repo = _FakePostRepo()
        service._repo = fake_repo  # type: ignore[assignment]
        tenant_id = uuid.uuid4()
        early_fy = _make_purchase_bill(bill_date=date(2026, 3, 15))  # FY 2025-26
        late_fy = _make_purchase_bill(bill_date=date(2026, 7, 22))  # FY 2026-27

        early_number = await service._allocate_purchase_number(early_fy, tenant_id)
        late_number = await service._allocate_purchase_number(late_fy, tenant_id)

        assert early_number == "PUR/2025-26/00001"
        assert late_number == "PUR/2026-27/00001"

    async def test_different_tenants_get_independent_counters(self) -> None:
        service = PurchaseService.__new__(PurchaseService)
        fake_repo = _FakePostRepo()
        service._repo = fake_repo  # type: ignore[assignment]
        bill = _make_purchase_bill(bill_date=date(2026, 7, 22))

        first_tenant_number = await service._allocate_purchase_number(bill, uuid.uuid4())
        second_tenant_number = await service._allocate_purchase_number(bill, uuid.uuid4())

        assert first_tenant_number == "PUR/2026-27/00001"
        assert second_tenant_number == "PUR/2026-27/00001"

    async def test_ensures_sequence_row_before_locking_it(self) -> None:
        service = PurchaseService.__new__(PurchaseService)
        fake_repo = _FakePostRepo()
        service._repo = fake_repo  # type: ignore[assignment]
        bill = _make_purchase_bill(bill_date=date(2026, 7, 22))
        tenant_id = uuid.uuid4()

        await service._allocate_purchase_number(bill, tenant_id)

        assert fake_repo.ensure_sequence_calls == [(tenant_id, "PUR", "2026-27")]
