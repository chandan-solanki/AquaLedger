import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.errors import ConflictError
from app.modules.fish.constants import FishUnit
from app.modules.fish.exceptions import DuplicateFishCodeError, DuplicateFishNameError
from app.modules.fish.models import Fish
from app.modules.fish.schemas import FishListParams
from app.modules.fish.service import FishService


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
    def __init__(self, rows: list[Fish], total: int) -> None:
        self.rows = rows
        self.total = total
        self.last_call: dict[str, Any] | None = None

    async def search(self, tenant_id: uuid.UUID, **kwargs: Any) -> tuple[list[Fish], int]:
        self.last_call = {"tenant_id": tenant_id, **kwargs}
        return self.rows, self.total


def _make_fish(**overrides: Any) -> Fish:
    """A Fish that satisfies FishResponse validation without touching the DB -
    the non-nullable columns normally filled by server_default / TimestampMixin
    need explicit values since this object is never flushed."""
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "code": "F-1",
        "name": "Test Fish",
        "unit": FishUnit.KG,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return Fish(**defaults)


def _service_with_fake_repo(rows: list[Fish], total: int) -> tuple[FishService, _FakeRepo]:
    service = FishService.__new__(FishService)
    fake_repo = _FakeRepo(rows, total)
    service._repo = fake_repo  # type: ignore[assignment]
    return service, fake_repo


class TestTranslateIntegrityError:
    def test_code_constraint_maps_to_duplicate_code_error(self) -> None:
        exc = _FakeIntegrityError("ix_fish_tenant_code")
        result = FishService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert isinstance(result, DuplicateFishCodeError)

    def test_name_constraint_maps_to_duplicate_name_error(self) -> None:
        exc = _FakeIntegrityError("ix_fish_tenant_name")
        result = FishService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert isinstance(result, DuplicateFishNameError)

    def test_unknown_constraint_falls_back_to_generic_conflict(self) -> None:
        exc = _FakeIntegrityError("some_other_constraint")
        result = FishService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert type(result) is ConflictError

    def test_missing_orig_falls_back_to_generic_conflict(self) -> None:
        class _BareError(Exception):
            orig = None

        result = FishService._translate_integrity_error(_BareError())  # type: ignore[arg-type]
        assert type(result) is ConflictError


class TestListFishPaginationMath:
    async def test_first_page_of_several(self) -> None:
        rows = [_make_fish() for _ in range(2)]
        service, fake_repo = _service_with_fake_repo(rows, total=5)

        result = await service.list_fish(
            tenant_id=uuid.uuid4(), params=FishListParams(page=1, page_size=2)
        )

        assert len(result.data) == 2
        assert result.meta.total_records == 5
        assert result.meta.total_pages == 3
        assert result.meta.current_page == 1
        assert result.meta.has_previous is False
        assert result.meta.has_next is True
        assert fake_repo.last_call is not None

    async def test_last_page_has_no_next(self) -> None:
        rows = [_make_fish()]
        service, _ = _service_with_fake_repo(rows, total=5)

        result = await service.list_fish(
            tenant_id=uuid.uuid4(), params=FishListParams(page=3, page_size=2)
        )

        assert result.meta.has_next is False
        assert result.meta.has_previous is True

    async def test_empty_result_gives_zero_pages(self) -> None:
        service, _ = _service_with_fake_repo([], total=0)

        result = await service.list_fish(
            tenant_id=uuid.uuid4(), params=FishListParams(page=1, page_size=20)
        )

        assert result.data == []
        assert result.meta.total_records == 0
        assert result.meta.total_pages == 0
        assert result.meta.has_next is False
        assert result.meta.has_previous is False

    async def test_filters_are_forwarded_to_the_repository(self) -> None:
        service, fake_repo = _service_with_fake_repo([], total=0)
        tenant_id = uuid.uuid4()

        await service.list_fish(
            tenant_id=tenant_id,
            params=FishListParams(
                q="pomfret",
                category="Whitefish",
                unit=FishUnit.KG,
                is_active=True,
                sort="-name",
                page=2,
                page_size=10,
            ),
        )

        assert fake_repo.last_call == {
            "tenant_id": tenant_id,
            "q": "pomfret",
            "category": "Whitefish",
            "unit": FishUnit.KG,
            "is_active": True,
            "sort": "-name",
            "page": 2,
            "page_size": 10,
        }
