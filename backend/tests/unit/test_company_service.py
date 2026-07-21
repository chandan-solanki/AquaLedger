import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.core.errors import ConflictError
from app.modules.companies.constants import CompanyStatus, CompanyType
from app.modules.companies.exceptions import DuplicateCompanyCodeError, DuplicateCompanyNameError
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

    async def search(self, tenant_id: uuid.UUID, **kwargs: Any) -> tuple[list[Company], int]:
        self.last_call = {"tenant_id": tenant_id, **kwargs}
        return self.rows, self.total


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
                q="ocean", company_type=CompanyType.SUPPLIER, status=CompanyStatus.INACTIVE,
                city="Mumbai", state="Maharashtra", sort="-name", page=2, page_size=10,
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
