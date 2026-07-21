import uuid
from datetime import UTC, date, datetime
from typing import Any

import pytest

from app.core.errors import ConflictError
from app.modules.boats.exceptions import (
    BoatCompanyNotFoundError,
    DuplicateBoatCodeError,
    DuplicateBoatRegistrationNumberError,
)
from app.modules.boats.models import Boat
from app.modules.boats.schemas import BoatListParams
from app.modules.boats.service import BoatService
from app.modules.companies.exceptions import CompanyNotFoundError


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
    def __init__(self, rows: list[Boat], total: int) -> None:
        self.rows = rows
        self.total = total
        self.last_call: dict[str, Any] | None = None

    async def search(self, tenant_id: uuid.UUID, **kwargs: Any) -> tuple[list[Boat], int]:
        self.last_call = {"tenant_id": tenant_id, **kwargs}
        return self.rows, self.total


class _FakeCompanyService:
    """Stands in for CompanyService.get - either returns a stub or raises,
    matching the two branches BoatService._ensure_company_exists handles."""

    def __init__(self, *, raises: bool = False) -> None:
        self.raises = raises
        self.calls: list[tuple[uuid.UUID, uuid.UUID]] = []

    async def get(self, company_id: uuid.UUID, *, tenant_id: uuid.UUID) -> object:
        self.calls.append((company_id, tenant_id))
        if self.raises:
            raise CompanyNotFoundError("Company not found")
        return object()


def _make_boat(**overrides: Any) -> Boat:
    """A Boat that satisfies BoatResponse validation without touching the DB -
    the non-nullable columns normally filled by server_default / TimestampMixin
    need explicit values since this object is never flushed."""
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "company_id": uuid.uuid4(),
        "code": "B-1",
        "name": "Test Boat",
        "registration_number": "REG-1",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return Boat(**defaults)


def _service_with_fakes(
    rows: list[Boat], total: int, *, company_raises: bool = False
) -> tuple[BoatService, _FakeRepo, _FakeCompanyService]:
    service = BoatService.__new__(BoatService)
    fake_repo = _FakeRepo(rows, total)
    fake_company_service = _FakeCompanyService(raises=company_raises)
    service._repo = fake_repo  # type: ignore[assignment]
    service._company_service = fake_company_service  # type: ignore[assignment]
    return service, fake_repo, fake_company_service


class TestTranslateIntegrityError:
    def test_code_constraint_maps_to_duplicate_code_error(self) -> None:
        exc = _FakeIntegrityError("ix_boats_tenant_code")
        result = BoatService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert isinstance(result, DuplicateBoatCodeError)

    def test_registration_constraint_maps_to_duplicate_registration_error(self) -> None:
        exc = _FakeIntegrityError("ix_boats_tenant_registration")
        result = BoatService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert isinstance(result, DuplicateBoatRegistrationNumberError)

    def test_unknown_constraint_falls_back_to_generic_conflict(self) -> None:
        exc = _FakeIntegrityError("some_other_constraint")
        result = BoatService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert type(result) is ConflictError

    def test_missing_orig_falls_back_to_generic_conflict(self) -> None:
        class _BareError(Exception):
            orig = None

        result = BoatService._translate_integrity_error(_BareError())  # type: ignore[arg-type]
        assert type(result) is ConflictError


class TestEnsureCompanyExists:
    async def test_passes_through_when_company_exists(self) -> None:
        service, _, fake_company_service = _service_with_fakes([], total=0, company_raises=False)
        company_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        await service._ensure_company_exists(company_id, tenant_id)

        assert fake_company_service.calls == [(company_id, tenant_id)]

    async def test_translates_company_not_found_to_boat_company_not_found(self) -> None:
        service, _, _ = _service_with_fakes([], total=0, company_raises=True)

        with pytest.raises(BoatCompanyNotFoundError):
            await service._ensure_company_exists(uuid.uuid4(), uuid.uuid4())


class TestListBoatsPaginationMath:
    async def test_first_page_of_several(self) -> None:
        rows = [_make_boat() for _ in range(2)]
        service, fake_repo, _ = _service_with_fakes(rows, total=5)

        result = await service.list_boats(
            tenant_id=uuid.uuid4(), params=BoatListParams(page=1, page_size=2)
        )

        assert len(result.data) == 2
        assert result.meta.total_records == 5
        assert result.meta.total_pages == 3
        assert result.meta.current_page == 1
        assert result.meta.has_previous is False
        assert result.meta.has_next is True
        assert fake_repo.last_call is not None

    async def test_last_page_has_no_next(self) -> None:
        rows = [_make_boat()]
        service, _, _ = _service_with_fakes(rows, total=5)

        result = await service.list_boats(
            tenant_id=uuid.uuid4(), params=BoatListParams(page=3, page_size=2)
        )

        assert result.meta.has_next is False
        assert result.meta.has_previous is True

    async def test_empty_result_gives_zero_pages(self) -> None:
        service, _, _ = _service_with_fakes([], total=0)

        result = await service.list_boats(
            tenant_id=uuid.uuid4(), params=BoatListParams(page=1, page_size=20)
        )

        assert result.data == []
        assert result.meta.total_records == 0
        assert result.meta.total_pages == 0
        assert result.meta.has_next is False
        assert result.meta.has_previous is False

    async def test_filters_are_forwarded_to_the_repository(self) -> None:
        service, fake_repo, _ = _service_with_fakes([], total=0)
        tenant_id = uuid.uuid4()
        company_id = uuid.uuid4()

        await service.list_boats(
            tenant_id=tenant_id,
            params=BoatListParams(
                q="falcon",
                boat_type="trawler",
                company_id=company_id,
                is_active=True,
                insurance_expired=False,
                license_expired=True,
                sort="-name",
                page=2,
                page_size=10,
            ),
        )

        assert fake_repo.last_call == {
            "tenant_id": tenant_id,
            "q": "falcon",
            "boat_type": "trawler",
            "company_id": company_id,
            "is_active": True,
            "insurance_expired": False,
            "license_expired": True,
            "sort": "-name",
            "page": 2,
            "page_size": 10,
        }


def test_make_boat_helper_produces_a_response_compatible_row() -> None:
    """Sanity check on the test helper itself - insurance/license expiry are
    optional date columns and shouldn't be required to build a valid row."""
    boat = _make_boat(insurance_expiry=date(2027, 1, 1))
    assert boat.insurance_expiry == date(2027, 1, 1)
    assert boat.license_expiry is None
