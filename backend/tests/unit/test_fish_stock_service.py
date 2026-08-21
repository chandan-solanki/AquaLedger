import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.common.schemas import PaginatedResponse
from app.modules.fish.exceptions import FishNotFoundError
from app.modules.trip_catches.exceptions import FishStockFishNotFoundError
from app.modules.trip_catches.models import TripCatch
from app.modules.trip_catches.schemas import FishStockDetail, FishStockListParams, FishStockRow
from app.modules.trip_catches.service import TripCatchService


@dataclass
class _AggregateRow:
    """Stands in for the Row TripCatchRepository.aggregate_stock_by_fish
    returns - attribute access only, same shape the service reads."""

    fish_id: uuid.UUID
    total_caught: Decimal
    total_sold: Decimal
    total_available: Decimal
    total_waste: Decimal


class _FishStub:
    """Stands in for a FishResponse - only the fields the service reads."""

    def __init__(self, **overrides: Any) -> None:
        self.id: uuid.UUID = overrides.get("id", uuid.uuid4())
        self.name: str = overrides.get("name", "Pomfret")
        self.code: str = overrides.get("code", "FISH-001")
        self.unit: str = overrides.get("unit", "kg")
        self.is_active: bool = overrides.get("is_active", True)


class _TripStub:
    """Stands in for a TripResponse - only the fields the service reads."""

    def __init__(self, **overrides: Any) -> None:
        self.id: uuid.UUID = overrides.get("id", uuid.uuid4())
        self.trip_number: str = overrides.get("trip_number", "TRIP-0001")


class _FakeTripCatchRepo:
    def __init__(
        self,
        aggregates: list[_AggregateRow] | None = None,
        catches: list[TripCatch] | None = None,
    ) -> None:
        self.aggregates = aggregates or []
        self.catches = catches or []
        self.aggregate_calls: list[uuid.UUID] = []
        self.get_by_fish_id_calls: list[tuple[uuid.UUID, uuid.UUID]] = []

    async def aggregate_stock_by_fish(self, tenant_id: uuid.UUID) -> list[_AggregateRow]:
        self.aggregate_calls.append(tenant_id)
        return self.aggregates

    async def get_by_fish_id(self, tenant_id: uuid.UUID, fish_id: uuid.UUID) -> list[TripCatch]:
        self.get_by_fish_id_calls.append((tenant_id, fish_id))
        return self.catches


class _FakeFishService:
    """Stands in for FishService.get/get_many_by_ids - the two entry points
    the Fish Stock methods call (ARCHITECTURE.md §2 - cross-module access
    goes through the other module's service, never its repository)."""

    def __init__(
        self,
        fish_list: list[_FishStub] | None = None,
        *,
        get_result: _FishStub | None = None,
        get_raises: bool = False,
    ) -> None:
        self.fish_list = fish_list or []
        self.get_result = get_result
        self.get_raises = get_raises
        self.get_many_calls: list[tuple[list[uuid.UUID], uuid.UUID]] = []
        self.get_calls: list[tuple[uuid.UUID, uuid.UUID]] = []

    async def get_many_by_ids(
        self, fish_ids: list[uuid.UUID], *, tenant_id: uuid.UUID
    ) -> list[_FishStub]:
        self.get_many_calls.append((fish_ids, tenant_id))
        return [fish for fish in self.fish_list if fish.id in fish_ids]

    async def get(self, fish_id: uuid.UUID, *, tenant_id: uuid.UUID) -> _FishStub:
        self.get_calls.append((fish_id, tenant_id))
        if self.get_raises:
            raise FishNotFoundError("Fish not found")
        assert self.get_result is not None
        return self.get_result


class _FakeTripService:
    def __init__(self, trips: list[_TripStub] | None = None) -> None:
        self.trips = trips or []
        self.get_many_calls: list[tuple[list[uuid.UUID], uuid.UUID]] = []

    async def get_many_by_ids(
        self, trip_ids: list[uuid.UUID], *, tenant_id: uuid.UUID
    ) -> list[_TripStub]:
        self.get_many_calls.append((trip_ids, tenant_id))
        return [trip for trip in self.trips if trip.id in trip_ids]


