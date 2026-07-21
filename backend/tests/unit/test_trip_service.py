import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.core.errors import ConflictError
from app.modules.boats.exceptions import BoatNotFoundError
from app.modules.trips.constants import TripStatus, TripType
from app.modules.trips.exceptions import (
    DuplicateTripNumberError,
    TripBoatAlreadyActiveError,
    TripBoatNotActiveError,
    TripBoatNotFoundError,
    TripInvalidReturnDatetimeError,
)
from app.modules.trips.models import Trip
from app.modules.trips.schemas import TripListParams
from app.modules.trips.service import TripService


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


class _BoatStub:
    """Stands in for a BoatResponse - only .id/.is_active are read by TripService."""

    def __init__(self, boat_id: uuid.UUID | None = None, *, is_active: bool = True) -> None:
        self.id = boat_id or uuid.uuid4()
        self.is_active = is_active


class _FakeTripRepo:
    def __init__(self, rows: list[Trip] | None = None, total: int = 0) -> None:
        self.rows = rows or []
        self.total = total
        self.last_search_call: dict[str, Any] | None = None

    async def search(self, tenant_id: uuid.UUID, **kwargs: Any) -> tuple[list[Trip], int]:
        self.last_search_call = {"tenant_id": tenant_id, **kwargs}
        return self.rows, self.total


class _FakeBoatService:
    """Stands in for BoatService.get/find_ids_by_name - the two entry points
    TripService calls (ARCHITECTURE.md §2 - cross-module access goes through
    the other module's service, never its repository)."""

    def __init__(self, *, boat: _BoatStub | None = None, raises: bool = False) -> None:
        self.boat = boat
        self.raises = raises
        self.get_calls: list[tuple[uuid.UUID, uuid.UUID]] = []
        self.find_ids_calls: list[tuple[uuid.UUID, str]] = []
        self.find_ids_result: list[uuid.UUID] = []

    async def get(self, boat_id: uuid.UUID, *, tenant_id: uuid.UUID) -> _BoatStub:
        self.get_calls.append((boat_id, tenant_id))
        if self.raises:
            raise BoatNotFoundError("Boat not found")
        assert self.boat is not None
        return self.boat

    async def find_ids_by_name(self, tenant_id: uuid.UUID, q: str) -> list[uuid.UUID]:
        self.find_ids_calls.append((tenant_id, q))
        return self.find_ids_result


def _make_trip(**overrides: Any) -> Trip:
    """A Trip that satisfies TripResponse validation without touching the DB -
    the non-nullable columns normally filled by server_default / TimestampMixin
    need explicit values since this object is never flushed."""
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "boat_id": uuid.uuid4(),
        "trip_number": "T-1",
        "trip_type": TripType.FISHING,
        "departure_datetime": now,
        "status": TripStatus.PLANNED,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return Trip(**defaults)


def _service_with_fakes(
    rows: list[Trip] | None = None,
    total: int = 0,
    *,
    boat: _BoatStub | None = None,
    boat_raises: bool = False,
) -> tuple[TripService, _FakeTripRepo, _FakeBoatService]:
    service = TripService.__new__(TripService)
    fake_repo = _FakeTripRepo(rows, total)
    fake_boat_service = _FakeBoatService(boat=boat, raises=boat_raises)
    service._repo = fake_repo  # type: ignore[assignment]
    service._boat_service = fake_boat_service  # type: ignore[assignment]
    return service, fake_repo, fake_boat_service


class TestTranslateIntegrityError:
    def test_trip_number_constraint_maps_to_duplicate_error(self) -> None:
        exc = _FakeIntegrityError("ix_trips_tenant_trip_number")
        result = TripService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert isinstance(result, DuplicateTripNumberError)

    def test_boat_single_active_trip_constraint_maps_to_already_active_error(self) -> None:
        exc = _FakeIntegrityError("ix_trips_boat_single_active")
        result = TripService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert isinstance(result, TripBoatAlreadyActiveError)

    def test_unknown_constraint_falls_back_to_generic_conflict(self) -> None:
        exc = _FakeIntegrityError("some_other_constraint")
        result = TripService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert type(result) is ConflictError

    def test_missing_orig_falls_back_to_generic_conflict(self) -> None:
        class _BareError(Exception):
            orig = None

        result = TripService._translate_integrity_error(_BareError())  # type: ignore[arg-type]
        assert type(result) is ConflictError


class TestGetActiveBoatOrRaise:
    async def test_returns_boat_when_active(self) -> None:
        boat = _BoatStub(is_active=True)
        service, _, _ = _service_with_fakes(boat=boat)

        result = await service._get_active_boat_or_raise(boat.id, uuid.uuid4())

        assert result is boat  # type: ignore[comparison-overlap]

    async def test_raises_not_found_when_boat_missing(self) -> None:
        service, _, _ = _service_with_fakes(boat_raises=True)

        with pytest.raises(TripBoatNotFoundError):
            await service._get_active_boat_or_raise(uuid.uuid4(), uuid.uuid4())

    async def test_raises_not_active_when_boat_inactive(self) -> None:
        boat = _BoatStub(is_active=False)
        service, _, _ = _service_with_fakes(boat=boat)

        with pytest.raises(TripBoatNotActiveError):
            await service._get_active_boat_or_raise(boat.id, uuid.uuid4())

    async def test_tenant_scoping_is_forwarded_to_boat_service(self) -> None:
        boat = _BoatStub(is_active=True)
        service, _, fake_boat_service = _service_with_fakes(boat=boat)
        tenant_id = uuid.uuid4()

        await service._get_active_boat_or_raise(boat.id, tenant_id)

        assert fake_boat_service.get_calls == [(boat.id, tenant_id)]


