import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.core.errors import ConflictError
from app.modules.suppliers.constants import SupplierStatus
from app.modules.suppliers.exceptions import (
    DuplicateSupplierCodeError,
    DuplicateSupplierNameError,
    SupplierOutstandingCalculationError,
)
from app.modules.suppliers.models import Supplier
from app.modules.suppliers.schemas import SupplierListParams
from app.modules.suppliers.service import SupplierService


class _FakeConstraintCause(Exception):
    """`__cause__` must be a BaseException, so this stands in for the part of
    asyncpg's UniqueViolationError that _translate_integrity_error reads."""

    def __init__(self, constraint_name: str) -> None:
        super().__init__("fake constraint violation")
        self.constraint_name = constraint_name


class _FakeDriverError(Exception):
    """Stands in for asyncpg's UniqueViolationError, chained as __cause__."""

    def __init__(self, constraint_name: str) -> None:
        super().__init__("duplicate key value violates unique constraint")
        self.__cause__ = _FakeConstraintCause(constraint_name)


class _FakeIntegrityError(Exception):
    """Stands in for sqlalchemy.exc.IntegrityError - only `.orig` is read."""

    def __init__(self, constraint_name: str) -> None:
        super().__init__("integrity error")
        self.orig = _FakeDriverError(constraint_name)


class _FakeRepo:
    def __init__(self, rows: list[Supplier], total: int) -> None:
        self.rows = rows
        self.total = total
        self.last_call: dict[str, Any] | None = None
        self.increase_calls: list[tuple[uuid.UUID, uuid.UUID, Decimal]] = []
        self.set_outstanding_calls: list[tuple[uuid.UUID, uuid.UUID, Decimal]] = []

    async def search(self, tenant_id: uuid.UUID, **kwargs: Any) -> tuple[list[Supplier], int]:
        self.last_call = {"tenant_id": tenant_id, **kwargs}
        return self.rows, self.total

    async def increase_outstanding_amount(
        self, supplier_id: uuid.UUID, tenant_id: uuid.UUID, amount: Decimal
    ) -> None:
        self.increase_calls.append((supplier_id, tenant_id, amount))

    async def set_outstanding_amount(
        self, supplier_id: uuid.UUID, tenant_id: uuid.UUID, amount: Decimal
    ) -> None:
        self.set_outstanding_calls.append((supplier_id, tenant_id, amount))


def _make_supplier(**overrides: Any) -> Supplier:
    """A Supplier that satisfies SupplierResponse validation without
    touching the DB - the non-nullable columns normally filled by
    server_default/TimestampMixin need explicit values since this object is
    never flushed."""
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "code": "SUP-1",
        "name": "Test Supplier",
        "status": SupplierStatus.ACTIVE,
        "credit_days": 0,
        "opening_balance": Decimal("0"),
        "outstanding_amount": Decimal("0"),
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return Supplier(**defaults)


def _service_with_fake_repo(rows: list[Supplier], total: int) -> tuple[SupplierService, _FakeRepo]:
    service = SupplierService.__new__(SupplierService)
    fake_repo = _FakeRepo(rows, total)
    service._repo = fake_repo  # type: ignore[assignment]
    return service, fake_repo


class TestIncreaseOutstanding:
    """SupplierService.increase_outstanding - used by PurchaseService.post
    (Sprint 11 Session 5) to credit the billing supplier's outstanding_amount
    in the same transaction as the purchase bill being posted."""

    async def test_forwards_supplier_tenant_and_amount_to_the_repository(self) -> None:
        service, fake_repo = _service_with_fake_repo([], total=0)
        supplier_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        await service.increase_outstanding(supplier_id, Decimal("23625.00"), tenant_id=tenant_id)

        assert fake_repo.increase_calls == [(supplier_id, tenant_id, Decimal("23625.00"))]


class TestRecalculateOutstanding:
    """SupplierService.recalculate_outstanding - Sprint 12 Session 4's
    outstanding engine. PurchaseService is the only caller; it sums this
    supplier's open purchase bills' balance_amount via its own
    PurchaseRepository and passes the raw total in - never incremented,
    always recomputed."""

    async def test_sets_outstanding_to_the_recomputed_total(self) -> None:
        service, fake_repo = _service_with_fake_repo([], total=0)
        supplier_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        await service.recalculate_outstanding(
            supplier_id, tenant_id=tenant_id, total_open_balance=Decimal("2500.00")
        )

        assert fake_repo.set_outstanding_calls == [(supplier_id, tenant_id, Decimal("2500.00"))]

    async def test_zero_balance_sets_outstanding_to_zero(self) -> None:
        service, fake_repo = _service_with_fake_repo([], total=0)
        supplier_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        await service.recalculate_outstanding(
            supplier_id, tenant_id=tenant_id, total_open_balance=Decimal("0")
        )

        assert fake_repo.set_outstanding_calls == [(supplier_id, tenant_id, Decimal("0.00"))]

    async def test_negative_total_raises_and_does_not_write(self) -> None:
        """Not reachable in practice - it is a SUM of balance_amount, which
        PurchaseService's own reconciliation guard never lets go negative -
        but SupplierService must not trust an input it did not itself
        validate, and must not persist a rejected value."""
        service, fake_repo = _service_with_fake_repo([], total=0)

        with pytest.raises(SupplierOutstandingCalculationError):
            await service.recalculate_outstanding(
                uuid.uuid4(), tenant_id=uuid.uuid4(), total_open_balance=Decimal("-0.01")
            )

        assert fake_repo.set_outstanding_calls == []


