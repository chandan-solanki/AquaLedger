import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.core.errors import ConflictError
from app.modules.fish.exceptions import FishNotFoundError
from app.modules.trip_catches.exceptions import (
    TripCatchFishNotFoundError,
    TripCatchInsufficientQuantityError,
    TripCatchNotFoundError,
    TripCatchQuantityInvariantError,
    TripCatchTripNotFoundError,
    TripCatchTripNotReturnedError,
)
from app.modules.trip_catches.models import TripCatch
from app.modules.trip_catches.schemas import TripCatchListParams
from app.modules.trip_catches.service import TripCatchService
from app.modules.trips.constants import TripStatus
from app.modules.trips.exceptions import TripNotFoundError


class _FakeConstraintCause(Exception):
    """`__cause__` must be a BaseException, so this stands in for the part of
    asyncpg's CheckViolationError that _translate_integrity_error reads."""

    def __init__(self, constraint_name: str) -> None:
        super().__init__("fake constraint violation")
        self.constraint_name = constraint_name


class _FakeDriverError(Exception):
    """Stands in for asyncpg's CheckViolationError, chained as __cause__."""

    def __init__(self, constraint_name: str) -> None:
        super().__init__("new row violates check constraint")
        self.__cause__ = _FakeConstraintCause(constraint_name)


class _FakeIntegrityError(Exception):
    """Stands in for sqlalchemy.exc.IntegrityError - only `.orig` is read."""

    def __init__(self, constraint_name: str) -> None:
        super().__init__("integrity error")
        self.orig = _FakeDriverError(constraint_name)


