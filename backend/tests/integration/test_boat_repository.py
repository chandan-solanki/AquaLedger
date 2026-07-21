import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Tenant
from app.modules.boats.models import Boat
from app.modules.boats.repository import BoatRepository
from app.modules.companies.models import Company

_PAST = date.today() - timedelta(days=30)
_FUTURE = date.today() + timedelta(days=30)


@pytest.fixture
async def repo(db_session: AsyncSession) -> BoatRepository:
    return BoatRepository(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - the seeded default tenant may already carry
    boats from manual/exploratory testing, which would silently pollute any
    count-based assertion here."""
    tenant = Tenant(name="Boat Repo Test Tenant", slug=f"boat-repo-test-{uuid.uuid4().hex[:8]}")
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


@pytest.fixture
async def company_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    company = await _make_company(db_session, tenant_id)
    return company.id


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


class TestGetById:
    async def test_finds_boat_in_own_tenant(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        boat = await _make_boat(db_session, tenant_id, company_id, name="Findable Boat")
        found = await repo.get_by_id(boat.id, tenant_id)
        assert found is not None
        assert found.name == "Findable Boat"

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        boat = await _make_boat(db_session, tenant_id, company_id)
        assert await repo.get_by_id(boat.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: BoatRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id(uuid.uuid4(), tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        boat = await _make_boat(
            db_session, tenant_id, company_id, deleted_at=datetime.now(UTC)
        )
        assert await repo.get_by_id(boat.id, tenant_id) is None


async def _search(
    repo: BoatRepository,
    tenant_id: uuid.UUID,
    *,
    q: str | None = None,
    boat_type: str | None = None,
    company_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    insurance_expired: bool | None = None,
    license_expired: bool | None = None,
    sort: str = "-created_at",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Boat], int]:
    return await repo.search(
        tenant_id,
        q=q,
        boat_type=boat_type,
        company_id=company_id,
        is_active=is_active,
        insurance_expired=insurance_expired,
        license_expired=license_expired,
        sort=sort,
        page=page,
        page_size=page_size,
    )


class TestSearchFilters:
    async def test_filters_by_boat_type_case_insensitively(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        trawler = await _make_boat(db_session, tenant_id, company_id, boat_type="Trawler")
        await _make_boat(db_session, tenant_id, company_id, boat_type="Gillnetter")

        rows, total = await _search(repo, tenant_id, boat_type="trawler")
        assert total == 1
        assert rows[0].id == trawler.id

    async def test_filters_by_company_id(
        self, repo: BoatRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company_a = await _make_company(db_session, tenant_id)
        company_b = await _make_company(db_session, tenant_id)
        target = await _make_boat(db_session, tenant_id, company_a.id)
        await _make_boat(db_session, tenant_id, company_b.id)

        rows, total = await _search(repo, tenant_id, company_id=company_a.id)
        assert total == 1
        assert rows[0].id == target.id

    async def test_filters_by_is_active(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_boat(db_session, tenant_id, company_id, is_active=True)
        inactive = await _make_boat(db_session, tenant_id, company_id, is_active=False)

        rows, total = await _search(repo, tenant_id, is_active=False)
        assert total == 1
        assert rows[0].id == inactive.id

    async def test_filters_by_insurance_expired_true(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        expired = await _make_boat(db_session, tenant_id, company_id, insurance_expiry=_PAST)
        await _make_boat(db_session, tenant_id, company_id, insurance_expiry=_FUTURE)
        await _make_boat(db_session, tenant_id, company_id, insurance_expiry=None)

        rows, total = await _search(repo, tenant_id, insurance_expired=True)
        assert total == 1
        assert rows[0].id == expired.id

    async def test_filters_by_insurance_expired_false_includes_unset(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_boat(db_session, tenant_id, company_id, insurance_expiry=_PAST)
        not_expired = await _make_boat(
            db_session, tenant_id, company_id, insurance_expiry=_FUTURE
        )
        unset = await _make_boat(db_session, tenant_id, company_id, insurance_expiry=None)

        rows, total = await _search(repo, tenant_id, insurance_expired=False)
        assert total == 2
        assert {r.id for r in rows} == {not_expired.id, unset.id}

    async def test_filters_by_license_expired_true(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        expired = await _make_boat(db_session, tenant_id, company_id, license_expiry=_PAST)
        await _make_boat(db_session, tenant_id, company_id, license_expiry=_FUTURE)

        rows, total = await _search(repo, tenant_id, license_expired=True)
        assert total == 1
        assert rows[0].id == expired.id

    async def test_combines_filters(
        self, repo: BoatRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company_a = await _make_company(db_session, tenant_id)
        target = await _make_boat(
            db_session, tenant_id, company_a.id, boat_type="trawler", is_active=True
        )
        await _make_boat(db_session, tenant_id, company_a.id, boat_type="trawler", is_active=False)
        await _make_boat(
            db_session, tenant_id, company_a.id, boat_type="gillnetter", is_active=True
        )

        rows, total = await _search(repo, tenant_id, boat_type="trawler", is_active=True)
        assert total == 1
        assert rows[0].id == target.id

    async def test_excludes_soft_deleted_from_results(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_boat(db_session, tenant_id, company_id, deleted_at=datetime.now(UTC))
        rows, total = await _search(repo, tenant_id)
        assert total == 0
        assert rows == []


class TestSearchQuery:
    @pytest.mark.parametrize(
        ("field", "value", "query"),
        [
            ("code", "SPECIAL-CODE-1", "special-code"),
            ("name", "Ocean Falcon", "ocean"),
            ("registration_number", "MH-01-AB-9999", "mh-01-ab"),
            ("captain_name", "Suresh Patil", "suresh"),
        ],
    )
    async def test_matches_each_documented_field_case_insensitively(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        field: str,
        value: str,
        query: str,
    ) -> None:
        target = await _make_boat(db_session, tenant_id, company_id, **{field: value})
        await _make_boat(db_session, tenant_id, company_id)  # noise row that shouldn't match

        rows, total = await _search(repo, tenant_id, q=query)
        assert total == 1
        assert rows[0].id == target.id

    async def test_blank_query_returns_everything(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_boat(db_session, tenant_id, company_id)
        await _make_boat(db_session, tenant_id, company_id)

        rows, total = await _search(repo, tenant_id, q="   ")
        assert total == 2


class TestSearchSorting:
    async def _seed_three(
        self, db_session: AsyncSession, tenant_id: uuid.UUID, company_id: uuid.UUID
    ) -> None:
        await _make_boat(db_session, tenant_id, company_id, code="B-CODE", name="Bravo")
        await _make_boat(db_session, tenant_id, company_id, code="A-CODE", name="Alpha")
        await _make_boat(db_session, tenant_id, company_id, code="C-CODE", name="Charlie")

    async def test_sort_by_name_ascending(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, company_id)
        rows, _ = await _search(repo, tenant_id, sort="name")
        assert [r.name for r in rows] == ["Alpha", "Bravo", "Charlie"]

    async def test_sort_by_code_descending(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, company_id)
        rows, _ = await _search(repo, tenant_id, sort="-code")
        assert [r.code for r in rows] == ["C-CODE", "B-CODE", "A-CODE"]

    async def test_sort_by_created_at_and_updated_at_accepted(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, company_id)
        for sort in ("created_at", "-created_at", "updated_at", "-updated_at"):
            rows, total = await _search(repo, tenant_id, sort=sort)
            assert total == 3
            assert len(rows) == 3

    async def test_id_tie_break_follows_the_primary_sort_direction(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        """A tied created_at (two rows inserted in the same instant) must not
        silently override the caller's requested direction - the id
        tie-break has to point the same way as the primary sort."""
        tied_at = datetime.now(UTC)
        older_id_row = await _make_boat(db_session, tenant_id, company_id, created_at=tied_at)
        newer_id_row = await _make_boat(db_session, tenant_id, company_id, created_at=tied_at)
        assert older_id_row.id < newer_id_row.id  # uuid7 is time-ordered

        desc_rows, _ = await _search(repo, tenant_id, sort="-created_at")
        assert [r.id for r in desc_rows] == [newer_id_row.id, older_id_row.id]

        asc_rows, _ = await _search(repo, tenant_id, sort="created_at")
        assert [r.id for r in asc_rows] == [older_id_row.id, newer_id_row.id]


class TestSearchPagination:
    async def test_page_size_limits_rows_and_total_reflects_full_count(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        for i in range(5):
            await _make_boat(
                db_session, tenant_id, company_id, code=f"P-{i}", name=f"Page Boat {i}"
            )

        rows, total = await _search(repo, tenant_id, sort="code", page=1, page_size=2)
        assert total == 5
        assert len(rows) == 2

    async def test_pages_do_not_overlap_and_cover_all_rows(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        for i in range(5):
            await _make_boat(
                db_session, tenant_id, company_id, code=f"Q-{i}", name=f"Page Boat {i}"
            )

        seen_ids: set[uuid.UUID] = set()
        for page in (1, 2, 3):
            rows, _ = await _search(repo, tenant_id, sort="code", page=page, page_size=2)
            page_ids = {r.id for r in rows}
            assert not (page_ids & seen_ids), "pages overlapped"
            seen_ids |= page_ids
        assert len(seen_ids) == 5

    async def test_page_past_the_end_returns_empty(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_boat(db_session, tenant_id, company_id)
        rows, total = await _search(repo, tenant_id, page=99, page_size=10)
        assert total == 1
        assert rows == []


class TestSearchTenantScoping:
    async def test_never_returns_rows_from_another_tenant(
        self,
        repo: BoatRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        other_tenant = Tenant(name="Other Boat Tenant", slug=f"other-boat-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_company = await _make_company(db_session, other_tenant.id)

        mine = await _make_boat(db_session, tenant_id, company_id, name="Mine")
        await _make_boat(db_session, other_tenant.id, other_company.id, name="Not Mine")

        rows, total = await _search(repo, tenant_id)
        assert total == 1
        assert rows[0].id == mine.id
