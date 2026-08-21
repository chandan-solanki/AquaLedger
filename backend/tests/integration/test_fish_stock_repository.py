import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Tenant
from app.modules.boats.models import Boat
from app.modules.fish.models import Fish
from app.modules.trip_catches.models import TripCatch
from app.modules.trip_catches.repository import TripCatchRepository
from app.modules.trips.constants import TripStatus, TripType
from app.modules.trips.models import Trip

_LANDING_DATE = date(2026, 7, 1)


@pytest.fixture
async def repo(db_session: AsyncSession) -> TripCatchRepository:
    return TripCatchRepository(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - the seeded default tenant may already carry
    trip catches from manual/exploratory testing, which would silently
    pollute any sum-based assertion here."""
    tenant = Tenant(
        name="Fish Stock Repo Test Tenant", slug=f"fish-stock-repo-test-{uuid.uuid4().hex[:8]}"
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant.id


async def _make_boat(db_session: AsyncSession, tenant_id: uuid.UUID, **overrides: Any) -> Boat:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "code": f"B-{uuid.uuid4().hex[:8]}",
        "name": f"Boat {uuid.uuid4().hex[:8]}",
        "registration_number": f"REG-{uuid.uuid4().hex[:8]}",
    }
    defaults.update(overrides)
    boat = Boat(**defaults)
    db_session.add(boat)
    await db_session.commit()
    return boat


async def _make_trip(
    db_session: AsyncSession, tenant_id: uuid.UUID, boat_id: uuid.UUID, **overrides: Any
) -> Trip:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "boat_id": boat_id,
        "trip_number": f"TRIP-{uuid.uuid4().hex[:8]}",
        "trip_type": TripType.FISHING,
        "departure_datetime": datetime(2026, 6, 1, 4, 0, tzinfo=UTC),
        "status": TripStatus.RETURNED,
    }
    defaults.update(overrides)
    trip = Trip(**defaults)
    db_session.add(trip)
    await db_session.commit()
    return trip


async def _make_fish(db_session: AsyncSession, tenant_id: uuid.UUID, **overrides: Any) -> Fish:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "code": f"FISH-{uuid.uuid4().hex[:8]}",
        "name": f"Fish {uuid.uuid4().hex[:8]}",
    }
    defaults.update(overrides)
    fish = Fish(**defaults)
    db_session.add(fish)
    await db_session.commit()
    return fish


async def _fresh_trip_id(
    db_session: AsyncSession, tenant_id: uuid.UUID, **overrides: Any
) -> uuid.UUID:
    boat = await _make_boat(db_session, tenant_id)
    trip = await _make_trip(db_session, tenant_id, boat.id, **overrides)
    return trip.id


@pytest.fixture
async def boat_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    boat = await _make_boat(db_session, tenant_id)
    return boat.id


@pytest.fixture
async def trip_id(db_session: AsyncSession, tenant_id: uuid.UUID, boat_id: uuid.UUID) -> uuid.UUID:
    trip = await _make_trip(db_session, tenant_id, boat_id)
    return trip.id


@pytest.fixture
async def fish_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    fish = await _make_fish(db_session, tenant_id)
    return fish.id


async def _make_trip_catch(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    trip_id: uuid.UUID,
    fish_id: uuid.UUID,
    **overrides: Any,
) -> TripCatch:
    # available_quantity defaults to whatever keeps the quantity invariant
    # satisfied given quantity_caught/sold_quantity/waste_quantity - so a
    # caller can override just quantity_caught without also having to work
    # out a matching available_quantity by hand.
    quantity_caught = overrides.get("quantity_caught", Decimal("100.000"))
    sold_quantity = overrides.get("sold_quantity", Decimal("0.000"))
    waste_quantity = overrides.get("waste_quantity", Decimal("0.000"))
    available_quantity = overrides.get(
        "available_quantity", quantity_caught - sold_quantity - waste_quantity
    )
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "trip_id": trip_id,
        "fish_id": fish_id,
        "quantity_caught": quantity_caught,
        "available_quantity": available_quantity,
        "sold_quantity": sold_quantity,
        "waste_quantity": waste_quantity,
        "landing_date": _LANDING_DATE,
    }
    defaults.update(overrides)
    trip_catch = TripCatch(**defaults)
    db_session.add(trip_catch)
    await db_session.commit()
    return trip_catch


class TestAggregateStockByFish:
    async def test_empty_tenant_returns_nothing(
        self, repo: TripCatchRepository, tenant_id: uuid.UUID
    ) -> None:
        rows = await repo.aggregate_stock_by_fish(tenant_id)
        assert rows == []

    async def test_single_catch_sums_correctly(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        await _make_trip_catch(
            db_session,
            tenant_id,
            trip_id,
            fish_id,
            quantity_caught=Decimal("100.000"),
            available_quantity=Decimal("70.000"),
            sold_quantity=Decimal("30.000"),
            waste_quantity=Decimal("0.000"),
        )

        rows = await repo.aggregate_stock_by_fish(tenant_id)

        assert len(rows) == 1
        row = rows[0]
        assert row.fish_id == fish_id
        assert row.total_caught == Decimal("100.000")
        assert row.total_sold == Decimal("30.000")
        assert row.total_available == Decimal("70.000")
        assert row.total_waste == Decimal("0.000")

    async def test_multiple_catches_for_the_same_fish_are_summed(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        trip_a = await _fresh_trip_id(db_session, tenant_id)
        trip_b = await _fresh_trip_id(db_session, tenant_id)
        await _make_trip_catch(
            db_session,
            tenant_id,
            trip_a,
            fish_id,
            quantity_caught=Decimal("100.000"),
            available_quantity=Decimal("70.000"),
            sold_quantity=Decimal("30.000"),
            waste_quantity=Decimal("0.000"),
        )
        await _make_trip_catch(
            db_session,
            tenant_id,
            trip_b,
            fish_id,
            quantity_caught=Decimal("50.000"),
            available_quantity=Decimal("40.000"),
            sold_quantity=Decimal("5.000"),
            waste_quantity=Decimal("5.000"),
        )

        rows = await repo.aggregate_stock_by_fish(tenant_id)

        assert len(rows) == 1
        row = rows[0]
        assert row.total_caught == Decimal("150.000")
        assert row.total_sold == Decimal("35.000")
        assert row.total_available == Decimal("110.000")
        assert row.total_waste == Decimal("5.000")

    async def test_invariant_holds_over_the_aggregate(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        trip_a = await _fresh_trip_id(db_session, tenant_id)
        trip_b = await _fresh_trip_id(db_session, tenant_id)
        await _make_trip_catch(
            db_session,
            tenant_id,
            trip_a,
            fish_id,
            quantity_caught=Decimal("100.000"),
            available_quantity=Decimal("60.000"),
            sold_quantity=Decimal("30.000"),
            waste_quantity=Decimal("10.000"),
        )
        await _make_trip_catch(
            db_session,
            tenant_id,
            trip_b,
            fish_id,
            quantity_caught=Decimal("50.000"),
            available_quantity=Decimal("50.000"),
            sold_quantity=Decimal("0.000"),
            waste_quantity=Decimal("0.000"),
        )

        rows = await repo.aggregate_stock_by_fish(tenant_id)
        row = rows[0]
        assert row.total_available + row.total_sold + row.total_waste == row.total_caught

    async def test_multiple_fish_aggregate_independently(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        fish_a = await _make_fish(db_session, tenant_id)
        fish_b = await _make_fish(db_session, tenant_id)
        await _make_trip_catch(
            db_session, tenant_id, trip_id, fish_a.id, quantity_caught=Decimal("10.000")
        )
        await _make_trip_catch(
            db_session, tenant_id, trip_id, fish_b.id, quantity_caught=Decimal("20.000")
        )

        rows = await repo.aggregate_stock_by_fish(tenant_id)

        totals_by_fish = {row.fish_id: row.total_caught for row in rows}
        assert totals_by_fish[fish_a.id] == Decimal("10.000")
        assert totals_by_fish[fish_b.id] == Decimal("20.000")

    async def test_soft_deleted_catches_are_excluded(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        await _make_trip_catch(
            db_session,
            tenant_id,
            trip_id,
            fish_id,
            quantity_caught=Decimal("100.000"),
            deleted_at=datetime.now(UTC),
        )

        rows = await repo.aggregate_stock_by_fish(tenant_id)

        assert rows == []

    async def test_soft_deleted_catch_does_not_pollute_a_live_sibling(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        trip_a = await _fresh_trip_id(db_session, tenant_id)
        trip_b = await _fresh_trip_id(db_session, tenant_id)
        await _make_trip_catch(
            db_session,
            tenant_id,
            trip_a,
            fish_id,
            quantity_caught=Decimal("100.000"),
            deleted_at=datetime.now(UTC),
        )
        await _make_trip_catch(
            db_session, tenant_id, trip_b, fish_id, quantity_caught=Decimal("40.000")
        )

        rows = await repo.aggregate_stock_by_fish(tenant_id)

        assert len(rows) == 1
        assert rows[0].total_caught == Decimal("40.000")

    async def test_tenant_isolation(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        await _make_trip_catch(db_session, tenant_id, trip_id, fish_id)

        other_tenant = Tenant(
            name="Other Fish Stock Tenant", slug=f"other-fish-stock-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_boat = await _make_boat(db_session, other_tenant.id)
        other_trip = await _make_trip(db_session, other_tenant.id, other_boat.id)
        other_fish = await _make_fish(db_session, other_tenant.id)
        await _make_trip_catch(db_session, other_tenant.id, other_trip.id, other_fish.id)

        rows = await repo.aggregate_stock_by_fish(tenant_id)

        assert len(rows) == 1
        assert rows[0].fish_id == fish_id

    async def test_decimal_precision_is_preserved(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        await _make_trip_catch(
            db_session,
            tenant_id,
            trip_id,
            fish_id,
            quantity_caught=Decimal("120.505"),
            available_quantity=Decimal("80.380"),
            sold_quantity=Decimal("40.125"),
            waste_quantity=Decimal("0.000"),
        )

        rows = await repo.aggregate_stock_by_fish(tenant_id)

        assert rows[0].total_caught == Decimal("120.505")
        assert rows[0].total_available == Decimal("80.380")
        assert rows[0].total_sold == Decimal("40.125")


class TestGetByFishId:
    async def test_returns_only_that_fish_and_tenants_catches(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        fish_a = await _make_fish(db_session, tenant_id)
        fish_b = await _make_fish(db_session, tenant_id)
        target = await _make_trip_catch(db_session, tenant_id, trip_id, fish_a.id)
        await _make_trip_catch(db_session, tenant_id, trip_id, fish_b.id)

        rows = await repo.get_by_fish_id(tenant_id, fish_a.id)

        assert [row.id for row in rows] == [target.id]

    async def test_excludes_soft_deleted_rows(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        await _make_trip_catch(
            db_session, tenant_id, trip_id, fish_id, deleted_at=datetime.now(UTC)
        )

        rows = await repo.get_by_fish_id(tenant_id, fish_id)

        assert rows == []

    async def test_excludes_other_tenants_rows(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        await _make_trip_catch(db_session, tenant_id, trip_id, fish_id)

        rows = await repo.get_by_fish_id(uuid.uuid4(), fish_id)

        assert rows == []

    async def test_returns_no_rows_for_a_fish_with_no_catches(
        self, repo: TripCatchRepository, tenant_id: uuid.UUID
    ) -> None:
        rows = await repo.get_by_fish_id(tenant_id, uuid.uuid4())
        assert rows == []
