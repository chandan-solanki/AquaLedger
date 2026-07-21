import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Tenant
from app.modules.boats.models import Boat
from app.modules.companies.models import Company
from app.modules.trips.constants import TripStatus, TripType
from app.modules.trips.models import Trip
from app.modules.trips.repository import TripRepository

_PAST_DATE = date.today() - timedelta(days=30)
_FUTURE_DATE = date.today() + timedelta(days=30)


@pytest.fixture
async def repo(db_session: AsyncSession) -> TripRepository:
    return TripRepository(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - the seeded default tenant may already carry
    trips from manual/exploratory testing, which would silently pollute any
    count-based assertion here."""
    tenant = Tenant(name="Trip Repo Test Tenant", slug=f"trip-repo-test-{uuid.uuid4().hex[:8]}")
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


async def _fresh_boat_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    """A boat on its own, unshared with any other trip - needed whenever a
    test wants two simultaneously PLANNED/DEPARTED trips, since
    ix_trips_boat_single_active (models.py) now forbids that on one boat."""
    company = await _make_company(db_session, tenant_id)
    boat = await _make_boat(db_session, tenant_id, company.id)
    return boat.id


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


async def _make_trip(
    db_session: AsyncSession, tenant_id: uuid.UUID, boat_id: uuid.UUID, **overrides: Any
) -> Trip:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "boat_id": boat_id,
        "trip_number": f"TRIP-{uuid.uuid4().hex[:8]}",
        "trip_type": TripType.FISHING,
        "departure_datetime": datetime(2026, 8, 1, 4, 0, tzinfo=UTC),
        "status": TripStatus.PLANNED,
    }
    defaults.update(overrides)
    trip = Trip(**defaults)
    db_session.add(trip)
    await db_session.commit()
    return trip


class TestGetById:
    async def test_finds_trip_in_own_tenant(
        self,
        repo: TripRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        trip = await _make_trip(db_session, tenant_id, boat_id, trip_number="Findable Trip")
        found = await repo.get_by_id(trip.id, tenant_id)
        assert found is not None
        assert found.trip_number == "Findable Trip"

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: TripRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        trip = await _make_trip(db_session, tenant_id, boat_id)
        assert await repo.get_by_id(trip.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: TripRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id(uuid.uuid4(), tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self,
        repo: TripRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        trip = await _make_trip(db_session, tenant_id, boat_id, deleted_at=datetime.now(UTC))
        assert await repo.get_by_id(trip.id, tenant_id) is None


async def _search(
    repo: TripRepository,
    tenant_id: uuid.UUID,
    *,
    q: str | None = None,
    q_boat_ids: list[uuid.UUID] | None = None,
    boat_id: uuid.UUID | None = None,
    status: TripStatus | None = None,
    trip_type: TripType | None = None,
    departure_date_from: date | None = None,
    departure_date_to: date | None = None,
    return_date_from: date | None = None,
    return_date_to: date | None = None,
    sort: str = "-created_at",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Trip], int]:
    return await repo.search(
        tenant_id,
        q=q,
        q_boat_ids=q_boat_ids,
        boat_id=boat_id,
        status=status,
        trip_type=trip_type,
        departure_date_from=departure_date_from,
        departure_date_to=departure_date_to,
        return_date_from=return_date_from,
        return_date_to=return_date_to,
        sort=sort,
        page=page,
        page_size=page_size,
    )


class TestSearchFilters:
    async def test_filters_by_boat_id(
        self, repo: TripRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        boat_a = await _make_boat(db_session, tenant_id, company.id)
        boat_b = await _make_boat(db_session, tenant_id, company.id)
        target = await _make_trip(db_session, tenant_id, boat_a.id)
        await _make_trip(db_session, tenant_id, boat_b.id)

        rows, total = await _search(repo, tenant_id, boat_id=boat_a.id)
        assert total == 1
        assert rows[0].id == target.id

    async def test_filters_by_status(
        self,
        repo: TripRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        await _make_trip(db_session, tenant_id, boat_id, status=TripStatus.PLANNED)
        cancelled = await _make_trip(db_session, tenant_id, boat_id, status=TripStatus.CANCELLED)

        rows, total = await _search(repo, tenant_id, status=TripStatus.CANCELLED)
        assert total == 1
        assert rows[0].id == cancelled.id

    async def test_filters_by_trip_type(
        self,
        repo: TripRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        await _make_trip(db_session, tenant_id, boat_id, trip_type=TripType.FISHING)
        other_boat_id = await _fresh_boat_id(db_session, tenant_id)
        transport = await _make_trip(
            db_session, tenant_id, other_boat_id, trip_type=TripType.TRANSPORT
        )

        rows, total = await _search(repo, tenant_id, trip_type=TripType.TRANSPORT)
        assert total == 1
        assert rows[0].id == transport.id

    async def test_filters_by_departure_date_range(
        self,
        repo: TripRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        in_range = await _make_trip(
            db_session,
            tenant_id,
            boat_id,
            departure_datetime=datetime.combine(date(2026, 8, 15), time(4, 0), tzinfo=UTC),
        )
        other_boat_id = await _fresh_boat_id(db_session, tenant_id)
        await _make_trip(
            db_session,
            tenant_id,
            other_boat_id,
            departure_datetime=datetime.combine(date(2026, 9, 15), time(4, 0), tzinfo=UTC),
        )

        rows, total = await _search(
            repo,
            tenant_id,
            departure_date_from=date(2026, 8, 1),
            departure_date_to=date(2026, 8, 31),
        )
        assert total == 1
        assert rows[0].id == in_range.id

    async def test_filters_by_return_date_range(
        self,
        repo: TripRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        returned = await _make_trip(
            db_session,
            tenant_id,
            boat_id,
            status=TripStatus.RETURNED,
            actual_return_datetime=datetime.combine(date(2026, 8, 20), time(10, 0), tzinfo=UTC),
        )
        await _make_trip(db_session, tenant_id, boat_id, actual_return_datetime=None)

        rows, total = await _search(
            repo,
            tenant_id,
            return_date_from=date(2026, 8, 1),
            return_date_to=date(2026, 8, 31),
        )
        assert total == 1
        assert rows[0].id == returned.id

    async def test_combines_filters(
        self, repo: TripRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        boat = await _make_boat(db_session, tenant_id, company.id)
        target = await _make_trip(
            db_session, tenant_id, boat.id, trip_type=TripType.FISHING, status=TripStatus.PLANNED
        )
        await _make_trip(
            db_session, tenant_id, boat.id, trip_type=TripType.FISHING, status=TripStatus.CANCELLED
        )
        other_boat_id = await _fresh_boat_id(db_session, tenant_id)
        await _make_trip(
            db_session,
            tenant_id,
            other_boat_id,
            trip_type=TripType.TRANSPORT,
            status=TripStatus.PLANNED,
        )

        rows, total = await _search(
            repo, tenant_id, trip_type=TripType.FISHING, status=TripStatus.PLANNED
        )
        assert total == 1
        assert rows[0].id == target.id

    async def test_excludes_soft_deleted_from_results(
        self,
        repo: TripRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        await _make_trip(db_session, tenant_id, boat_id, deleted_at=datetime.now(UTC))
        rows, total = await _search(repo, tenant_id)
        assert total == 0
        assert rows == []


class TestSearchQuery:
    async def test_matches_trip_number_case_insensitively(
        self,
        repo: TripRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        target = await _make_trip(db_session, tenant_id, boat_id, trip_number="SPECIAL-TRIP-1")
        noise_boat_id = await _fresh_boat_id(db_session, tenant_id)
        await _make_trip(db_session, tenant_id, noise_boat_id)  # noise row that shouldn't match

        rows, total = await _search(repo, tenant_id, q="special-trip")
        assert total == 1
        assert rows[0].id == target.id

    async def test_matches_captain_name_case_insensitively(
        self,
        repo: TripRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        target = await _make_trip(db_session, tenant_id, boat_id, captain_name="Suresh Patil")
        other_boat_id = await _fresh_boat_id(db_session, tenant_id)
        await _make_trip(db_session, tenant_id, other_boat_id, captain_name="Ramesh Yadav")

        rows, total = await _search(repo, tenant_id, q="suresh")
        assert total == 1
        assert rows[0].id == target.id

    async def test_matches_via_pre_resolved_boat_ids(
        self,
        repo: TripRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        """Boat-name search is resolved by the service layer (BoatService),
        not joined here - the repository only accepts the already-matched
        boat ids via `q_boat_ids` (ARCHITECTURE.md §2)."""
        company = await _make_company(db_session, tenant_id)
        other_boat = await _make_boat(db_session, tenant_id, company.id)
        on_target_boat = await _make_trip(
            db_session, tenant_id, boat_id, trip_number="NO-TEXT-MATCH-1"
        )
        await _make_trip(db_session, tenant_id, other_boat.id, trip_number="NO-TEXT-MATCH-2")

        rows, total = await _search(
            repo, tenant_id, q="something not matching text fields", q_boat_ids=[boat_id]
        )
        assert total == 1
        assert rows[0].id == on_target_boat.id

    async def test_blank_query_returns_everything(
        self,
        repo: TripRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        await _make_trip(db_session, tenant_id, boat_id)
        other_boat_id = await _fresh_boat_id(db_session, tenant_id)
        await _make_trip(db_session, tenant_id, other_boat_id)

        rows, total = await _search(repo, tenant_id, q="   ")
        assert total == 2


class TestSearchSorting:
    async def _seed_three(self, db_session: AsyncSession, tenant_id: uuid.UUID) -> None:
        """Each trip gets its own boat - ix_trips_boat_single_active forbids
        three simultaneously PLANNED trips sharing one boat, and these tests
        only care about sort order, not the boat-per-trip business rule."""
        await _make_trip(
            db_session,
            tenant_id,
            await _fresh_boat_id(db_session, tenant_id),
            trip_number="B-TRIP",
            departure_datetime=datetime(2026, 8, 15, 0, 0, tzinfo=UTC),
        )
        await _make_trip(
            db_session,
            tenant_id,
            await _fresh_boat_id(db_session, tenant_id),
            trip_number="A-TRIP",
            departure_datetime=datetime(2026, 8, 1, 0, 0, tzinfo=UTC),
        )
        await _make_trip(
            db_session,
            tenant_id,
            await _fresh_boat_id(db_session, tenant_id),
            trip_number="C-TRIP",
            departure_datetime=datetime(2026, 8, 30, 0, 0, tzinfo=UTC),
        )

    async def test_sort_by_trip_number_ascending(
        self, repo: TripRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await self._seed_three(db_session, tenant_id)
        rows, _ = await _search(repo, tenant_id, sort="trip_number")
        assert [r.trip_number for r in rows] == ["A-TRIP", "B-TRIP", "C-TRIP"]

    async def test_sort_by_departure_datetime_descending(
        self, repo: TripRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await self._seed_three(db_session, tenant_id)
        rows, _ = await _search(repo, tenant_id, sort="-departure_datetime")
        assert [r.trip_number for r in rows] == ["C-TRIP", "B-TRIP", "A-TRIP"]

    async def test_sort_by_created_at_and_updated_at_accepted(
        self, repo: TripRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await self._seed_three(db_session, tenant_id)
        for sort in ("created_at", "-created_at", "updated_at", "-updated_at"):
            rows, total = await _search(repo, tenant_id, sort=sort)
            assert total == 3
            assert len(rows) == 3

    async def test_id_tie_break_follows_the_primary_sort_direction(
        self,
        repo: TripRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        """A tied created_at (two rows inserted in the same instant) must not
        silently override the caller's requested direction - the id
        tie-break has to point the same way as the primary sort."""
        tied_at = datetime.now(UTC)
        older_id_row = await _make_trip(db_session, tenant_id, boat_id, created_at=tied_at)
        other_boat_id = await _fresh_boat_id(db_session, tenant_id)
        newer_id_row = await _make_trip(db_session, tenant_id, other_boat_id, created_at=tied_at)
        assert older_id_row.id < newer_id_row.id  # uuid7 is time-ordered

        desc_rows, _ = await _search(repo, tenant_id, sort="-created_at")
        assert [r.id for r in desc_rows] == [newer_id_row.id, older_id_row.id]

        asc_rows, _ = await _search(repo, tenant_id, sort="created_at")
        assert [r.id for r in asc_rows] == [older_id_row.id, newer_id_row.id]


class TestSearchPagination:
    async def test_page_size_limits_rows_and_total_reflects_full_count(
        self, repo: TripRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        for i in range(5):
            trip_boat_id = await _fresh_boat_id(db_session, tenant_id)
            await _make_trip(db_session, tenant_id, trip_boat_id, trip_number=f"P-{i}")

        rows, total = await _search(repo, tenant_id, sort="trip_number", page=1, page_size=2)
        assert total == 5
        assert len(rows) == 2

    async def test_pages_do_not_overlap_and_cover_all_rows(
        self, repo: TripRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        for i in range(5):
            trip_boat_id = await _fresh_boat_id(db_session, tenant_id)
            await _make_trip(db_session, tenant_id, trip_boat_id, trip_number=f"Q-{i}")

        seen_ids: set[uuid.UUID] = set()
        for page in (1, 2, 3):
            rows, _ = await _search(repo, tenant_id, sort="trip_number", page=page, page_size=2)
            page_ids = {r.id for r in rows}
            assert not (page_ids & seen_ids), "pages overlapped"
            seen_ids |= page_ids
        assert len(seen_ids) == 5

    async def test_page_past_the_end_returns_empty(
        self,
        repo: TripRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        await _make_trip(db_session, tenant_id, boat_id)
        rows, total = await _search(repo, tenant_id, page=99, page_size=10)
        assert total == 1
        assert rows == []


class TestSearchTenantScoping:
    async def test_never_returns_rows_from_another_tenant(
        self,
        repo: TripRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        other_tenant = Tenant(name="Other Trip Tenant", slug=f"other-trip-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_company = await _make_company(db_session, other_tenant.id)
        other_boat = await _make_boat(db_session, other_tenant.id, other_company.id)

        mine = await _make_trip(db_session, tenant_id, boat_id, trip_number="Mine")
        await _make_trip(db_session, other_tenant.id, other_boat.id, trip_number="Not Mine")

        rows, total = await _search(repo, tenant_id)
        assert total == 1
        assert rows[0].id == mine.id


class TestBoatSingleActiveTripConstraint:
    """Exercises ix_trips_boat_single_active (models.py) directly at the
    database layer - the partial unique index that replaced the
    check-then-insert pre-check to close the race window between
    concurrent requests. Inserts go through db_session directly (not the
    repository) since this is a constraint, not a query."""

    async def test_second_planned_trip_on_same_boat_is_rejected(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        await _make_trip(db_session, tenant_id, boat_id, status=TripStatus.PLANNED)
        db_session.add(
            Trip(
                tenant_id=tenant_id,
                boat_id=boat_id,
                trip_number=f"TRIP-{uuid.uuid4().hex[:8]}",
                trip_type=TripType.FISHING,
                departure_datetime=datetime(2026, 8, 1, 4, 0, tzinfo=UTC),
                status=TripStatus.PLANNED,
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_departed_conflicts_with_an_existing_planned_trip(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        """The rule is "at most one of {planned, departed}" per boat, not
        "at most one planned" - the two statuses share the same slot."""
        await _make_trip(db_session, tenant_id, boat_id, status=TripStatus.PLANNED)
        db_session.add(
            Trip(
                tenant_id=tenant_id,
                boat_id=boat_id,
                trip_number=f"TRIP-{uuid.uuid4().hex[:8]}",
                trip_type=TripType.FISHING,
                departure_datetime=datetime(2026, 8, 1, 4, 0, tzinfo=UTC),
                status=TripStatus.DEPARTED,
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    @pytest.mark.parametrize("status", [TripStatus.RETURNED, TripStatus.CANCELLED])
    async def test_terminal_status_trips_do_not_conflict_with_a_new_active_one(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
        status: TripStatus,
    ) -> None:
        await _make_trip(db_session, tenant_id, boat_id, status=status)
        new_trip = await _make_trip(db_session, tenant_id, boat_id, status=TripStatus.PLANNED)
        assert new_trip.id is not None

    async def test_soft_deleted_active_trip_does_not_block_a_new_one(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        await _make_trip(
            db_session,
            tenant_id,
            boat_id,
            status=TripStatus.PLANNED,
            deleted_at=datetime.now(UTC),
        )
        new_trip = await _make_trip(db_session, tenant_id, boat_id, status=TripStatus.PLANNED)
        assert new_trip.id is not None

    async def test_updating_a_trip_to_active_conflicts_with_another_active_trip(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        """Postgres checks the constraint on UPDATE too, not just INSERT -
        this is what makes an explicit exclude-self check unnecessary in
        TripService.update() (the row being updated is compared against
        *other* rows, never against its own prior state)."""
        await _make_trip(db_session, tenant_id, boat_id, status=TripStatus.PLANNED)
        cancelled = await _make_trip(db_session, tenant_id, boat_id, status=TripStatus.CANCELLED)

        cancelled.status = TripStatus.PLANNED
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_transitioning_a_trips_own_status_within_the_active_slot_is_not_a_conflict(
        self,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        boat_id: uuid.UUID,
    ) -> None:
        """A trip moving from planned -> departed on its own boat must not
        be seen as colliding with itself."""
        trip = await _make_trip(db_session, tenant_id, boat_id, status=TripStatus.PLANNED)
        trip.status = TripStatus.DEPARTED
        await db_session.commit()
        assert trip.status == TripStatus.DEPARTED

    async def test_two_active_trips_on_different_boats_do_not_conflict(
        self, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        first_boat_id = await _fresh_boat_id(db_session, tenant_id)
        second_boat_id = await _fresh_boat_id(db_session, tenant_id)
        await _make_trip(db_session, tenant_id, first_boat_id, status=TripStatus.PLANNED)
        second_trip = await _make_trip(
            db_session, tenant_id, second_boat_id, status=TripStatus.PLANNED
        )
        assert second_trip.id is not None
