import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Tenant
from app.modules.boats.models import Boat
from app.modules.companies.models import Company
from app.modules.fish.models import Fish
from app.modules.trip_catches.constants import CatchGrade
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
    pollute any count-based assertion here."""
    tenant = Tenant(
        name="Trip Catch Repo Test Tenant", slug=f"trip-catch-repo-test-{uuid.uuid4().hex[:8]}"
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant.id


async def _make_company(
    db_session: AsyncSession, tenant_id: uuid.UUID, **overrides: Any
) -> Company:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "code": f"CO-{uuid.uuid4().hex[:8]}",
        "name": f"Company {uuid.uuid4().hex[:8]}",
        "company_type": "customer",
    }
    defaults.update(overrides)
    company = Company(**defaults)
    db_session.add(company)
    await db_session.commit()
    return company


async def _make_boat(
    db_session: AsyncSession, tenant_id: uuid.UUID, company_id: uuid.UUID, **overrides: Any
) -> Boat:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "company_id": company_id,
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
    """A trip on its own boat/company, for tests that need multiple distinct
    trips without caring about boat-sharing rules."""
    company = await _make_company(db_session, tenant_id)
    boat = await _make_boat(db_session, tenant_id, company.id)
    trip = await _make_trip(db_session, tenant_id, boat.id, **overrides)
    return trip.id


@pytest.fixture
async def company_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    company = await _make_company(db_session, tenant_id)
    return company.id


@pytest.fixture
async def boat_id(
    db_session: AsyncSession, tenant_id: uuid.UUID, company_id: uuid.UUID
) -> uuid.UUID:
    boat = await _make_boat(db_session, tenant_id, company_id)
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
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "trip_id": trip_id,
        "fish_id": fish_id,
        "quantity_caught": Decimal("100.000"),
        "available_quantity": Decimal("100.000"),
        "sold_quantity": Decimal("0.000"),
        "waste_quantity": Decimal("0.000"),
        "landing_date": _LANDING_DATE,
    }
    defaults.update(overrides)
    trip_catch = TripCatch(**defaults)
    db_session.add(trip_catch)
    await db_session.commit()
    return trip_catch


class TestGetById:
    async def test_finds_trip_catch_in_own_tenant(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        trip_catch = await _make_trip_catch(
            db_session, tenant_id, trip_id, fish_id, remarks="Findable"
        )
        found = await repo.get_by_id(trip_catch.id, tenant_id)
        assert found is not None
        assert found.remarks == "Findable"

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        trip_catch = await _make_trip_catch(db_session, tenant_id, trip_id, fish_id)
        assert await repo.get_by_id(trip_catch.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: TripCatchRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id(uuid.uuid4(), tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        trip_catch = await _make_trip_catch(
            db_session, tenant_id, trip_id, fish_id, deleted_at=datetime.now(UTC)
        )
        assert await repo.get_by_id(trip_catch.id, tenant_id) is None


class TestGetByIdForUpdate:
    """Same read semantics as get_by_id, but through the SELECT ... FOR
    UPDATE path TripCatchService.update() uses to close the concurrent
    lost-update race on the quantity invariant. A true two-transaction
    blocking test isn't possible in this suite - db_session wraps every
    test in one rolled-back transaction, so a second, independent
    connection would never see the row at all (it's uncommitted). What's
    verifiable here is that the locked lookup is otherwise identical to the
    unlocked one."""

    async def test_finds_trip_catch_in_own_tenant(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        trip_catch = await _make_trip_catch(
            db_session, tenant_id, trip_id, fish_id, remarks="Lockable"
        )
        found = await repo.get_by_id_for_update(trip_catch.id, tenant_id)
        assert found is not None
        assert found.remarks == "Lockable"

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        trip_catch = await _make_trip_catch(db_session, tenant_id, trip_id, fish_id)
        assert await repo.get_by_id_for_update(trip_catch.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: TripCatchRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id_for_update(uuid.uuid4(), tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        trip_catch = await _make_trip_catch(
            db_session, tenant_id, trip_id, fish_id, deleted_at=datetime.now(UTC)
        )
        assert await repo.get_by_id_for_update(trip_catch.id, tenant_id) is None


class TestQuantityInvariantConstraint:
    """Exercises ck_trip_catches_quantity_invariant (models.py) directly at
    the database layer - the CHECK constraint that backstops the invariant
    regardless of what wrote the row, the same way
    TestBoatSingleActiveTripConstraint (test_trip_repository.py) exercises
    ix_trips_boat_single_active. Inserts/updates go through db_session
    directly (not the repository or service), since this is a constraint,
    not a query, and the service's own _ensure_quantity_invariant check
    would otherwise never let an invalid combination reach the database."""

    async def test_mismatched_quantities_on_insert_is_rejected(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        db_session.add(
            TripCatch(
                tenant_id=tenant_id,
                trip_id=trip_id,
                fish_id=fish_id,
                quantity_caught=Decimal("100.000"),
                available_quantity=Decimal("50.000"),
                sold_quantity=Decimal("0.000"),
                waste_quantity=Decimal("0.000"),
                landing_date=_LANDING_DATE,
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_mismatched_quantities_on_update_is_rejected(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        trip_catch = await _make_trip_catch(db_session, tenant_id, trip_id, fish_id)
        trip_catch.sold_quantity = Decimal("999.000")
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_matching_quantities_are_accepted(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        trip_catch = await _make_trip_catch(
            db_session,
            tenant_id,
            trip_id,
            fish_id,
            quantity_caught=Decimal("100.000"),
            available_quantity=Decimal("60.000"),
            sold_quantity=Decimal("30.000"),
            waste_quantity=Decimal("10.000"),
        )
        assert trip_catch.id is not None


async def _search(
    repo: TripCatchRepository,
    tenant_id: uuid.UUID,
    *,
    q: str | None = None,
    q_trip_ids: list[uuid.UUID] | None = None,
    q_fish_ids: list[uuid.UUID] | None = None,
    trip_id: uuid.UUID | None = None,
    fish_id: uuid.UUID | None = None,
    grade: CatchGrade | None = None,
    landing_date_from: date | None = None,
    landing_date_to: date | None = None,
    sort: str = "-created_at",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[TripCatch], int]:
    return await repo.search(
        tenant_id,
        q=q,
        q_trip_ids=q_trip_ids,
        q_fish_ids=q_fish_ids,
        trip_id=trip_id,
        fish_id=fish_id,
        grade=grade,
        landing_date_from=landing_date_from,
        landing_date_to=landing_date_to,
        sort=sort,
        page=page,
        page_size=page_size,
    )


class TestSearchFilters:
    async def test_filters_by_trip_id(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        trip_a = await _fresh_trip_id(db_session, tenant_id)
        trip_b = await _fresh_trip_id(db_session, tenant_id)
        target = await _make_trip_catch(db_session, tenant_id, trip_a, fish_id)
        await _make_trip_catch(db_session, tenant_id, trip_b, fish_id)

        rows, total = await _search(repo, tenant_id, trip_id=trip_a)
        assert total == 1
        assert rows[0].id == target.id

    async def test_filters_by_fish_id(
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

        rows, total = await _search(repo, tenant_id, fish_id=fish_a.id)
        assert total == 1
        assert rows[0].id == target.id

    async def test_filters_by_grade(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        await _make_trip_catch(db_session, tenant_id, trip_id, fish_id, grade=CatchGrade.A)
        graded_b = await _make_trip_catch(
            db_session, tenant_id, trip_id, fish_id, grade=CatchGrade.B
        )

        rows, total = await _search(repo, tenant_id, grade=CatchGrade.B)
        assert total == 1
        assert rows[0].id == graded_b.id

    async def test_filters_by_landing_date_range(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        in_range = await _make_trip_catch(
            db_session, tenant_id, trip_id, fish_id, landing_date=date(2026, 7, 15)
        )
        await _make_trip_catch(
            db_session, tenant_id, trip_id, fish_id, landing_date=date(2026, 9, 15)
        )

        rows, total = await _search(
            repo,
            tenant_id,
            landing_date_from=date(2026, 7, 1),
            landing_date_to=date(2026, 7, 31),
        )
        assert total == 1
        assert rows[0].id == in_range.id

    async def test_combines_filters(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        target = await _make_trip_catch(db_session, tenant_id, trip_id, fish_id, grade=CatchGrade.A)
        await _make_trip_catch(db_session, tenant_id, trip_id, fish_id, grade=CatchGrade.C)
        other_trip = await _fresh_trip_id(db_session, tenant_id)
        await _make_trip_catch(db_session, tenant_id, other_trip, fish_id, grade=CatchGrade.A)

        rows, total = await _search(repo, tenant_id, trip_id=trip_id, grade=CatchGrade.A)
        assert total == 1
        assert rows[0].id == target.id

    async def test_excludes_soft_deleted_from_results(
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
        rows, total = await _search(repo, tenant_id)
        assert total == 0
        assert rows == []


class TestSearchQuery:
    async def test_matches_via_pre_resolved_trip_ids(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        """Trip-number search is resolved by the service layer (TripService),
        not joined here - the repository only accepts the already-matched
        trip ids via `q_trip_ids` (ARCHITECTURE.md §2)."""
        other_trip = await _fresh_trip_id(db_session, tenant_id)
        on_target_trip = await _make_trip_catch(db_session, tenant_id, trip_id, fish_id)
        await _make_trip_catch(db_session, tenant_id, other_trip, fish_id)

        rows, total = await _search(
            repo, tenant_id, q="something not matching", q_trip_ids=[trip_id]
        )
        assert total == 1
        assert rows[0].id == on_target_trip.id

    async def test_matches_via_pre_resolved_fish_ids(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        fish_a = await _make_fish(db_session, tenant_id)
        fish_b = await _make_fish(db_session, tenant_id)
        on_target_fish = await _make_trip_catch(db_session, tenant_id, trip_id, fish_a.id)
        await _make_trip_catch(db_session, tenant_id, trip_id, fish_b.id)

        rows, total = await _search(
            repo, tenant_id, q="something not matching", q_fish_ids=[fish_a.id]
        )
        assert total == 1
        assert rows[0].id == on_target_fish.id

    async def test_q_set_with_no_matching_ids_returns_nothing(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        """Unlike trips (which can fall back to its own ilike columns),
        trip_catches has no text column of its own - if the service resolved
        zero matching trip/fish ids, the search must return nothing rather
        than silently matching every row."""
        await _make_trip_catch(db_session, tenant_id, trip_id, fish_id)

        rows, total = await _search(
            repo, tenant_id, q="no-such-trip-or-fish", q_trip_ids=[], q_fish_ids=[]
        )
        assert total == 0
        assert rows == []

    async def test_blank_query_returns_everything(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        await _make_trip_catch(db_session, tenant_id, trip_id, fish_id)
        other_trip = await _fresh_trip_id(db_session, tenant_id)
        await _make_trip_catch(db_session, tenant_id, other_trip, fish_id)

        rows, total = await _search(repo, tenant_id, q="   ")
        assert total == 2


class TestSearchSorting:
    async def _seed_three(
        self, db_session: AsyncSession, tenant_id: uuid.UUID, trip_id: uuid.UUID, fish_id: uuid.UUID
    ) -> None:
        await _make_trip_catch(
            db_session,
            tenant_id,
            trip_id,
            fish_id,
            landing_date=date(2026, 7, 15),
            quantity_caught=Decimal("50.000"),
            available_quantity=Decimal("50.000"),
        )
        await _make_trip_catch(
            db_session,
            tenant_id,
            trip_id,
            fish_id,
            landing_date=date(2026, 7, 1),
            quantity_caught=Decimal("10.000"),
            available_quantity=Decimal("10.000"),
        )
        await _make_trip_catch(
            db_session,
            tenant_id,
            trip_id,
            fish_id,
            landing_date=date(2026, 7, 30),
            quantity_caught=Decimal("90.000"),
            available_quantity=Decimal("90.000"),
        )

    async def test_sort_by_landing_date_ascending(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, trip_id, fish_id)
        rows, _ = await _search(repo, tenant_id, sort="landing_date")
        assert [r.landing_date for r in rows] == [
            date(2026, 7, 1),
            date(2026, 7, 15),
            date(2026, 7, 30),
        ]

    async def test_sort_by_quantity_caught_descending(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, trip_id, fish_id)
        rows, _ = await _search(repo, tenant_id, sort="-quantity_caught")
        assert [r.quantity_caught for r in rows] == [
            Decimal("90.000"),
            Decimal("50.000"),
            Decimal("10.000"),
        ]

    async def test_sort_by_created_at_accepted(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, trip_id, fish_id)
        for sort in ("created_at", "-created_at"):
            rows, total = await _search(repo, tenant_id, sort=sort)
            assert total == 3
            assert len(rows) == 3

    async def test_id_tie_break_follows_the_primary_sort_direction(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        """A tied created_at (two rows inserted in the same instant) must not
        silently override the caller's requested direction - the id
        tie-break has to point the same way as the primary sort."""
        tied_at = datetime.now(UTC)
        older_id_row = await _make_trip_catch(
            db_session, tenant_id, trip_id, fish_id, created_at=tied_at
        )
        newer_id_row = await _make_trip_catch(
            db_session, tenant_id, trip_id, fish_id, created_at=tied_at
        )
        assert older_id_row.id < newer_id_row.id  # uuid7 is time-ordered

        desc_rows, _ = await _search(repo, tenant_id, sort="-created_at")
        assert [r.id for r in desc_rows] == [newer_id_row.id, older_id_row.id]

        asc_rows, _ = await _search(repo, tenant_id, sort="created_at")
        assert [r.id for r in asc_rows] == [older_id_row.id, newer_id_row.id]


class TestSearchPagination:
    async def test_page_size_limits_rows_and_total_reflects_full_count(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        for i in range(5):
            await _make_trip_catch(
                db_session,
                tenant_id,
                trip_id,
                fish_id,
                landing_date=_LANDING_DATE + timedelta(days=i),
            )

        rows, total = await _search(repo, tenant_id, sort="landing_date", page=1, page_size=2)
        assert total == 5
        assert len(rows) == 2

    async def test_pages_do_not_overlap_and_cover_all_rows(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        for i in range(5):
            await _make_trip_catch(
                db_session,
                tenant_id,
                trip_id,
                fish_id,
                landing_date=_LANDING_DATE + timedelta(days=i),
            )

        seen_ids: set[uuid.UUID] = set()
        for page in (1, 2, 3):
            rows, _ = await _search(repo, tenant_id, sort="landing_date", page=page, page_size=2)
            page_ids = {r.id for r in rows}
            assert not (page_ids & seen_ids), "pages overlapped"
            seen_ids |= page_ids
        assert len(seen_ids) == 5

    async def test_page_past_the_end_returns_empty(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        await _make_trip_catch(db_session, tenant_id, trip_id, fish_id)
        rows, total = await _search(repo, tenant_id, page=99, page_size=10)
        assert total == 1
        assert rows == []


class TestSearchTenantScoping:
    async def test_never_returns_rows_from_another_tenant(
        self,
        repo: TripCatchRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        other_tenant = Tenant(
            name="Other Trip Catch Tenant", slug=f"other-trip-catch-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_company = await _make_company(db_session, other_tenant.id)
        other_boat = await _make_boat(db_session, other_tenant.id, other_company.id)
        other_trip = await _make_trip(db_session, other_tenant.id, other_boat.id)
        other_fish = await _make_fish(db_session, other_tenant.id)

        mine = await _make_trip_catch(db_session, tenant_id, trip_id, fish_id)
        await _make_trip_catch(db_session, other_tenant.id, other_trip.id, other_fish.id)

        rows, total = await _search(repo, tenant_id)
        assert total == 1
        assert rows[0].id == mine.id
