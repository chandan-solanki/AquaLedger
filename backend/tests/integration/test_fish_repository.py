import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Tenant
from app.modules.fish.constants import FishUnit
from app.modules.fish.models import Fish
from app.modules.fish.repository import FishRepository


@pytest.fixture
async def repo(db_session: AsyncSession) -> FishRepository:
    return FishRepository(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - the seeded default tenant may already carry
    fish from manual/exploratory testing, which would silently pollute any
    count-based assertion here."""
    tenant = Tenant(name="Fish Repo Test Tenant", slug=f"fish-repo-test-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    await db_session.commit()
    return tenant.id


async def _make_fish(db_session: AsyncSession, tenant_id: uuid.UUID, **overrides: Any) -> Fish:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "code": f"F-{uuid.uuid4().hex[:8]}",
        "name": f"Fish {uuid.uuid4().hex[:8]}",
    }
    defaults.update(overrides)
    fish = Fish(**defaults)
    db_session.add(fish)
    await db_session.commit()
    return fish


class TestGetById:
    async def test_finds_fish_in_own_tenant(
        self, repo: FishRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        fish = await _make_fish(db_session, tenant_id, name="Findable Fish")
        found = await repo.get_by_id(fish.id, tenant_id)
        assert found is not None
        assert found.name == "Findable Fish"

    async def test_returns_none_for_a_different_tenant(
        self, repo: FishRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        fish = await _make_fish(db_session, tenant_id)
        assert await repo.get_by_id(fish.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: FishRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id(uuid.uuid4(), tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self, repo: FishRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        fish = await _make_fish(db_session, tenant_id, deleted_at=datetime.now(UTC))
        assert await repo.get_by_id(fish.id, tenant_id) is None


async def _search(
    repo: FishRepository,
    tenant_id: uuid.UUID,
    *,
    q: str | None = None,
    category: str | None = None,
    unit: FishUnit | None = None,
    is_active: bool | None = None,
    sort: str = "-created_at",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Fish], int]:
    return await repo.search(
        tenant_id,
        q=q,
        category=category,
        unit=unit,
        is_active=is_active,
        sort=sort,
        page=page,
        page_size=page_size,
    )


class TestSearchFilters:
    async def test_filters_by_category_case_insensitively(
        self, repo: FishRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        whitefish = await _make_fish(db_session, tenant_id, category="Whitefish")
        await _make_fish(db_session, tenant_id, category="Shellfish")

        rows, total = await _search(repo, tenant_id, category="whitefish")
        assert total == 1
        assert rows[0].id == whitefish.id

    async def test_filters_by_unit(
        self, repo: FishRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        boxed = await _make_fish(db_session, tenant_id, unit=FishUnit.BOX)
        await _make_fish(db_session, tenant_id, unit=FishUnit.KG)

        rows, total = await _search(repo, tenant_id, unit=FishUnit.BOX)
        assert total == 1
        assert rows[0].id == boxed.id

    async def test_filters_by_is_active(
        self, repo: FishRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await _make_fish(db_session, tenant_id, is_active=True)
        inactive = await _make_fish(db_session, tenant_id, is_active=False)

        rows, total = await _search(repo, tenant_id, is_active=False)
        assert total == 1
        assert rows[0].id == inactive.id

    async def test_combines_filters(
        self, repo: FishRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        target = await _make_fish(db_session, tenant_id, category="Whitefish", unit=FishUnit.KG)
        await _make_fish(db_session, tenant_id, category="Whitefish", unit=FishUnit.BOX)
        await _make_fish(db_session, tenant_id, category="Shellfish", unit=FishUnit.KG)

        rows, total = await _search(repo, tenant_id, category="Whitefish", unit=FishUnit.KG)
        assert total == 1
        assert rows[0].id == target.id

    async def test_excludes_soft_deleted_from_results(
        self, repo: FishRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await _make_fish(db_session, tenant_id, deleted_at=datetime.now(UTC))
        rows, total = await _search(repo, tenant_id)
        assert total == 0
        assert rows == []


class TestSearchQuery:
    @pytest.mark.parametrize(
        ("field", "value", "query"),
        [
            ("code", "SPECIAL-CODE-1", "special-code"),
            ("name", "Ocean Pomfret", "ocean"),
            ("local_name", "Paplet", "paplet"),
            ("scientific_name", "Pampus argenteus", "pampus"),
        ],
    )
    async def test_matches_each_documented_field_case_insensitively(
        self,
        repo: FishRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        field: str,
        value: str,
        query: str,
    ) -> None:
        target = await _make_fish(db_session, tenant_id, **{field: value})
        await _make_fish(db_session, tenant_id)  # noise row that shouldn't match

        rows, total = await _search(repo, tenant_id, q=query)
        assert total == 1
        assert rows[0].id == target.id

    async def test_blank_query_returns_everything(
        self, repo: FishRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await _make_fish(db_session, tenant_id)
        await _make_fish(db_session, tenant_id)

        rows, total = await _search(repo, tenant_id, q="   ")
        assert total == 2


class TestSearchSorting:
    async def _seed_three(self, db_session: AsyncSession, tenant_id: uuid.UUID) -> None:
        await _make_fish(db_session, tenant_id, code="B-CODE", name="Bravo")
        await _make_fish(db_session, tenant_id, code="A-CODE", name="Alpha")
        await _make_fish(db_session, tenant_id, code="C-CODE", name="Charlie")

    async def test_sort_by_name_ascending(
        self, repo: FishRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await self._seed_three(db_session, tenant_id)
        rows, _ = await _search(repo, tenant_id, sort="name")
        assert [r.name for r in rows] == ["Alpha", "Bravo", "Charlie"]

    async def test_sort_by_code_descending(
        self, repo: FishRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await self._seed_three(db_session, tenant_id)
        rows, _ = await _search(repo, tenant_id, sort="-code")
        assert [r.code for r in rows] == ["C-CODE", "B-CODE", "A-CODE"]

    async def test_sort_by_created_at_and_updated_at_accepted(
        self, repo: FishRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await self._seed_three(db_session, tenant_id)
        for sort in ("created_at", "-created_at", "updated_at", "-updated_at"):
            rows, total = await _search(repo, tenant_id, sort=sort)
            assert total == 3
            assert len(rows) == 3

    async def test_id_tie_break_follows_the_primary_sort_direction(
        self, repo: FishRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        """A tied created_at (two rows inserted in the same instant) must not
        silently override the caller's requested direction - the id
        tie-break has to point the same way as the primary sort."""
        tied_at = datetime.now(UTC)
        older_id_row = await _make_fish(db_session, tenant_id, created_at=tied_at)
        newer_id_row = await _make_fish(db_session, tenant_id, created_at=tied_at)
        assert older_id_row.id < newer_id_row.id  # uuid7 is time-ordered

        desc_rows, _ = await _search(repo, tenant_id, sort="-created_at")
        assert [r.id for r in desc_rows] == [newer_id_row.id, older_id_row.id]

        asc_rows, _ = await _search(repo, tenant_id, sort="created_at")
        assert [r.id for r in asc_rows] == [older_id_row.id, newer_id_row.id]


class TestSearchPagination:
    async def test_page_size_limits_rows_and_total_reflects_full_count(
        self, repo: FishRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        for i in range(5):
            await _make_fish(db_session, tenant_id, code=f"P-{i}", name=f"Page Fish {i}")

        rows, total = await _search(repo, tenant_id, sort="code", page=1, page_size=2)
        assert total == 5
        assert len(rows) == 2

    async def test_pages_do_not_overlap_and_cover_all_rows(
        self, repo: FishRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        for i in range(5):
            await _make_fish(db_session, tenant_id, code=f"Q-{i}", name=f"Page Fish {i}")

        seen_ids: set[uuid.UUID] = set()
        for page in (1, 2, 3):
            rows, _ = await _search(repo, tenant_id, sort="code", page=page, page_size=2)
            page_ids = {r.id for r in rows}
            assert not (page_ids & seen_ids), "pages overlapped"
            seen_ids |= page_ids
        assert len(seen_ids) == 5

    async def test_page_past_the_end_returns_empty(
        self, repo: FishRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await _make_fish(db_session, tenant_id)
        rows, total = await _search(repo, tenant_id, page=99, page_size=10)
        assert total == 1
        assert rows == []


class TestSearchTenantScoping:
    async def test_never_returns_rows_from_another_tenant(
        self, repo: FishRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(name="Other Fish Tenant", slug=f"other-fish-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()

        mine = await _make_fish(db_session, tenant_id, name="Mine")
        await _make_fish(db_session, other_tenant.id, name="Not Mine")

        rows, total = await _search(repo, tenant_id)
        assert total == 1
        assert rows[0].id == mine.id
