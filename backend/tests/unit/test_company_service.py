import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.core.errors import ConflictError
from app.modules.companies.constants import CompanyStatus, CompanyType
from app.modules.companies.exceptions import (
    CompanyOutstandingCalculationError,
    DuplicateCompanyCodeError,
    DuplicateCompanyNameError,
)
from app.modules.companies.models import Company
from app.modules.companies.schemas import CompanyListParams
from app.modules.companies.service import CompanyService


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
    def __init__(self, rows: list[Company], total: int) -> None:
        self.rows = rows
        self.total = total
        self.last_call: dict[str, Any] | None = None
        self.increase_calls: list[tuple[uuid.UUID, uuid.UUID, Decimal]] = []
        self.set_outstanding_calls: list[tuple[uuid.UUID, uuid.UUID, Decimal]] = []

    async def search(self, tenant_id: uuid.UUID, **kwargs: Any) -> tuple[list[Company], int]:
        self.last_call = {"tenant_id": tenant_id, **kwargs}
        return self.rows, self.total

    async def increase_outstanding_amount(
        self, company_id: uuid.UUID, tenant_id: uuid.UUID, amount: Decimal
    ) -> None:
        self.increase_calls.append((company_id, tenant_id, amount))

    async def set_outstanding_amount(
        self, company_id: uuid.UUID, tenant_id: uuid.UUID, amount: Decimal
    ) -> None:
        self.set_outstanding_calls.append((company_id, tenant_id, amount))


def _make_company(**overrides: Any) -> Company:
    """A Company that satisfies CompanyResponse validation without touching
    the DB - the non-nullable columns normally filled by server_default /
    TimestampMixin need explicit values since this object is never flushed."""
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "code": "C-1",
        "name": "Test Co",
        "company_type": CompanyType.CUSTOMER,
        "status": CompanyStatus.ACTIVE,
        "credit_limit": Decimal("0"),
        "credit_days": 0,
        "opening_balance": Decimal("0"),
        "outstanding_amount": Decimal("0"),
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return Company(**defaults)


def _service_with_fake_repo(rows: list[Company], total: int) -> tuple[CompanyService, _FakeRepo]:
    service = CompanyService.__new__(CompanyService)
    fake_repo = _FakeRepo(rows, total)
    service._repo = fake_repo  # type: ignore[assignment]
    return service, fake_repo


class TestTranslateIntegrityError:
    def test_code_constraint_maps_to_duplicate_code_error(self) -> None:
        exc = _FakeIntegrityError("ix_companies_tenant_code")
        result = CompanyService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert isinstance(result, DuplicateCompanyCodeError)

    def test_name_constraint_maps_to_duplicate_name_error(self) -> None:
        exc = _FakeIntegrityError("ix_companies_tenant_name")
        result = CompanyService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert isinstance(result, DuplicateCompanyNameError)

    def test_unknown_constraint_falls_back_to_generic_conflict(self) -> None:
        exc = _FakeIntegrityError("some_other_constraint")
        result = CompanyService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert type(result) is ConflictError

    def test_missing_orig_falls_back_to_generic_conflict(self) -> None:
        class _BareError(Exception):
            orig = None

        result = CompanyService._translate_integrity_error(_BareError())  # type: ignore[arg-type]
        assert type(result) is ConflictError