class TestTranslateIntegrityError:
    def test_code_constraint_maps_to_duplicate_code_error(self) -> None:
        exc = _FakeIntegrityError("ix_suppliers_tenant_code")
        result = SupplierService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert isinstance(result, DuplicateSupplierCodeError)

    def test_name_constraint_maps_to_duplicate_name_error(self) -> None:
        exc = _FakeIntegrityError("ix_suppliers_tenant_name")
        result = SupplierService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert isinstance(result, DuplicateSupplierNameError)

    def test_unknown_constraint_falls_back_to_generic_conflict(self) -> None:
        exc = _FakeIntegrityError("some_other_constraint")
        result = SupplierService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert type(result) is ConflictError

    def test_missing_orig_falls_back_to_generic_conflict(self) -> None:
        class _BareError(Exception):
            orig = None

        result = SupplierService._translate_integrity_error(_BareError())  # type: ignore[arg-type]
        assert type(result) is ConflictError


class TestListSuppliersPaginationMath:
    async def test_first_page_of_several(self) -> None:
        rows = [_make_supplier() for _ in range(2)]
        service, fake_repo = _service_with_fake_repo(rows, total=5)

        result = await service.list_suppliers(
            tenant_id=uuid.uuid4(), params=SupplierListParams(page=1, page_size=2)
        )

        assert len(result.data) == 2
        assert result.meta.total_records == 5
        assert result.meta.total_pages == 3
        assert result.meta.current_page == 1
        assert result.meta.has_previous is False
        assert result.meta.has_next is True
        assert fake_repo.last_call is not None

    async def test_last_page_has_no_next(self) -> None:
        rows = [_make_supplier()]
        service, _ = _service_with_fake_repo(rows, total=5)

        result = await service.list_suppliers(
            tenant_id=uuid.uuid4(), params=SupplierListParams(page=3, page_size=2)
        )

        assert result.meta.has_next is False
        assert result.meta.has_previous is True

    async def test_empty_result_gives_zero_pages(self) -> None:
        service, _ = _service_with_fake_repo([], total=0)

        result = await service.list_suppliers(
            tenant_id=uuid.uuid4(), params=SupplierListParams(page=1, page_size=20)
        )

        assert result.data == []
        assert result.meta.total_records == 0
        assert result.meta.total_pages == 0
        assert result.meta.has_next is False
        assert result.meta.has_previous is False

    async def test_filters_are_forwarded_to_the_repository(self) -> None:
        service, fake_repo = _service_with_fake_repo([], total=0)
        tenant_id = uuid.uuid4()

        await service.list_suppliers(
            tenant_id=tenant_id,
            params=SupplierListParams(
                q="coastal",
                status=SupplierStatus.INACTIVE,
                city="Mumbai",
                state="Maharashtra",
                sort="-name",
                page=2,
                page_size=10,
            ),
        )

        assert fake_repo.last_call == {
            "tenant_id": tenant_id,
            "q": "coastal",
            "status": SupplierStatus.INACTIVE,
            "city": "Mumbai",
            "state": "Maharashtra",
            "sort": "-name",
            "page": 2,
            "page_size": 10,
        }


class TestFindIdsByName:
    async def test_wraps_query_in_ilike_pattern(self) -> None:
        class _FakeFindRepo:
            def __init__(self) -> None:
                self.last_call: tuple[uuid.UUID, str] | None = None

            async def find_ids_by_name(self, tenant_id: uuid.UUID, pattern: str) -> list[uuid.UUID]:
                self.last_call = (tenant_id, pattern)
                return []

        service = SupplierService.__new__(SupplierService)
        fake_repo = _FakeFindRepo()
        service._repo = fake_repo  # type: ignore[assignment]
        tenant_id = uuid.uuid4()

        await service.find_ids_by_name(tenant_id, "  Ocean  ")

        assert fake_repo.last_call == (tenant_id, "%Ocean%")