def _make_trip_catch(**overrides: Any) -> TripCatch:
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "trip_id": uuid.uuid4(),
        "fish_id": uuid.uuid4(),
        "quantity_caught": Decimal("100.000"),
        "available_quantity": Decimal("70.000"),
        "sold_quantity": Decimal("30.000"),
        "waste_quantity": Decimal("0.000"),
        "landing_date": date(2026, 7, 1),
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return TripCatch(**defaults)


def _service_with_fakes(
    *,
    aggregates: list[_AggregateRow] | None = None,
    catches: list[TripCatch] | None = None,
    fish_list: list[_FishStub] | None = None,
    fish_get_result: _FishStub | None = None,
    fish_get_raises: bool = False,
    trips: list[_TripStub] | None = None,
) -> tuple[TripCatchService, _FakeTripCatchRepo, _FakeFishService, _FakeTripService]:
    service = TripCatchService.__new__(TripCatchService)
    fake_repo = _FakeTripCatchRepo(aggregates, catches)
    fake_fish_service = _FakeFishService(
        fish_list, get_result=fish_get_result, get_raises=fish_get_raises
    )
    fake_trip_service = _FakeTripService(trips)
    service._repo = fake_repo  # type: ignore[assignment]
    service._fish_service = fake_fish_service  # type: ignore[assignment]
    service._trip_service = fake_trip_service  # type: ignore[assignment]
    return service, fake_repo, fake_fish_service, fake_trip_service


class TestGetFishStockListEmpty:
    async def test_no_trip_catches_returns_empty_page(self) -> None:
        service, _, _, _ = _service_with_fakes(aggregates=[])

        result = await service.get_fish_stock_list(
            tenant_id=uuid.uuid4(), params=FishStockListParams()
        )

        assert result.data == []
        assert result.meta.total_records == 0
        assert result.meta.total_pages == 0
        assert result.meta.has_next is False
        assert result.meta.has_previous is False


class TestGetFishStockListAggregation:
    async def test_single_fish_row_maps_through(self) -> None:
        fish = _FishStub(name="Pomfret")
        aggregate = _AggregateRow(
            fish_id=fish.id,
            total_caught=Decimal("180.000"),
            total_sold=Decimal("60.000"),
            total_available=Decimal("120.000"),
            total_waste=Decimal("0.000"),
        )
        service, _, _, _ = _service_with_fakes(aggregates=[aggregate], fish_list=[fish])

        result = await service.get_fish_stock_list(
            tenant_id=uuid.uuid4(), params=FishStockListParams()
        )

        assert len(result.data) == 1
        row = result.data[0]
        assert row.fish_id == fish.id
        assert row.fish_name == "Pomfret"
        assert row.total_caught == Decimal("180.000")
        assert row.total_sold == Decimal("60.000")
        assert row.total_available == Decimal("120.000")
        assert row.total_waste == Decimal("0.000")

    async def test_preserves_decimal_precision(self) -> None:
        """Values must pass through as Decimal, never float - a float
        round-trip (e.g. 100.005 -> float -> Decimal) can silently corrupt
        the last digit."""
        fish = _FishStub()
        aggregate = _AggregateRow(
            fish_id=fish.id,
            total_caught=Decimal("120.505"),
            total_sold=Decimal("40.125"),
            total_available=Decimal("80.380"),
            total_waste=Decimal("0.000"),
        )
        service, _, _, _ = _service_with_fakes(aggregates=[aggregate], fish_list=[fish])

        result = await service.get_fish_stock_list(
            tenant_id=uuid.uuid4(), params=FishStockListParams()
        )

        row = result.data[0]
        assert isinstance(row.total_caught, Decimal)
        assert row.total_caught == Decimal("120.505")
        assert row.total_available == Decimal("80.380")

    async def test_fish_that_cannot_be_resolved_is_dropped(self) -> None:
        """A fish_id present in the aggregation but missing from
        FishService.get_many_by_ids (soft-deleted, or otherwise gone) must
        never surface as normal stock."""
        aggregate = _AggregateRow(
            fish_id=uuid.uuid4(),
            total_caught=Decimal("10"),
            total_sold=Decimal("0"),
            total_available=Decimal("10"),
            total_waste=Decimal("0"),
        )
        service, _, _, _ = _service_with_fakes(aggregates=[aggregate], fish_list=[])

        result = await service.get_fish_stock_list(
            tenant_id=uuid.uuid4(), params=FishStockListParams()
        )

        assert result.data == []
        assert result.meta.total_records == 0

    async def test_multiple_fish_are_sorted_by_name(self) -> None:
        fish_a = _FishStub(name="Tuna")
        fish_b = _FishStub(name="Mackerel")
        aggregates = [
            _AggregateRow(fish_a.id, Decimal("10"), Decimal("0"), Decimal("10"), Decimal("0")),
            _AggregateRow(fish_b.id, Decimal("20"), Decimal("0"), Decimal("20"), Decimal("0")),
        ]
        service, _, _, _ = _service_with_fakes(aggregates=aggregates, fish_list=[fish_a, fish_b])

        result = await service.get_fish_stock_list(
            tenant_id=uuid.uuid4(), params=FishStockListParams()
        )

        assert [row.fish_name for row in result.data] == ["Mackerel", "Tuna"]