class _FakeTripCatchRepo:
    def __init__(self, rows: list[TripCatch] | None = None, total: int = 0) -> None:
        self.rows = rows or []
        self.total = total
        self.last_search_call: dict[str, Any] | None = None
        self.locked_row: TripCatch | None = None
        self.get_for_update_calls: list[tuple[uuid.UUID, uuid.UUID]] = []

    async def search(self, tenant_id: uuid.UUID, **kwargs: Any) -> tuple[list[TripCatch], int]:
        self.last_search_call = {"tenant_id": tenant_id, **kwargs}
        return self.rows, self.total

    async def get_by_id_for_update(
        self, trip_catch_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> TripCatch | None:
        self.get_for_update_calls.append((trip_catch_id, tenant_id))
        return self.locked_row


class _TripStub:
    """Stands in for a TripResponse - only .status is read by TripCatchService."""

    def __init__(self, *, status: TripStatus = TripStatus.RETURNED) -> None:
        self.id = uuid.uuid4()
        self.status = status


class _FakeTripService:
    """Stands in for TripService.get/find_ids_by_trip_number - the two entry
    points TripCatchService calls (ARCHITECTURE.md §2 - cross-module access
    goes through the other module's service, never its repository)."""

    def __init__(self, *, trip: _TripStub | None = None, raises: bool = False) -> None:
        self.trip = trip
        self.raises = raises
        self.get_calls: list[tuple[uuid.UUID, uuid.UUID]] = []
        self.find_ids_calls: list[tuple[uuid.UUID, str]] = []
        self.find_ids_result: list[uuid.UUID] = []

    async def get(self, trip_id: uuid.UUID, *, tenant_id: uuid.UUID) -> _TripStub:
        self.get_calls.append((trip_id, tenant_id))
        if self.raises:
            raise TripNotFoundError("Trip not found")
        assert self.trip is not None
        return self.trip

    async def find_ids_by_trip_number(self, tenant_id: uuid.UUID, q: str) -> list[uuid.UUID]:
        self.find_ids_calls.append((tenant_id, q))
        return self.find_ids_result


class _FishStub:
    def __init__(self) -> None:
        self.id = uuid.uuid4()


class _FakeFishService:
    """Stands in for FishService.get/find_ids_by_name."""

    def __init__(self, *, fish: _FishStub | None = None, raises: bool = False) -> None:
        self.fish = fish
        self.raises = raises
        self.get_calls: list[tuple[uuid.UUID, uuid.UUID]] = []
        self.find_ids_calls: list[tuple[uuid.UUID, str]] = []
        self.find_ids_result: list[uuid.UUID] = []

    async def get(self, fish_id: uuid.UUID, *, tenant_id: uuid.UUID) -> _FishStub:
        self.get_calls.append((fish_id, tenant_id))
        if self.raises:
            raise FishNotFoundError("Fish not found")
        assert self.fish is not None
        return self.fish

    async def find_ids_by_name(self, tenant_id: uuid.UUID, q: str) -> list[uuid.UUID]:
        self.find_ids_calls.append((tenant_id, q))
        return self.find_ids_result


def _make_trip_catch(**overrides: Any) -> TripCatch:
    """A TripCatch that satisfies TripCatchResponse validation without
    touching the DB - the non-nullable columns normally filled by
    server_default / TimestampMixin need explicit values since this object
    is never flushed."""
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "trip_id": uuid.uuid4(),
        "fish_id": uuid.uuid4(),
        "quantity_caught": Decimal("100.000"),
        "available_quantity": Decimal("100.000"),
        "sold_quantity": Decimal("0.000"),
        "waste_quantity": Decimal("0.000"),
        "landing_date": date(2026, 7, 22),
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return TripCatch(**defaults)


def _service_with_fakes(
    rows: list[TripCatch] | None = None,
    total: int = 0,
    *,
    trip: _TripStub | None = None,
    trip_raises: bool = False,
    fish: _FishStub | None = None,
    fish_raises: bool = False,
) -> tuple[TripCatchService, _FakeTripCatchRepo, _FakeTripService, _FakeFishService]:
    service = TripCatchService.__new__(TripCatchService)
    fake_repo = _FakeTripCatchRepo(rows, total)
    fake_trip_service = _FakeTripService(trip=trip, raises=trip_raises)
    fake_fish_service = _FakeFishService(fish=fish, raises=fish_raises)
    service._repo = fake_repo  # type: ignore[assignment]
    service._trip_service = fake_trip_service  # type: ignore[assignment]
    service._fish_service = fake_fish_service  # type: ignore[assignment]
    return service, fake_repo, fake_trip_service, fake_fish_service


class TestTranslateIntegrityError:
    """The DB-level backstop for the quantity invariant
    (ck_trip_catches_quantity_invariant, models.py) - _commit_or_raise
    routes here when the CHECK constraint fires, which the FOR UPDATE lock
    in update() should make unreachable in normal operation, but a bug or
    a future direct-write code path must still surface a clean 422 rather
    than a raw 500."""

    def test_quantity_invariant_constraint_maps_to_quantity_invariant_error(self) -> None:
        exc = _FakeIntegrityError("ck_trip_catches_quantity_invariant")
        result = TripCatchService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert isinstance(result, TripCatchQuantityInvariantError)

    def test_unknown_constraint_falls_back_to_generic_conflict(self) -> None:
        exc = _FakeIntegrityError("some_other_constraint")
        result = TripCatchService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert type(result) is ConflictError

    def test_missing_orig_falls_back_to_generic_conflict(self) -> None:
        class _BareError(Exception):
            orig = None

        result = TripCatchService._translate_integrity_error(_BareError())  # type: ignore[arg-type]
        assert type(result) is ConflictError


class TestEnsureTripReturned:
    async def test_passes_through_when_trip_returned(self) -> None:
        trip = _TripStub(status=TripStatus.RETURNED)
        service, _, _, _ = _service_with_fakes(trip=trip)

        await service._ensure_trip_returned(trip.id, uuid.uuid4())

    async def test_raises_not_found_when_trip_missing(self) -> None:
        service, _, _, _ = _service_with_fakes(trip_raises=True)

        with pytest.raises(TripCatchTripNotFoundError):
            await service._ensure_trip_returned(uuid.uuid4(), uuid.uuid4())

    @pytest.mark.parametrize(
        "status", [TripStatus.PLANNED, TripStatus.DEPARTED, TripStatus.CANCELLED]
    )
    async def test_raises_not_returned_for_non_returned_statuses(self, status: TripStatus) -> None:
        trip = _TripStub(status=status)
        service, _, _, _ = _service_with_fakes(trip=trip)

        with pytest.raises(TripCatchTripNotReturnedError):
            await service._ensure_trip_returned(trip.id, uuid.uuid4())

    async def test_tenant_scoping_is_forwarded_to_trip_service(self) -> None:
        trip = _TripStub(status=TripStatus.RETURNED)
        service, _, fake_trip_service, _ = _service_with_fakes(trip=trip)
        tenant_id = uuid.uuid4()

        await service._ensure_trip_returned(trip.id, tenant_id)

        assert fake_trip_service.get_calls == [(trip.id, tenant_id)]


class TestEnsureFishExists:
    async def test_passes_through_when_fish_exists(self) -> None:
        fish = _FishStub()
        service, _, _, fake_fish_service = _service_with_fakes(fish=fish)
        tenant_id = uuid.uuid4()

        await service._ensure_fish_exists(fish.id, tenant_id)

        assert fake_fish_service.get_calls == [(fish.id, tenant_id)]

    async def test_raises_not_found_when_fish_missing(self) -> None:
        service, _, _, _ = _service_with_fakes(fish_raises=True)

        with pytest.raises(TripCatchFishNotFoundError):
            await service._ensure_fish_exists(uuid.uuid4(), uuid.uuid4())


class TestEnsureQuantityInvariant:
    def test_holds_when_sum_equals_quantity_caught(self) -> None:
        TripCatchService._ensure_quantity_invariant(
            quantity_caught=Decimal("100"),
            available_quantity=Decimal("60"),
            sold_quantity=Decimal("40"),
            waste_quantity=Decimal("0"),
        )

    def test_raises_when_sum_is_less_than_quantity_caught(self) -> None:
        with pytest.raises(TripCatchQuantityInvariantError):
            TripCatchService._ensure_quantity_invariant(
                quantity_caught=Decimal("100"),
                available_quantity=Decimal("50"),
                sold_quantity=Decimal("40"),
                waste_quantity=Decimal("0"),
            )

    def test_raises_when_sum_exceeds_quantity_caught(self) -> None:
        with pytest.raises(TripCatchQuantityInvariantError):
            TripCatchService._ensure_quantity_invariant(
                quantity_caught=Decimal("100"),
                available_quantity=Decimal("60"),
                sold_quantity=Decimal("40"),
                waste_quantity=Decimal("10"),
            )

    def test_holds_with_all_zero_available_when_fully_sold(self) -> None:
        TripCatchService._ensure_quantity_invariant(
            quantity_caught=Decimal("100"),
            available_quantity=Decimal("0"),
            sold_quantity=Decimal("90"),
            waste_quantity=Decimal("10"),
        )


class TestListCatchesPaginationMath:
    async def test_first_page_of_several(self) -> None:
        rows = [_make_trip_catch() for _ in range(2)]
        service, _, _, _ = _service_with_fakes(rows, total=5)

        result = await service.list_catches(
            tenant_id=uuid.uuid4(), params=TripCatchListParams(page=1, page_size=2)
        )

        assert len(result.data) == 2
        assert result.meta.total_records == 5
        assert result.meta.total_pages == 3
        assert result.meta.current_page == 1
        assert result.meta.has_previous is False
        assert result.meta.has_next is True

    async def test_last_page_has_no_next(self) -> None:
        rows = [_make_trip_catch()]
        service, _, _, _ = _service_with_fakes(rows, total=5)

        result = await service.list_catches(
            tenant_id=uuid.uuid4(), params=TripCatchListParams(page=3, page_size=2)
        )

        assert result.meta.has_next is False
        assert result.meta.has_previous is True

    async def test_empty_result_gives_zero_pages(self) -> None:
        service, _, _, _ = _service_with_fakes([], total=0)

        result = await service.list_catches(
            tenant_id=uuid.uuid4(), params=TripCatchListParams(page=1, page_size=20)
        )

        assert result.data == []
        assert result.meta.total_records == 0
        assert result.meta.total_pages == 0
        assert result.meta.has_next is False
        assert result.meta.has_previous is False

    async def test_filters_are_forwarded_to_the_repository(self) -> None:
        service, fake_repo, _, _ = _service_with_fakes([], total=0)
        tenant_id = uuid.uuid4()
        trip_id = uuid.uuid4()
        fish_id = uuid.uuid4()

        await service.list_catches(
            tenant_id=tenant_id,
            params=TripCatchListParams(
                trip_id=trip_id,
                fish_id=fish_id,
                grade="A",
                landing_date_from="2026-07-01",
                landing_date_to="2026-07-31",
                sort="-quantity_caught",
                page=2,
                page_size=10,
            ),
        )

        assert fake_repo.last_search_call is not None
        assert fake_repo.last_search_call["tenant_id"] == tenant_id
        assert fake_repo.last_search_call["trip_id"] == trip_id
        assert fake_repo.last_search_call["fish_id"] == fish_id
        assert fake_repo.last_search_call["grade"] == "A"
        assert fake_repo.last_search_call["sort"] == "-quantity_caught"
        assert fake_repo.last_search_call["page"] == 2
        assert fake_repo.last_search_call["page_size"] == 10
        assert fake_repo.last_search_call["q_trip_ids"] is None
        assert fake_repo.last_search_call["q_fish_ids"] is None

    async def test_q_triggers_trip_and_fish_lookup_and_forwards_ids(self) -> None:
        matched_trip_id = uuid.uuid4()
        matched_fish_id = uuid.uuid4()
        service, fake_repo, fake_trip_service, fake_fish_service = _service_with_fakes([], total=0)
        fake_trip_service.find_ids_result = [matched_trip_id]
        fake_fish_service.find_ids_result = [matched_fish_id]
        tenant_id = uuid.uuid4()

        await service.list_catches(tenant_id=tenant_id, params=TripCatchListParams(q="Alpha"))

        assert fake_trip_service.find_ids_calls == [(tenant_id, "Alpha")]
        assert fake_fish_service.find_ids_calls == [(tenant_id, "Alpha")]
        assert fake_repo.last_search_call is not None
        assert fake_repo.last_search_call["q_trip_ids"] == [matched_trip_id]
        assert fake_repo.last_search_call["q_fish_ids"] == [matched_fish_id]

    async def test_blank_q_does_not_trigger_lookups(self) -> None:
        service, fake_repo, fake_trip_service, fake_fish_service = _service_with_fakes([], total=0)

        await service.list_catches(tenant_id=uuid.uuid4(), params=TripCatchListParams(q="   "))

        assert fake_trip_service.find_ids_calls == []
        assert fake_fish_service.find_ids_calls == []
        assert fake_repo.last_search_call is not None
        assert fake_repo.last_search_call["q_trip_ids"] is None
        assert fake_repo.last_search_call["q_fish_ids"] is None


class TestDeductAvailableQuantity:
    """TripCatchService.deduct_available_quantity - the inventory-deduction
    half of Sprint 9 Session 5's invoice issue workflow."""

    async def test_deducts_from_available_and_credits_sold(self) -> None:
        trip_catch = _make_trip_catch(
            available_quantity=Decimal("100.000"), sold_quantity=Decimal("0.000")
        )
        service, fake_repo, _, _ = _service_with_fakes()
        fake_repo.locked_row = trip_catch
        actor_id = uuid.uuid4()

        result = await service.deduct_available_quantity(
            trip_catch.id, Decimal("30.000"), tenant_id=trip_catch.tenant_id, actor_id=actor_id
        )

        assert trip_catch.available_quantity == Decimal("70.000")
        assert trip_catch.sold_quantity == Decimal("30.000")
        assert trip_catch.updated_by == actor_id
        assert result.available_quantity == Decimal("70.000")

    async def test_deducting_exactly_the_available_quantity_is_allowed(self) -> None:
        trip_catch = _make_trip_catch(available_quantity=Decimal("50.000"))
        service, fake_repo, _, _ = _service_with_fakes()
        fake_repo.locked_row = trip_catch

        await service.deduct_available_quantity(
            trip_catch.id, Decimal("50.000"), tenant_id=trip_catch.tenant_id, actor_id=uuid.uuid4()
        )

        assert trip_catch.available_quantity == Decimal("0.000")

    async def test_raises_insufficient_quantity_when_over_the_limit(self) -> None:
        trip_catch = _make_trip_catch(available_quantity=Decimal("10.000"))
        service, fake_repo, _, _ = _service_with_fakes()
        fake_repo.locked_row = trip_catch

        with pytest.raises(TripCatchInsufficientQuantityError):
            await service.deduct_available_quantity(
                trip_catch.id,
                Decimal("10.001"),
                tenant_id=trip_catch.tenant_id,
                actor_id=uuid.uuid4(),
            )
        # Never left partially mutated on rejection.
        assert trip_catch.available_quantity == Decimal("10.000")
        assert trip_catch.sold_quantity == Decimal("0.000")

    async def test_raises_not_found_when_trip_catch_missing(self) -> None:
        service, fake_repo, _, _ = _service_with_fakes()
        fake_repo.locked_row = None

        with pytest.raises(TripCatchNotFoundError):
            await service.deduct_available_quantity(
                uuid.uuid4(), Decimal("1.000"), tenant_id=uuid.uuid4(), actor_id=uuid.uuid4()
            )

    async def test_lookup_is_scoped_to_tenant_via_for_update_lock(self) -> None:
        trip_catch = _make_trip_catch()
        service, fake_repo, _, _ = _service_with_fakes()
        fake_repo.locked_row = trip_catch
        tenant_id = uuid.uuid4()

        await service.deduct_available_quantity(
            trip_catch.id, Decimal("1.000"), tenant_id=tenant_id, actor_id=uuid.uuid4()
        )

        assert fake_repo.get_for_update_calls == [(trip_catch.id, tenant_id)]


def test_make_trip_catch_helper_produces_a_response_compatible_row() -> None:
    """Sanity check on the test helper itself - grade/landing_port/remarks
    are optional and shouldn't be required to build a valid row."""
    trip_catch = _make_trip_catch(grade=None, landing_port=None, remarks=None)
    assert trip_catch.grade is None
    assert trip_catch.landing_port is None
    assert trip_catch.remarks is None