class TestListCompaniesPaginationMath:
    async def test_first_page_of_several(self) -> None:
        rows = [_make_company() for _ in range(2)]
        service, fake_repo = _service_with_fake_repo(rows, total=5)

        result = await service.list_companies(
            tenant_id=uuid.uuid4(), params=CompanyListParams(page=1, page_size=2)
        )

        assert len(result.data) == 2
        assert result.meta.total_records == 5
        assert result.meta.total_pages == 3
        assert result.meta.current_page == 1
        assert result.meta.has_previous is False
        assert result.meta.has_next is True
        assert fake_repo.last_call is not None

    async def test_last_page_has_no_next(self) -> None:
        rows = [_make_company()]
        service, _ = _service_with_fake_repo(rows, total=5)

        result = await service.list_companies(
            tenant_id=uuid.uuid4(), params=CompanyListParams(page=3, page_size=2)
        )

        assert result.meta.has_next is False
        assert result.meta.has_previous is True

    async def test_empty_result_gives_zero_pages(self) -> None:
        service, _ = _service_with_fake_repo([], total=0)

        result = await service.list_companies(
            tenant_id=uuid.uuid4(), params=CompanyListParams(page=1, page_size=20)
        )

        assert result.data == []
        assert result.meta.total_records == 0
        assert result.meta.total_pages == 0
        assert result.meta.has_next is False
        assert result.meta.has_previous is False

    async def test_filters_are_forwarded_to_the_repository(self) -> None:
        service, fake_repo = _service_with_fake_repo([], total=0)
        tenant_id = uuid.uuid4()

        await service.list_companies(
            tenant_id=tenant_id,
            params=CompanyListParams(
                q="ocean",
                company_type=CompanyType.SUPPLIER,
                status=CompanyStatus.INACTIVE,
                city="Mumbai",
                state="Maharashtra",
                sort="-name",
                page=2,
                page_size=10,
            ),
        )

        assert fake_repo.last_call == {
            "tenant_id": tenant_id,
            "q": "ocean",
            "company_type": CompanyType.SUPPLIER,
            "status": CompanyStatus.INACTIVE,
            "city": "Mumbai",
            "state": "Maharashtra",
            "sort": "-name",
            "page": 2,
            "page_size": 10,
        }


class TestIncreaseOutstanding:
    """CompanyService.increase_outstanding - used by InvoiceService.issue
    (Sprint 9 Session 5) to credit the billed company's outstanding_amount
    in the same transaction as the invoice being issued."""

    async def test_forwards_company_tenant_and_amount_to_the_repository(self) -> None:
        service, fake_repo = _service_with_fake_repo([], total=0)
        company_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        await service.increase_outstanding(company_id, Decimal("23875.00"), tenant_id=tenant_id)

        assert fake_repo.increase_calls == [(company_id, tenant_id, Decimal("23875.00"))]


class TestRecalculateOutstanding:
    """CompanyService.recalculate_outstanding - Sprint 10 Session 4's
    outstanding engine. InvoiceService is the only caller; it sums this
    company's open invoices' balance_amount via its own InvoiceRepository
    and passes the raw total in - never incremented, always recomputed."""

    async def test_sets_outstanding_to_the_recomputed_total(self) -> None:
        service, fake_repo = _service_with_fake_repo([], total=0)
        company_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        await service.recalculate_outstanding(
            company_id, tenant_id=tenant_id, total_open_balance=Decimal("2500.00")
        )

        assert fake_repo.set_outstanding_calls == [(company_id, tenant_id, Decimal("2500.00"))]

    async def test_zero_balance_sets_outstanding_to_zero(self) -> None:
        service, fake_repo = _service_with_fake_repo([], total=0)
        company_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        await service.recalculate_outstanding(
            company_id, tenant_id=tenant_id, total_open_balance=Decimal("0")
        )

        assert fake_repo.set_outstanding_calls == [(company_id, tenant_id, Decimal("0.00"))]

    async def test_negative_total_raises_and_does_not_write(self) -> None:
        """Not reachable in practice - it is a SUM of balance_amount, which
        InvoiceService's own reconciliation guard never lets go negative -
        but CompanyService must not trust an input it did not itself
        validate, and must not persist a rejected value."""
        service, fake_repo = _service_with_fake_repo([], total=0)

        with pytest.raises(CompanyOutstandingCalculationError):
            await service.recalculate_outstanding(
                uuid.uuid4(), tenant_id=uuid.uuid4(), total_open_balance=Decimal("-0.01")
            )

        assert fake_repo.set_outstanding_calls == []
