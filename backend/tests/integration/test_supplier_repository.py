import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Tenant
from app.modules.suppliers.constants import SupplierStatus
from app.modules.suppliers.models import Supplier
from app.modules.suppliers.repository import SupplierRepository


@pytest.fixture
async def repo(db_session: AsyncSession) -> SupplierRepository:
    return SupplierRepository(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - the seeded default tenant may already carry
    suppliers from manual/exploratory testing, which would silently pollute
    any count-based assertion here."""
    tenant = Tenant(
        name="Supplier Repo Test Tenant", slug=f"supplier-repo-test-{uuid.uuid4().hex[:8]}"
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant.id


async def _make_supplier(
    db_session: AsyncSession, tenant_id: uuid.UUID, **overrides: Any
) -> Supplier:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "code": f"SUP-{uuid.uuid4().hex[:8]}",
        "name": f"Supplier {uuid.uuid4().hex[:8]}",
    }
    defaults.update(overrides)
    supplier = Supplier(**defaults)
    db_session.add(supplier)
    await db_session.commit()
    return supplier


class TestGetById:
    async def test_finds_supplier_in_own_tenant(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier = await _make_supplier(db_session, tenant_id, name="Findable Sup")
        found = await repo.get_by_id(supplier.id, tenant_id)
        assert found is not None
        assert found.name == "Findable Sup"

    async def test_returns_none_for_a_different_tenant(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier = await _make_supplier(db_session, tenant_id)
        assert await repo.get_by_id(supplier.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: SupplierRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id(uuid.uuid4(), tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier = await _make_supplier(db_session, tenant_id, deleted_at=datetime.now(UTC))
        assert await repo.get_by_id(supplier.id, tenant_id) is None


class TestSearchFilters:
    async def test_filters_by_status(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await _make_supplier(db_session, tenant_id, status=SupplierStatus.ACTIVE)
        inactive = await _make_supplier(db_session, tenant_id, status=SupplierStatus.INACTIVE)

        rows, total = await repo.search(
            tenant_id,
            q=None,
            status=SupplierStatus.INACTIVE,
            city=None,
            state=None,
            sort="-created_at",
            page=1,
            page_size=50,
        )
        assert total == 1
        assert rows[0].id == inactive.id

    async def test_filters_by_city_case_insensitively(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        mumbai = await _make_supplier(db_session, tenant_id, city="Mumbai")
        await _make_supplier(db_session, tenant_id, city="Kochi")

        rows, total = await repo.search(
            tenant_id,
            q=None,
            status=None,
            city="mumbai",
            state=None,
            sort="-created_at",
            page=1,
            page_size=50,
        )
        assert total == 1
        assert rows[0].id == mumbai.id

    async def test_filters_by_state(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        kerala = await _make_supplier(db_session, tenant_id, state="Kerala")
        await _make_supplier(db_session, tenant_id, state="Maharashtra")

        rows, total = await repo.search(
            tenant_id,
            q=None,
            status=None,
            city=None,
            state="Kerala",
            sort="-created_at",
            page=1,
            page_size=50,
        )
        assert total == 1
        assert rows[0].id == kerala.id

    async def test_combines_filters(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        target = await _make_supplier(
            db_session, tenant_id, city="Mumbai", status=SupplierStatus.ACTIVE
        )
        await _make_supplier(db_session, tenant_id, city="Mumbai", status=SupplierStatus.INACTIVE)
        await _make_supplier(db_session, tenant_id, city="Kochi", status=SupplierStatus.ACTIVE)

        rows, total = await repo.search(
            tenant_id,
            q=None,
            status=SupplierStatus.ACTIVE,
            city="Mumbai",
            state=None,
            sort="-created_at",
            page=1,
            page_size=50,
        )
        assert total == 1
        assert rows[0].id == target.id

    async def test_excludes_soft_deleted_from_results(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await _make_supplier(db_session, tenant_id, deleted_at=datetime.now(UTC))
        rows, total = await repo.search(
            tenant_id,
            q=None,
            status=None,
            city=None,
            state=None,
            sort="-created_at",
            page=1,
            page_size=50,
        )
        assert total == 0
        assert rows == []


class TestSearchQuery:
    @pytest.mark.parametrize(
        ("field", "value", "query"),
        [
            ("name", "Ocean Fresh Suppliers Ltd", "ocean"),
            ("code", "SPECIAL-CODE-1", "special-code"),
            ("gstin", "27ABCDE1234F1Z5", "abcde1234f"),
        ],
    )
    async def test_matches_each_documented_field_case_insensitively(
        self,
        repo: SupplierRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        field: str,
        value: str,
        query: str,
    ) -> None:
        target = await _make_supplier(db_session, tenant_id, **{field: value})
        await _make_supplier(db_session, tenant_id)  # noise row that shouldn't match

        rows, total = await repo.search(
            tenant_id,
            q=query,
            status=None,
            city=None,
            state=None,
            sort="-created_at",
            page=1,
            page_size=50,
        )
        assert total == 1
        assert rows[0].id == target.id

    async def test_blank_query_returns_everything(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await _make_supplier(db_session, tenant_id)
        await _make_supplier(db_session, tenant_id)

        rows, total = await repo.search(
            tenant_id,
            q="   ",
            status=None,
            city=None,
            state=None,
            sort="-created_at",
            page=1,
            page_size=50,
        )
        assert total == 2


class TestSearchSorting:
    async def _seed_three(self, db_session: AsyncSession, tenant_id: uuid.UUID) -> None:
        await _make_supplier(db_session, tenant_id, code="B-CODE", name="Bravo")
        await _make_supplier(db_session, tenant_id, code="A-CODE", name="Alpha")
        await _make_supplier(db_session, tenant_id, code="C-CODE", name="Charlie")

    async def test_sort_by_name_ascending(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await self._seed_three(db_session, tenant_id)
        rows, _ = await repo.search(
            tenant_id,
            q=None,
            status=None,
            city=None,
            state=None,
            sort="name",
            page=1,
            page_size=50,
        )
        assert [r.name for r in rows] == ["Alpha", "Bravo", "Charlie"]

    async def test_sort_by_code_descending(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await self._seed_three(db_session, tenant_id)
        rows, _ = await repo.search(
            tenant_id,
            q=None,
            status=None,
            city=None,
            state=None,
            sort="-code",
            page=1,
            page_size=50,
        )
        assert [r.code for r in rows] == ["C-CODE", "B-CODE", "A-CODE"]

    async def test_sort_by_created_at_accepted(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await self._seed_three(db_session, tenant_id)
        for sort in ("created_at", "-created_at"):
            rows, total = await repo.search(
                tenant_id,
                q=None,
                status=None,
                city=None,
                state=None,
                sort=sort,
                page=1,
                page_size=50,
            )
            assert total == 3
            assert len(rows) == 3


class TestSearchPagination:
    async def test_page_size_limits_rows_and_total_reflects_full_count(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        for i in range(5):
            await _make_supplier(db_session, tenant_id, code=f"P-{i}", name=f"Page Sup {i}")

        rows, total = await repo.search(
            tenant_id,
            q=None,
            status=None,
            city=None,
            state=None,
            sort="code",
            page=1,
            page_size=2,
        )
        assert total == 5
        assert len(rows) == 2

    async def test_pages_do_not_overlap_and_cover_all_rows(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        for i in range(5):
            await _make_supplier(db_session, tenant_id, code=f"Q-{i}", name=f"Page Sup {i}")

        seen_ids: set[uuid.UUID] = set()
        for page in (1, 2, 3):
            rows, _ = await repo.search(
                tenant_id,
                q=None,
                status=None,
                city=None,
                state=None,
                sort="code",
                page=page,
                page_size=2,
            )
            page_ids = {r.id for r in rows}
            assert not (page_ids & seen_ids), "pages overlapped"
            seen_ids |= page_ids
        assert len(seen_ids) == 5

    async def test_page_past_the_end_returns_empty(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await _make_supplier(db_session, tenant_id)
        rows, total = await repo.search(
            tenant_id,
            q=None,
            status=None,
            city=None,
            state=None,
            sort="-created_at",
            page=99,
            page_size=10,
        )
        assert total == 1
        assert rows == []


class TestSearchTenantScoping:
    async def test_never_returns_rows_from_another_tenant(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(name="Other Tenant Sup", slug=f"other-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()

        await _make_supplier(db_session, tenant_id, name="Mine")
        await _make_supplier(db_session, other_tenant.id, name="Not Mine")

        rows, total = await repo.search(
            tenant_id,
            q=None,
            status=None,
            city=None,
            state=None,
            sort="-created_at",
            page=1,
            page_size=50,
        )
        assert total == 1
        assert rows[0].name == "Mine"


class TestFindIdsByName:
    async def test_matches_by_ilike_pattern(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        target = await _make_supplier(db_session, tenant_id, name="Coastal Fish Suppliers")
        await _make_supplier(db_session, tenant_id, name="Irrelevant Co")

        ids = await repo.find_ids_by_name(tenant_id, "%coastal%")
        assert ids == [target.id]

    async def test_excludes_soft_deleted(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await _make_supplier(
            db_session, tenant_id, name="Deleted Coastal Co", deleted_at=datetime.now(UTC)
        )
        ids = await repo.find_ids_by_name(tenant_id, "%coastal%")
        assert ids == []

    async def test_scoped_to_tenant(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(name="Other Find Tenant", slug=f"other-find-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        await _make_supplier(db_session, other_tenant.id, name="Coastal Elsewhere")

        ids = await repo.find_ids_by_name(tenant_id, "%coastal%")
        assert ids == []


class TestSetOutstandingAmount:
    """SupplierService.recalculate_outstanding's straight SET (Sprint 12
    Session 4's outstanding engine) - distinct from
    increase_outstanding_amount's atomic += used by the Sprint 11 Session 5
    posting workflow."""

    async def test_overwrites_with_the_given_amount(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier = await _make_supplier(db_session, tenant_id, outstanding_amount=Decimal("999.00"))

        await repo.set_outstanding_amount(supplier.id, tenant_id, Decimal("2500.00"))
        await db_session.commit()

        refetched = await repo.get_by_id(supplier.id, tenant_id)
        assert refetched is not None
        assert refetched.outstanding_amount == Decimal("2500.00")

    async def test_can_set_back_to_zero(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier = await _make_supplier(db_session, tenant_id, outstanding_amount=Decimal("500.00"))

        await repo.set_outstanding_amount(supplier.id, tenant_id, Decimal("0"))
        await db_session.commit()

        refetched = await repo.get_by_id(supplier.id, tenant_id)
        assert refetched is not None
        assert refetched.outstanding_amount == Decimal("0.00")

    async def test_scoped_to_the_given_tenant(
        self, repo: SupplierRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier = await _make_supplier(db_session, tenant_id, outstanding_amount=Decimal("100.00"))

        await repo.set_outstanding_amount(supplier.id, uuid.uuid4(), Decimal("999.00"))
        await db_session.commit()

        refetched = await repo.get_by_id(supplier.id, tenant_id)
        assert refetched is not None
        assert refetched.outstanding_amount == Decimal("100.00")  # unchanged