class TestGetFishStockListFilters:
    async def test_q_filters_by_fish_name(self) -> None:
        matching = _FishStub(name="Pomfret", code="F-1")
        other = _FishStub(name="Tuna", code="F-2")
        aggregates = [
            _AggregateRow(matching.id, Decimal("1"), Decimal("0"), Decimal("1"), Decimal("0")),
            _AggregateRow(other.id, Decimal("1"), Decimal("0"), Decimal("1"), Decimal("0")),
        ]
        service, _, _, _ = _service_with_fakes(aggregates=aggregates, fish_list=[matching, other])

        result = await service.get_fish_stock_list(
            tenant_id=uuid.uuid4(), params=FishStockListParams(q="pomfret")
        )

        assert [row.fish_id for row in result.data] == [matching.id]

    async def test_q_filters_by_fish_code(self) -> None:
        matching = _FishStub(name="Species A", code="SPECIAL-1")
        other = _FishStub(name="Species B", code="OTHER-2")
        aggregates = [
            _AggregateRow(matching.id, Decimal("1"), Decimal("0"), Decimal("1"), Decimal("0")),
            _AggregateRow(other.id, Decimal("1"), Decimal("0"), Decimal("1"), Decimal("0")),
        ]
        service, _, _, _ = _service_with_fakes(aggregates=aggregates, fish_list=[matching, other])

        result = await service.get_fish_stock_list(
            tenant_id=uuid.uuid4(), params=FishStockListParams(q="special")
        )

        assert [row.fish_id for row in result.data] == [matching.id]

    async def test_is_active_filters_out_inactive_fish(self) -> None:
        active = _FishStub(is_active=True)
        inactive = _FishStub(is_active=False)
        aggregates = [
            _AggregateRow(active.id, Decimal("1"), Decimal("0"), Decimal("1"), Decimal("0")),
            _AggregateRow(inactive.id, Decimal("1"), Decimal("0"), Decimal("1"), Decimal("0")),
        ]
        service, _, _, _ = _service_with_fakes(aggregates=aggregates, fish_list=[active, inactive])

        result = await service.get_fish_stock_list(
            tenant_id=uuid.uuid4(), params=FishStockListParams(is_active=True)
        )

        assert [row.fish_id for row in result.data] == [active.id]


class TestGetFishStockListPagination:
    async def test_pagination_meta_is_correct(self) -> None:
        fish_rows = [_FishStub(name=f"Fish {i}") for i in range(3)]
        aggregates = [
            _AggregateRow(fish.id, Decimal("1"), Decimal("0"), Decimal("1"), Decimal("0"))
            for fish in fish_rows
        ]
        service, _, _, _ = _service_with_fakes(aggregates=aggregates, fish_list=fish_rows)

        result = await service.get_fish_stock_list(
            tenant_id=uuid.uuid4(), params=FishStockListParams(page=1, page_size=2)
        )

        assert len(result.data) == 2
        assert result.meta.total_records == 3
        assert result.meta.total_pages == 2
        assert result.meta.has_next is True
        assert result.meta.has_previous is False