class TestEnsureReturnAfterDeparture:
    def test_none_actual_return_is_allowed(self) -> None:
        TripService._ensure_return_after_departure(datetime.now(UTC), None)

    def test_return_after_departure_is_allowed(self) -> None:
        now = datetime.now(UTC)
        TripService._ensure_return_after_departure(now, now + timedelta(days=1))

    def test_return_equal_to_departure_is_allowed(self) -> None:
        now = datetime.now(UTC)
        TripService._ensure_return_after_departure(now, now)

    def test_return_before_departure_raises(self) -> None:
        now = datetime.now(UTC)
        with pytest.raises(TripInvalidReturnDatetimeError):
            TripService._ensure_return_after_departure(now, now - timedelta(days=1))


class TestListTripsPaginationMath:
    async def test_first_page_of_several(self) -> None:
        rows = [_make_trip() for _ in range(2)]
        service, _, _ = _service_with_fakes(rows, total=5)

        result = await service.list_trips(
            tenant_id=uuid.uuid4(), params=TripListParams(page=1, page_size=2)
        )

        assert len(result.data) == 2
        assert result.meta.total_records == 5
        assert result.meta.total_pages == 3
        assert result.meta.current_page == 1
        assert result.meta.has_previous is False
        assert result.meta.has_next is True

    async def test_last_page_has_no_next(self) -> None:
        rows = [_make_trip()]
        service, _, _ = _service_with_fakes(rows, total=5)

        result = await service.list_trips(
            tenant_id=uuid.uuid4(), params=TripListParams(page=3, page_size=2)
        )

        assert result.meta.has_next is False
        assert result.meta.has_previous is True

    async def test_empty_result_gives_zero_pages(self) -> None:
        service, _, _ = _service_with_fakes([], total=0)

        result = await service.list_trips(
            tenant_id=uuid.uuid4(), params=TripListParams(page=1, page_size=20)
        )

        assert result.data == []
        assert result.meta.total_records == 0
        assert result.meta.total_pages == 0
        assert result.meta.has_next is False
        assert result.meta.has_previous is False

    async def test_filters_are_forwarded_to_the_repository(self) -> None:
        service, fake_repo, fake_boat_service = _service_with_fakes([], total=0)
        tenant_id = uuid.uuid4()
        boat_id = uuid.uuid4()

        await service.list_trips(
            tenant_id=tenant_id,
            params=TripListParams(
                boat_id=boat_id,
                status=TripStatus.PLANNED,
                trip_type=TripType.FISHING,
                departure_date_from="2026-08-01",
                departure_date_to="2026-08-31",
                sort="-departure_datetime",
                page=2,
                page_size=10,
            ),
        )

        assert fake_repo.last_search_call is not None
        assert fake_repo.last_search_call["tenant_id"] == tenant_id
        assert fake_repo.last_search_call["boat_id"] == boat_id
        assert fake_repo.last_search_call["status"] == TripStatus.PLANNED
        assert fake_repo.last_search_call["trip_type"] == TripType.FISHING
        assert fake_repo.last_search_call["sort"] == "-departure_datetime"
        assert fake_repo.last_search_call["page"] == 2
        assert fake_repo.last_search_call["page_size"] == 10
        assert fake_repo.last_search_call["q_boat_ids"] is None
        assert fake_boat_service.find_ids_calls == []

    async def test_q_triggers_boat_name_lookup_and_forwards_ids(self) -> None:
        matched_boat_id = uuid.uuid4()
        service, fake_repo, fake_boat_service = _service_with_fakes([], total=0)
        fake_boat_service.find_ids_result = [matched_boat_id]
        tenant_id = uuid.uuid4()

        await service.list_trips(tenant_id=tenant_id, params=TripListParams(q="Alpha"))

        assert fake_boat_service.find_ids_calls == [(tenant_id, "Alpha")]
        assert fake_repo.last_search_call is not None
        assert fake_repo.last_search_call["q_boat_ids"] == [matched_boat_id]

    async def test_blank_q_does_not_trigger_boat_name_lookup(self) -> None:
        service, fake_repo, fake_boat_service = _service_with_fakes([], total=0)

        await service.list_trips(tenant_id=uuid.uuid4(), params=TripListParams(q="   "))

        assert fake_boat_service.find_ids_calls == []
        assert fake_repo.last_search_call is not None
        assert fake_repo.last_search_call["q_boat_ids"] is None
