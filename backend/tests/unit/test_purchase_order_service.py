import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.core.errors import ConflictError
from app.modules.purchase_orders.constants import PurchaseOrderStatus
from app.modules.purchase_orders.exceptions import (
    PurchaseOrderEmptyError,
    PurchaseOrderInvalidTransitionError,
    PurchaseOrderItemNotFoundError,
    PurchaseOrderNotDraftError,
    PurchaseOrderNotFoundError,
    PurchaseOrderNumberConflictError,
    PurchaseOrderSupplierInactiveError,
    PurchaseOrderSupplierNotFoundError,
)
from app.modules.purchase_orders.models import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderSequence,
)
from app.modules.purchase_orders.schemas import PurchaseOrderListParams, PurchaseOrderUpdateRequest
from app.modules.purchase_orders.service import PurchaseOrderService
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
    def __init__(self, rows: list[PurchaseOrder], total: int) -> None:
        self.rows = rows
        self.total = total
        self.last_call: dict[str, Any] | None = None

    async def search(self, tenant_id: uuid.UUID, **kwargs: Any) -> tuple[list[PurchaseOrder], int]:
        self.last_call = {"tenant_id": tenant_id, **kwargs}
        return self.rows, self.total


class _FakeSupplierService:
    """Stands in for SupplierService - PurchaseOrderService must call this,
    never SupplierRepository directly (ARCHITECTURE.md §2)."""

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