class TestGetFishStockListTenantScoping:
    async def test_tenant_id_is_forwarded_to_repo_and_fish_service(self) -> None:
        tenant_id = uuid.uuid4()
        fish = _FishStub()
        aggregate = _AggregateRow(fish.id, Decimal("1"), Decimal("0"), Decimal("1"), Decimal("0"))
        service, fake_repo, fake_fish_service, _ = _service_with_fakes(
            aggregates=[aggregate], fish_list=[fish]
        )

        await service.get_fish_stock_list(tenant_id=tenant_id, params=FishStockListParams())

        assert fake_repo.aggregate_calls == [tenant_id]
        assert fake_fish_service.get_many_calls == [([fish.id], tenant_id)]


class TestGetFishStockDetail:
    async def test_raises_when_fish_missing(self) -> None:
        service, _, _, _ = _service_with_fakes(fish_get_raises=True)

        with pytest.raises(FishStockFishNotFoundError):
            await service.get_fish_stock_detail(uuid.uuid4(), tenant_id=uuid.uuid4())

    async def test_returns_totals_and_contributing_catches(self) -> None:
        fish = _FishStub(name="Pomfret")
        trip = _TripStub(trip_number="TRIP-2026-0001")
        catch_a = _make_trip_catch(
            fish_id=fish.id,
            trip_id=trip.id,
            quantity_caught=Decimal("100.000"),
            available_quantity=Decimal("70.000"),
            sold_quantity=Decimal("30.000"),
            waste_quantity=Decimal("0.000"),
            landing_date=date(2026, 7, 1),
        )
        catch_b = _make_trip_catch(
            fish_id=fish.id,
            trip_id=trip.id,
            quantity_caught=Decimal("50.000"),
            available_quantity=Decimal("50.000"),
            sold_quantity=Decimal("0.000"),
            waste_quantity=Decimal("0.000"),
            landing_date=date(2026, 7, 2),
        )
        service, _, _, _ = _service_with_fakes(
            catches=[catch_a, catch_b], fish_get_result=fish, trips=[trip]
        )

        detail: FishStockDetail = await service.get_fish_stock_detail(
            fish.id, tenant_id=uuid.uuid4()
        )

        assert detail.fish_id == fish.id
        assert detail.fish_name == "Pomfret"
        assert detail.total_caught == Decimal("150.000")
        assert detail.total_sold == Decimal("30.000")
        assert detail.total_available == Decimal("120.000")
        assert detail.total_waste == Decimal("0.000")
        assert len(detail.catches) == 2
        assert {c.trip_catch_id for c in detail.catches} == {catch_a.id, catch_b.id}
        assert all(c.trip_number == "TRIP-2026-0001" for c in detail.catches)

    async def test_invariant_holds_over_the_response(self) -> None:
        fish = _FishStub()
        catch = _make_trip_catch(
            fish_id=fish.id,
            quantity_caught=Decimal("100.000"),
            available_quantity=Decimal("60.000"),
            sold_quantity=Decimal("30.000"),
            waste_quantity=Decimal("10.000"),
        )
        service, _, _, _ = _service_with_fakes(catches=[catch], fish_get_result=fish, trips=[])

        detail = await service.get_fish_stock_detail(fish.id, tenant_id=uuid.uuid4())

        assert detail.total_available + detail.total_sold + detail.total_waste == (
            detail.total_caught
        )

    async def test_empty_catches_returns_zero_totals(self) -> None:
        fish = _FishStub()
        service, _, _, _ = _service_with_fakes(catches=[], fish_get_result=fish, trips=[])

        detail = await service.get_fish_stock_detail(fish.id, tenant_id=uuid.uuid4())

        assert detail.total_caught == Decimal("0")
        assert detail.total_sold == Decimal("0")
        assert detail.total_available == Decimal("0")
        assert detail.total_waste == Decimal("0")
        assert detail.catches == []


class TestPaginatedResponseType:
    async def test_get_fish_stock_list_returns_fish_stock_rows(self) -> None:
        fish = _FishStub()
        aggregate = _AggregateRow(fish.id, Decimal("1"), Decimal("0"), Decimal("1"), Decimal("0"))
        service, _, _, _ = _service_with_fakes(aggregates=[aggregate], fish_list=[fish])

        result: PaginatedResponse[FishStockRow] = await service.get_fish_stock_list(
            tenant_id=uuid.uuid4(), params=FishStockListParams()
        )

        assert hasattr(result, "data") and hasattr(result, "meta")
        assert all(isinstance(row, FishStockRow) for row in result.data)
