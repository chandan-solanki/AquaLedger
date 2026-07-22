import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Tenant
from app.modules.boats.models import Boat
from app.modules.companies.models import Company
from app.modules.trip_expenses.constants import ExpenseType
from app.modules.trip_expenses.models import TripExpense
from app.modules.trip_expenses.repository import TripExpenseRepository
from app.modules.trips.constants import TripStatus, TripType
from app.modules.trips.models import Trip

_EXPENSE_DATE = date(2026, 7, 1)


@pytest.fixture
async def repo(db_session: AsyncSession) -> TripExpenseRepository:
    return TripExpenseRepository(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - the seeded default tenant may already carry
    trip expenses from manual/exploratory testing, which would silently
    pollute any count-based assertion here."""
    tenant = Tenant(
        name="Trip Expense Repo Test Tenant",
        slug=f"trip-expense-repo-test-{uuid.uuid4().hex[:8]}",
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
        "status": TripStatus.PLANNED,
    }
    defaults.update(overrides)
    trip = Trip(**defaults)
    db_session.add(trip)
    await db_session.commit()
    return trip


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


async def _make_trip_expense(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    trip_id: uuid.UUID,
    **overrides: Any,
) -> TripExpense:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "trip_id": trip_id,
        "expense_type": ExpenseType.DIESEL,
        "amount": Decimal("500.00"),
        "expense_date": _EXPENSE_DATE,
    }
    defaults.update(overrides)
    trip_expense = TripExpense(**defaults)
    db_session.add(trip_expense)
    await db_session.commit()
    return trip_expense


class TestGetById:
    async def test_finds_trip_expense_in_own_tenant(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        trip_expense = await _make_trip_expense(
            db_session, tenant_id, trip_id, description="Findable"
        )
        found = await repo.get_by_id(trip_expense.id, tenant_id)
        assert found is not None
        assert found.description == "Findable"

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        trip_expense = await _make_trip_expense(db_session, tenant_id, trip_id)
        assert await repo.get_by_id(trip_expense.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: TripExpenseRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id(uuid.uuid4(), tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        trip_expense = await _make_trip_expense(
            db_session, tenant_id, trip_id, deleted_at=datetime.now(UTC)
        )
        assert await repo.get_by_id(trip_expense.id, tenant_id) is None


async def _search(
    repo: TripExpenseRepository,
    tenant_id: uuid.UUID,
    *,
    q: str | None = None,
    trip_id: uuid.UUID | None = None,
    expense_type: ExpenseType | None = None,
    expense_date_from: date | None = None,
    expense_date_to: date | None = None,
    sort: str = "-created_at",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[TripExpense], int]:
    return await repo.search(
        tenant_id,
        q=q,
        trip_id=trip_id,
        expense_type=expense_type,
        expense_date_from=expense_date_from,
        expense_date_to=expense_date_to,
        sort=sort,
        page=page,
        page_size=page_size,
    )


class TestSearchFilters:
    async def test_filters_by_trip_id(
        self, repo: TripExpenseRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        trip_a = await _fresh_trip_id(db_session, tenant_id)
        trip_b = await _fresh_trip_id(db_session, tenant_id)
        target = await _make_trip_expense(db_session, tenant_id, trip_a)
        await _make_trip_expense(db_session, tenant_id, trip_b)

        rows, total = await _search(repo, tenant_id, trip_id=trip_a)
        assert total == 1
        assert rows[0].id == target.id

    async def test_filters_by_expense_type(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        await _make_trip_expense(db_session, tenant_id, trip_id, expense_type=ExpenseType.ICE)
        harbour = await _make_trip_expense(
            db_session, tenant_id, trip_id, expense_type=ExpenseType.HARBOUR
        )

        rows, total = await _search(repo, tenant_id, expense_type=ExpenseType.HARBOUR)
        assert total == 1
        assert rows[0].id == harbour.id

    async def test_filters_by_expense_date_range(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        in_range = await _make_trip_expense(
            db_session, tenant_id, trip_id, expense_date=date(2026, 7, 15)
        )
        await _make_trip_expense(db_session, tenant_id, trip_id, expense_date=date(2026, 9, 15))

        rows, total = await _search(
            repo,
            tenant_id,
            expense_date_from=date(2026, 7, 1),
            expense_date_to=date(2026, 7, 31),
        )
        assert total == 1
        assert rows[0].id == in_range.id

    async def test_combines_filters(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        target = await _make_trip_expense(
            db_session, tenant_id, trip_id, expense_type=ExpenseType.ICE
        )
        await _make_trip_expense(db_session, tenant_id, trip_id, expense_type=ExpenseType.FOOD)
        other_trip = await _fresh_trip_id(db_session, tenant_id)
        await _make_trip_expense(
            db_session, tenant_id, other_trip, expense_type=ExpenseType.ICE
        )

        rows, total = await _search(
            repo, tenant_id, trip_id=trip_id, expense_type=ExpenseType.ICE
        )
        assert total == 1
        assert rows[0].id == target.id

    async def test_excludes_soft_deleted_from_results(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        await _make_trip_expense(db_session, tenant_id, trip_id, deleted_at=datetime.now(UTC))
        rows, total = await _search(repo, tenant_id)
        assert total == 0
        assert rows == []


class TestSearchQuery:
    async def test_matches_vendor_name_case_insensitively(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        target = await _make_trip_expense(
            db_session, tenant_id, trip_id, vendor_name="Sassoon Dock Fuel Co"
        )
        await _make_trip_expense(db_session, tenant_id, trip_id, vendor_name="Irrelevant Vendor")

        rows, total = await _search(repo, tenant_id, q="sassoon dock")
        assert total == 1
        assert rows[0].id == target.id

    async def test_matches_receipt_number_case_insensitively(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        target = await _make_trip_expense(
            db_session, tenant_id, trip_id, receipt_number="RCPT-1042"
        )
        await _make_trip_expense(db_session, tenant_id, trip_id, receipt_number="RCPT-9999")

        rows, total = await _search(repo, tenant_id, q="rcpt-1042")
        assert total == 1
        assert rows[0].id == target.id

    async def test_no_match_returns_empty(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        await _make_trip_expense(db_session, tenant_id, trip_id, vendor_name="Some Vendor")

        rows, total = await _search(repo, tenant_id, q="no-such-vendor-or-receipt")
        assert total == 0
        assert rows == []

    async def test_blank_query_returns_everything(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        await _make_trip_expense(db_session, tenant_id, trip_id)
        await _make_trip_expense(db_session, tenant_id, trip_id)

        rows, total = await _search(repo, tenant_id, q="   ")
        assert total == 2


class TestSearchSorting:
    async def _seed_three(
        self, db_session: AsyncSession, tenant_id: uuid.UUID, trip_id: uuid.UUID
    ) -> None:
        await _make_trip_expense(
            db_session,
            tenant_id,
            trip_id,
            expense_date=date(2026, 7, 15),
            amount=Decimal("50.00"),
        )
        await _make_trip_expense(
            db_session,
            tenant_id,
            trip_id,
            expense_date=date(2026, 7, 1),
            amount=Decimal("10.00"),
        )
        await _make_trip_expense(
            db_session,
            tenant_id,
            trip_id,
            expense_date=date(2026, 7, 30),
            amount=Decimal("90.00"),
        )

    async def test_sort_by_expense_date_ascending(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, trip_id)
        rows, _ = await _search(repo, tenant_id, sort="expense_date")
        assert [r.expense_date for r in rows] == [
            date(2026, 7, 1),
            date(2026, 7, 15),
            date(2026, 7, 30),
        ]

    async def test_sort_by_amount_descending(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, trip_id)
        rows, _ = await _search(repo, tenant_id, sort="-amount")
        assert [r.amount for r in rows] == [
            Decimal("90.00"),
            Decimal("50.00"),
            Decimal("10.00"),
        ]

    async def test_sort_by_created_at_accepted(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, trip_id)
        for sort in ("created_at", "-created_at"):
            rows, total = await _search(repo, tenant_id, sort=sort)
            assert total == 3
            assert len(rows) == 3

    async def test_id_tie_break_follows_the_primary_sort_direction(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        """A tied created_at (two rows inserted in the same instant) must not
        silently override the caller's requested direction - the id
        tie-break has to point the same way as the primary sort."""
        tied_at = datetime.now(UTC)
        older_id_row = await _make_trip_expense(
            db_session, tenant_id, trip_id, created_at=tied_at
        )
        newer_id_row = await _make_trip_expense(
            db_session, tenant_id, trip_id, created_at=tied_at
        )
        assert older_id_row.id < newer_id_row.id  # uuid7 is time-ordered

        desc_rows, _ = await _search(repo, tenant_id, sort="-created_at")
        assert [r.id for r in desc_rows] == [newer_id_row.id, older_id_row.id]

        asc_rows, _ = await _search(repo, tenant_id, sort="created_at")
        assert [r.id for r in asc_rows] == [older_id_row.id, newer_id_row.id]


class TestSearchPagination:
    async def test_page_size_limits_rows_and_total_reflects_full_count(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        for i in range(5):
            await _make_trip_expense(
                db_session, tenant_id, trip_id, expense_date=_EXPENSE_DATE + timedelta(days=i)
            )

        rows, total = await _search(repo, tenant_id, sort="expense_date", page=1, page_size=2)
        assert total == 5
        assert len(rows) == 2

    async def test_pages_do_not_overlap_and_cover_all_rows(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        for i in range(5):
            await _make_trip_expense(
                db_session, tenant_id, trip_id, expense_date=_EXPENSE_DATE + timedelta(days=i)
            )

        seen_ids: set[uuid.UUID] = set()
        for page in (1, 2, 3):
            rows, _ = await _search(repo, tenant_id, sort="expense_date", page=page, page_size=2)
            page_ids = {r.id for r in rows}
            assert not (page_ids & seen_ids), "pages overlapped"
            seen_ids |= page_ids
        assert len(seen_ids) == 5

    async def test_page_past_the_end_returns_empty(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        await _make_trip_expense(db_session, tenant_id, trip_id)
        rows, total = await _search(repo, tenant_id, page=99, page_size=10)
        assert total == 1
        assert rows == []


class TestSearchTenantScoping:
    async def test_never_returns_rows_from_another_tenant(
        self,
        repo: TripExpenseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        other_tenant = Tenant(
            name="Other Trip Expense Tenant", slug=f"other-trip-expense-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_company = await _make_company(db_session, other_tenant.id)
        other_boat = await _make_boat(db_session, other_tenant.id, other_company.id)
        other_trip = await _make_trip(db_session, other_tenant.id, other_boat.id)

        mine = await _make_trip_expense(db_session, tenant_id, trip_id)
        await _make_trip_expense(db_session, other_tenant.id, other_trip.id)

        rows, total = await _search(repo, tenant_id)
        assert total == 1
        assert rows[0].id == mine.id