def _make_purchase_order(**overrides: Any) -> PurchaseOrder:
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "supplier_id": uuid.uuid4(),
        "po_number": None,
        "order_date": date(2026, 8, 15),
        "status": PurchaseOrderStatus.DRAFT,
        "subtotal": Decimal("0"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("0"),
        "tax_amount": Decimal("0"),
        "transport_charge": Decimal("0"),
        "other_charge": Decimal("0"),
        "round_off": Decimal("0"),
        "total_amount": Decimal("0"),
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return PurchaseOrder(**defaults)


def _make_purchase_order_item(**overrides: Any) -> PurchaseOrderItem:
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "purchase_order_id": uuid.uuid4(),
        "line_number": 1,
        "description": "Item",
        "quantity": Decimal("1"),
        "unit": "KG",
        "rate": Decimal("1"),
        "discount_percent": Decimal("0"),
        "discount_amount": Decimal("0"),
        "tax_rate": Decimal("0"),
        "tax_amount": Decimal("0"),
        "line_total": Decimal("0"),
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return PurchaseOrderItem(**defaults)


def _service_with_fakes(
    rows: list[PurchaseOrder],
    total: int,
    *,
    supplier_service: _FakeSupplierService | None = None,
) -> tuple[PurchaseOrderService, _FakeRepo, _FakeSupplierService]:
    service = PurchaseOrderService.__new__(PurchaseOrderService)
    fake_repo = _FakeRepo(rows, total)
    fake_supplier_service = supplier_service or _FakeSupplierService(
        supplier=_make_supplier_response()
    )
    service._repo = fake_repo  # type: ignore[assignment]
    service._supplier_service = fake_supplier_service  # type: ignore[assignment]
    return service, fake_repo, fake_supplier_service


class TestTranslateIntegrityError:
    def test_po_number_constraint_maps_to_duplicate_error(self) -> None:
        exc = _FakeIntegrityError("ix_purchase_orders_tenant_po_number")
        result = PurchaseOrderService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert isinstance(result, PurchaseOrderNumberConflictError)

    def test_unknown_constraint_falls_back_to_generic_conflict(self) -> None:
        exc = _FakeIntegrityError("some_other_constraint")
        result = PurchaseOrderService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert type(result) is ConflictError

    def test_missing_orig_falls_back_to_generic_conflict(self) -> None:
        class _BareError(Exception):
            orig = None

        result = PurchaseOrderService._translate_integrity_error(_BareError())  # type: ignore[arg-type]
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

    async def test_raises_purchase_order_scoped_not_found_when_supplier_missing(self) -> None:
        service, _, _ = _service_with_fakes(
            [], 0, supplier_service=_FakeSupplierService(raise_not_found=True)
        )

        with pytest.raises(PurchaseOrderSupplierNotFoundError):
            await service._ensure_supplier_active(uuid.uuid4(), uuid.uuid4())

    async def test_raises_purchase_order_scoped_inactive_when_supplier_inactive(self) -> None:
        supplier = _make_supplier_response(status=SupplierStatus.INACTIVE)
        service, _, _ = _service_with_fakes(
            [], 0, supplier_service=_FakeSupplierService(supplier=supplier)
        )

        with pytest.raises(PurchaseOrderSupplierInactiveError):
            await service._ensure_supplier_active(supplier.id, uuid.uuid4())


class TestEnsureDraft:
    def test_draft_order_passes(self) -> None:
        order = _make_purchase_order(status=PurchaseOrderStatus.DRAFT)
        PurchaseOrderService._ensure_draft(order)  # does not raise

    @pytest.mark.parametrize(
        "status",
        [
            PurchaseOrderStatus.CONFIRMED,
            PurchaseOrderStatus.FULFILLED,
            PurchaseOrderStatus.CANCELLED,
        ],
    )
    def test_non_draft_order_raises(self, status: PurchaseOrderStatus) -> None:
        order = _make_purchase_order(status=status)
        with pytest.raises(PurchaseOrderNotDraftError):
            PurchaseOrderService._ensure_draft(order)


class TestListPurchaseOrdersPaginationMath:
    async def test_first_page_of_several(self) -> None:
        rows = [_make_purchase_order() for _ in range(2)]
        service, fake_repo, _ = _service_with_fakes(rows, total=5)

        result = await service.list_purchase_orders(
            tenant_id=uuid.uuid4(), params=PurchaseOrderListParams(page=1, page_size=2)
        )

        assert len(result.data) == 2
        assert result.meta.total_records == 5
        assert result.meta.total_pages == 3
        assert result.meta.has_next is True
        assert result.meta.has_previous is False
        assert fake_repo.last_call is not None

    async def test_empty_result_gives_zero_pages(self) -> None:
        service, _, _ = _service_with_fakes([], total=0)

        result = await service.list_purchase_orders(
            tenant_id=uuid.uuid4(), params=PurchaseOrderListParams(page=1, page_size=20)
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

        await service.list_purchase_orders(
            tenant_id=tenant_id, params=PurchaseOrderListParams(q="Coastal")
        )

        assert fake_supplier_service.find_ids_by_name_calls == [(tenant_id, "Coastal")]
        assert fake_repo.last_call is not None
        assert fake_repo.last_call["q_supplier_ids"] == [match_id]

    async def test_blank_q_does_not_call_supplier_service(self) -> None:
        fake_supplier_service = _FakeSupplierService(supplier=_make_supplier_response())
        service, fake_repo, _ = _service_with_fakes(
            [], total=0, supplier_service=fake_supplier_service
        )

        await service.list_purchase_orders(
            tenant_id=uuid.uuid4(), params=PurchaseOrderListParams(q=None)
        )

        assert fake_supplier_service.find_ids_by_name_calls == []
        assert fake_repo.last_call is not None
        assert fake_repo.last_call["q_supplier_ids"] is None

    async def test_filters_are_forwarded_to_the_repository(self) -> None:
        service, fake_repo, _ = _service_with_fakes([], total=0)
        tenant_id = uuid.uuid4()
        supplier_id = uuid.uuid4()

        await service.list_purchase_orders(
            tenant_id=tenant_id,
            params=PurchaseOrderListParams(
                status=PurchaseOrderStatus.DRAFT,
                supplier_id=supplier_id,
                order_date_from=date(2026, 1, 1),
                order_date_to=date(2026, 12, 31),
                sort="-order_date",
                page=2,
                page_size=10,
            ),
        )

        assert fake_repo.last_call == {
            "tenant_id": tenant_id,
            "q": None,
            "q_supplier_ids": None,
            "status": PurchaseOrderStatus.DRAFT,
            "supplier_id": supplier_id,
            "billable": None,
            "order_date_from": date(2026, 1, 1),
            "order_date_to": date(2026, 12, 31),
            "sort": "-order_date",
            "page": 2,
            "page_size": 10,
        }


class TestUpdateSupplierRevalidation:
    """PurchaseOrderService.update only re-validates the supplier when
    supplier_id is actually present in the payload AND differs from the
    order's current supplier - mirrors PurchaseService.update's
    company_id handling exactly."""

    async def test_unchanged_supplier_id_does_not_call_supplier_service_again(self) -> None:
        supplier_id = uuid.uuid4()
        order = _make_purchase_order(status=PurchaseOrderStatus.DRAFT, supplier_id=supplier_id)
        fake_supplier_service = _FakeSupplierService(
            supplier=_make_supplier_response(id=supplier_id)
        )

        class _GetByIdRepo(_FakeRepo):
            async def get_by_id(
                self, purchase_order_id: uuid.UUID, tenant_id: uuid.UUID
            ) -> PurchaseOrder | None:
                return order

        service = PurchaseOrderService.__new__(PurchaseOrderService)
        service._repo = _GetByIdRepo([], 0)  # type: ignore[assignment]
        service._supplier_service = fake_supplier_service  # type: ignore[assignment]
        service._session = _NoOpSession()  # type: ignore[assignment]

        payload = PurchaseOrderUpdateRequest(supplier_id=supplier_id, remarks="Same supplier")
        await service.update(order.id, payload, tenant_id=order.tenant_id, actor_id=uuid.uuid4())

        assert fake_supplier_service.get_calls == []
        assert order.remarks == "Same supplier"


class _NoOpSession:
    """Stands in for AsyncSession - PurchaseOrderService.update only calls
    commit()/refresh() on it, neither of which this test cares about."""

    async def commit(self) -> None:
        return None

    async def refresh(self, _obj: object) -> None:
        return None


class _FakeItemRepo:
    def __init__(self, item: PurchaseOrderItem | None) -> None:
        self._item = item
        self.get_item_calls: list[tuple[uuid.UUID, uuid.UUID, uuid.UUID]] = []

    async def get_item_by_id(
        self, item_id: uuid.UUID, purchase_order_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PurchaseOrderItem | None:
        self.get_item_calls.append((item_id, purchase_order_id, tenant_id))
        return self._item


class TestGetItemOrRaise:
    """PurchaseOrderService._get_item_or_raise - the same "item id exists
    but on a different order/tenant is not found" scoping
    PurchaseRepository.get_item_by_id (already scoped by both ids) relies
    on."""

    async def test_returns_the_item_when_found(self) -> None:
        item = PurchaseOrderItem(
            tenant_id=uuid.uuid4(),
            purchase_order_id=uuid.uuid4(),
            line_number=1,
            quantity=Decimal("1.000"),
            unit="KG",
            rate=Decimal("1.0000"),
        )
        service = PurchaseOrderService.__new__(PurchaseOrderService)
        fake_repo = _FakeItemRepo(item)
        service._repo = fake_repo  # type: ignore[assignment]

        result = await service._get_item_or_raise(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())

        assert result is item

    async def test_raises_when_repository_returns_none(self) -> None:
        service = PurchaseOrderService.__new__(PurchaseOrderService)
        service._repo = _FakeItemRepo(None)  # type: ignore[assignment]

        with pytest.raises(PurchaseOrderItemNotFoundError):
            await service._get_item_or_raise(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())


class _FakeConfirmRepo:
    """Stands in for PurchaseOrderRepository across confirm()'s full call
    surface - the locked lookup, item search, and sequence counter
    orchestration."""

    def __init__(self) -> None:
        self.locked_order: PurchaseOrder | None = None
        self.get_for_update_calls: list[tuple[uuid.UUID, uuid.UUID]] = []
        self.items_by_order: dict[uuid.UUID, list[PurchaseOrderItem]] = {}
        self.sequences: dict[tuple[uuid.UUID, str, str], PurchaseOrderSequence] = {}
        self.ensure_sequence_calls: list[tuple[uuid.UUID, str, str]] = []

    async def get_by_id_for_update(
        self, purchase_order_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PurchaseOrder | None:
        self.get_for_update_calls.append((purchase_order_id, tenant_id))
        return self.locked_order

    async def search_items(
        self, purchase_order_id: uuid.UUID, tenant_id: uuid.UUID, **kwargs: Any
    ) -> list[PurchaseOrderItem]:
        return self.items_by_order.get(purchase_order_id, [])

    async def ensure_sequence_row(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> None:
        self.ensure_sequence_calls.append((tenant_id, prefix, fiscal_year))
        key = (tenant_id, prefix, fiscal_year)
        if key not in self.sequences:
            self.sequences[key] = PurchaseOrderSequence(
                tenant_id=tenant_id, prefix=prefix, fiscal_year=fiscal_year, last_number=0
            )

    async def get_sequence_for_update(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> PurchaseOrderSequence:
        return self.sequences[(tenant_id, prefix, fiscal_year)]


class _FakeSupplierServiceNoOutstandingMethods:
    """Deliberately has NO increase_outstanding/recalculate_outstanding
    method at all - if PurchaseOrderService.confirm ever touched supplier
    outstanding (it must not: a PO is a commitment, not a bill), this fake
    would raise AttributeError and fail the test loudly."""


class _FakeConfirmSession:
    """Stands in for AsyncSession - confirm() only ever calls .rollback()/
    .commit()/.refresh() on it."""

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


def _confirm_service_with_fakes(
    order: PurchaseOrder | None, items: list[PurchaseOrderItem]
) -> tuple[PurchaseOrderService, _FakeConfirmRepo, _FakeConfirmSession]:
    service = PurchaseOrderService.__new__(PurchaseOrderService)
    fake_repo = _FakeConfirmRepo()
    fake_repo.locked_order = order
    if order is not None:
        fake_repo.items_by_order[order.id] = items
    fake_session = _FakeConfirmSession()
    service._repo = fake_repo  # type: ignore[assignment]
    service._supplier_service = _FakeSupplierServiceNoOutstandingMethods()  # type: ignore[assignment]
    service._session = fake_session  # type: ignore[assignment]
    return service, fake_repo, fake_session


class TestConfirmSuccess:
    async def test_assigns_number_status_confirmed_and_never_touches_supplier(self) -> None:
        order = _make_purchase_order(
            status=PurchaseOrderStatus.DRAFT, order_date=date(2026, 7, 22), po_number=None
        )
        item = _make_purchase_order_item(
            purchase_order_id=order.id,
            tenant_id=order.tenant_id,
            quantity=Decimal("10"),
            rate=Decimal("100"),
        )
        service, fake_repo, fake_session = _confirm_service_with_fakes(order, [item])

        result = await service.confirm(order.id, tenant_id=order.tenant_id, actor_id=uuid.uuid4())

        assert result.status == PurchaseOrderStatus.CONFIRMED
        assert result.po_number == "PO/2026-27/00001"
        assert order.confirmed_at is not None
        assert result.total_amount == Decimal("1000.00")
        assert fake_session.commit_calls == 1
        assert fake_session.rollback_calls == 0

    async def test_locks_the_order_row_via_for_update_lookup(self) -> None:
        order = _make_purchase_order(status=PurchaseOrderStatus.DRAFT, order_date=date(2026, 7, 22))
        item = _make_purchase_order_item(purchase_order_id=order.id, tenant_id=order.tenant_id)
        service, fake_repo, _ = _confirm_service_with_fakes(order, [item])

        await service.confirm(order.id, tenant_id=order.tenant_id, actor_id=uuid.uuid4())

        assert fake_repo.get_for_update_calls == [(order.id, order.tenant_id)]


class TestConfirmRollback:
    async def test_unknown_order_rolls_back_and_raises_not_found(self) -> None:
        service, _, fake_session = _confirm_service_with_fakes(None, [])

        with pytest.raises(PurchaseOrderNotFoundError):
            await service.confirm(uuid.uuid4(), tenant_id=uuid.uuid4(), actor_id=uuid.uuid4())

        assert fake_session.rollback_calls == 1
        assert fake_session.commit_calls == 0

    async def test_already_confirmed_order_rolls_back_and_raises_not_draft(self) -> None:
        order = _make_purchase_order(status=PurchaseOrderStatus.CONFIRMED)
        service, _, fake_session = _confirm_service_with_fakes(order, [])

        with pytest.raises(PurchaseOrderNotDraftError):
            await service.confirm(order.id, tenant_id=order.tenant_id, actor_id=uuid.uuid4())

        assert fake_session.rollback_calls == 1
        assert fake_session.commit_calls == 0

    async def test_cancelled_order_rolls_back_and_raises_not_draft(self) -> None:
        order = _make_purchase_order(status=PurchaseOrderStatus.CANCELLED)
        service, _, fake_session = _confirm_service_with_fakes(order, [])

        with pytest.raises(PurchaseOrderNotDraftError):
            await service.confirm(order.id, tenant_id=order.tenant_id, actor_id=uuid.uuid4())

        assert fake_session.rollback_calls == 1

    async def test_empty_order_rolls_back_and_raises_empty(self) -> None:
        order = _make_purchase_order(status=PurchaseOrderStatus.DRAFT)
        service, _, fake_session = _confirm_service_with_fakes(order, [])

        with pytest.raises(PurchaseOrderEmptyError):
            await service.confirm(order.id, tenant_id=order.tenant_id, actor_id=uuid.uuid4())

        assert fake_session.rollback_calls == 1
        assert fake_session.commit_calls == 0

    async def test_order_is_not_mutated_after_a_failed_empty_confirm(self) -> None:
        order = _make_purchase_order(status=PurchaseOrderStatus.DRAFT, po_number=None)
        service, _, _ = _confirm_service_with_fakes(order, [])

        with pytest.raises(PurchaseOrderEmptyError):
            await service.confirm(order.id, tenant_id=order.tenant_id, actor_id=uuid.uuid4())

        assert order.status == PurchaseOrderStatus.DRAFT
        assert order.po_number is None
        assert order.confirmed_at is None


class TestAllocatePurchaseOrderNumber:
    """PurchaseOrderService._allocate_purchase_order_number - the
    counter-orchestration logic (fiscal year computation, ensure-then-lock,
    increment). The actual concurrency guarantee (SELECT ... FOR UPDATE
    serializing two real transactions) can only be verified against a real
    database - see tests/integration/test_purchase_order_repository.py."""

    async def test_first_allocation_for_a_fiscal_year_starts_at_one(self) -> None:
        service = PurchaseOrderService.__new__(PurchaseOrderService)
        fake_repo = _FakeConfirmRepo()
        service._repo = fake_repo  # type: ignore[assignment]
        order = _make_purchase_order(order_date=date(2026, 7, 22))

        number = await service._allocate_purchase_order_number(order, uuid.uuid4())

        assert number == "PO/2026-27/00001"

    async def test_second_allocation_for_the_same_fiscal_year_increments(self) -> None:
        service = PurchaseOrderService.__new__(PurchaseOrderService)
        fake_repo = _FakeConfirmRepo()
        service._repo = fake_repo  # type: ignore[assignment]
        order = _make_purchase_order(order_date=date(2026, 7, 22))
        tenant_id = uuid.uuid4()

        await service._allocate_purchase_order_number(order, tenant_id)
        second = await service._allocate_purchase_order_number(order, tenant_id)

        assert second == "PO/2026-27/00002"

    async def test_different_fiscal_years_get_independent_counters(self) -> None:
        service = PurchaseOrderService.__new__(PurchaseOrderService)
        fake_repo = _FakeConfirmRepo()
        service._repo = fake_repo  # type: ignore[assignment]
        tenant_id = uuid.uuid4()
        early_fy = _make_purchase_order(order_date=date(2026, 3, 15))  # FY 2025-26
        late_fy = _make_purchase_order(order_date=date(2026, 7, 22))  # FY 2026-27

        early_number = await service._allocate_purchase_order_number(early_fy, tenant_id)
        late_number = await service._allocate_purchase_order_number(late_fy, tenant_id)

        assert early_number == "PO/2025-26/00001"
        assert late_number == "PO/2026-27/00001"

    async def test_ensures_sequence_row_before_locking_it(self) -> None:
        service = PurchaseOrderService.__new__(PurchaseOrderService)
        fake_repo = _FakeConfirmRepo()
        service._repo = fake_repo  # type: ignore[assignment]
        order = _make_purchase_order(order_date=date(2026, 7, 22))
        tenant_id = uuid.uuid4()

        await service._allocate_purchase_order_number(order, tenant_id)

        assert fake_repo.ensure_sequence_calls == [(tenant_id, "PO", "2026-27")]


class _FakeLifecycleRepo:
    def __init__(self, order: PurchaseOrder | None) -> None:
        self._order = order
        self.get_for_update_calls: list[tuple[uuid.UUID, uuid.UUID]] = []

    async def get_by_id_for_update(
        self, purchase_order_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PurchaseOrder | None:
        self.get_for_update_calls.append((purchase_order_id, tenant_id))
        return self._order


class _FakeLifecycleSession:
    def __init__(self) -> None:
        self.commit_calls = 0
        self.refresh_calls: list[object] = []

    async def commit(self) -> None:
        self.commit_calls += 1

    async def refresh(self, obj: object) -> None:
        self.refresh_calls.append(obj)


def _lifecycle_service_with_fakes(
    order: PurchaseOrder | None,
) -> tuple[PurchaseOrderService, _FakeLifecycleSession]:
    service = PurchaseOrderService.__new__(PurchaseOrderService)
    service._repo = _FakeLifecycleRepo(order)  # type: ignore[assignment]
    fake_session = _FakeLifecycleSession()
    service._session = fake_session  # type: ignore[assignment]
    return service, fake_session


class TestCancel:
    @pytest.mark.parametrize("status", [PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.CONFIRMED])
    async def test_draft_or_confirmed_can_be_cancelled(self, status: PurchaseOrderStatus) -> None:
        order = _make_purchase_order(status=status)
        service, fake_session = _lifecycle_service_with_fakes(order)

        result = await service.cancel(order.id, tenant_id=order.tenant_id, actor_id=uuid.uuid4())

        assert result.status == PurchaseOrderStatus.CANCELLED
        assert fake_session.commit_calls == 1

    @pytest.mark.parametrize(
        "status", [PurchaseOrderStatus.FULFILLED, PurchaseOrderStatus.CANCELLED]
    )
    async def test_fulfilled_or_cancelled_raises_invalid_transition(
        self, status: PurchaseOrderStatus
    ) -> None:
        order = _make_purchase_order(status=status)
        service, fake_session = _lifecycle_service_with_fakes(order)

        with pytest.raises(PurchaseOrderInvalidTransitionError):
            await service.cancel(order.id, tenant_id=order.tenant_id, actor_id=uuid.uuid4())

        assert fake_session.commit_calls == 0

    async def test_unknown_order_raises_not_found(self) -> None:
        service, _ = _lifecycle_service_with_fakes(None)

        with pytest.raises(PurchaseOrderNotFoundError):
            await service.cancel(uuid.uuid4(), tenant_id=uuid.uuid4(), actor_id=uuid.uuid4())


class TestFulfill:
    async def test_confirmed_can_be_fulfilled(self) -> None:
        order = _make_purchase_order(status=PurchaseOrderStatus.CONFIRMED)
        service, fake_session = _lifecycle_service_with_fakes(order)

        result = await service.fulfill(order.id, tenant_id=order.tenant_id, actor_id=uuid.uuid4())

        assert result.status == PurchaseOrderStatus.FULFILLED
        assert fake_session.commit_calls == 1

    @pytest.mark.parametrize(
        "status",
        [PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.FULFILLED, PurchaseOrderStatus.CANCELLED],
    )
    async def test_non_confirmed_raises_invalid_transition(
        self, status: PurchaseOrderStatus
    ) -> None:
        order = _make_purchase_order(status=status)
        service, fake_session = _lifecycle_service_with_fakes(order)

        with pytest.raises(PurchaseOrderInvalidTransitionError):
            await service.fulfill(order.id, tenant_id=order.tenant_id, actor_id=uuid.uuid4())

        assert fake_session.commit_calls == 0

    async def test_unknown_order_raises_not_found(self) -> None:
        service, _ = _lifecycle_service_with_fakes(None)

        with pytest.raises(PurchaseOrderNotFoundError):
            await service.fulfill(uuid.uuid4(), tenant_id=uuid.uuid4(), actor_id=uuid.uuid4())
