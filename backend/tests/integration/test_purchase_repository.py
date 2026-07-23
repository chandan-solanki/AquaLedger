import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Tenant
from app.modules.purchase.constants import PurchaseStatus
from app.modules.purchase.models import PurchaseBill, PurchaseBillItem, PurchaseSequence
from app.modules.purchase.repository import PurchaseRepository
from app.modules.suppliers.models import Supplier

_BILL_DATE = date(2026, 7, 1)


@pytest.fixture
async def repo(db_session: AsyncSession) -> PurchaseRepository:
    return PurchaseRepository(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - the seeded default tenant may already carry
    purchase bills from manual/exploratory testing, which would silently
    pollute any count-based assertion here."""
    tenant = Tenant(
        name="Purchase Repo Test Tenant", slug=f"purchase-repo-test-{uuid.uuid4().hex[:8]}"
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


@pytest.fixture
async def supplier_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    supplier = await _make_supplier(db_session, tenant_id)
    return supplier.id


async def _make_bill(
    db_session: AsyncSession, tenant_id: uuid.UUID, supplier_id: uuid.UUID, **overrides: Any
) -> PurchaseBill:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "supplier_id": supplier_id,
        "bill_date": _BILL_DATE,
        "status": PurchaseStatus.DRAFT,
        "subtotal": Decimal("0"),
        "discount_amount": Decimal("0"),
        "tax_amount": Decimal("0"),
        "transport_charge": Decimal("0"),
        "other_charge": Decimal("0"),
        "round_off": Decimal("0"),
        "total_amount": Decimal("0"),
        "paid_amount": Decimal("0"),
        "balance_amount": Decimal("0"),
    }
    defaults.update(overrides)
    bill = PurchaseBill(**defaults)
    db_session.add(bill)
    await db_session.commit()
    return bill


async def _search(
    repo: PurchaseRepository,
    tenant_id: uuid.UUID,
    *,
    q: str | None = None,
    q_supplier_ids: list[uuid.UUID] | None = None,
    status: PurchaseStatus | None = None,
    supplier_id: uuid.UUID | None = None,
    bill_date_from: date | None = None,
    bill_date_to: date | None = None,
    sort: str = "-created_at",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[PurchaseBill], int]:
    return await repo.search(
        tenant_id,
        q=q,
        q_supplier_ids=q_supplier_ids,
        status=status,
        supplier_id=supplier_id,
        bill_date_from=bill_date_from,
        bill_date_to=bill_date_to,
        sort=sort,
        page=page,
        page_size=page_size,
    )


class TestGetById:
    async def test_finds_bill_in_own_tenant(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id, remarks="Findable")
        found = await repo.get_by_id(bill.id, tenant_id)
        assert found is not None
        assert found.remarks == "Findable"

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        assert await repo.get_by_id(bill.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: PurchaseRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id(uuid.uuid4(), tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id, deleted_at=datetime.now(UTC))
        assert await repo.get_by_id(bill.id, tenant_id) is None


class TestSearchFilters:
    async def test_filters_by_status(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_bill(db_session, tenant_id, supplier_id, status=PurchaseStatus.DRAFT)
        posted = await _make_bill(db_session, tenant_id, supplier_id, status=PurchaseStatus.POSTED)

        rows, total = await _search(repo, tenant_id, status=PurchaseStatus.POSTED)
        assert total == 1
        assert rows[0].id == posted.id

    async def test_filters_by_supplier_id(
        self, repo: PurchaseRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier_a = await _make_supplier(db_session, tenant_id)
        supplier_b = await _make_supplier(db_session, tenant_id)
        target = await _make_bill(db_session, tenant_id, supplier_a.id)
        await _make_bill(db_session, tenant_id, supplier_b.id)

        rows, total = await _search(repo, tenant_id, supplier_id=supplier_a.id)
        assert total == 1
        assert rows[0].id == target.id

    async def test_filters_by_bill_date_range(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        in_range = await _make_bill(db_session, tenant_id, supplier_id, bill_date=date(2026, 6, 15))
        await _make_bill(db_session, tenant_id, supplier_id, bill_date=date(2026, 1, 1))
        await _make_bill(db_session, tenant_id, supplier_id, bill_date=date(2026, 12, 31))

        rows, total = await _search(
            repo,
            tenant_id,
            bill_date_from=date(2026, 6, 1),
            bill_date_to=date(2026, 6, 30),
        )
        assert total == 1
        assert rows[0].id == in_range.id

    async def test_combines_filters(
        self, repo: PurchaseRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier_a = await _make_supplier(db_session, tenant_id)
        supplier_b = await _make_supplier(db_session, tenant_id)
        target = await _make_bill(db_session, tenant_id, supplier_a.id, status=PurchaseStatus.DRAFT)
        await _make_bill(db_session, tenant_id, supplier_a.id, status=PurchaseStatus.POSTED)
        await _make_bill(db_session, tenant_id, supplier_b.id, status=PurchaseStatus.DRAFT)

        rows, total = await _search(
            repo, tenant_id, supplier_id=supplier_a.id, status=PurchaseStatus.DRAFT
        )
        assert total == 1
        assert rows[0].id == target.id

    async def test_excludes_soft_deleted_from_results(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_bill(db_session, tenant_id, supplier_id, deleted_at=datetime.now(UTC))
        rows, total = await _search(repo, tenant_id)
        assert total == 0
        assert rows == []


class TestSearchQuery:
    async def test_matches_bill_number_case_insensitively(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        target = await _make_bill(
            db_session, tenant_id, supplier_id, bill_number="PUR/2026-27/00042"
        )
        await _make_bill(db_session, tenant_id, supplier_id)  # noise row, no bill number

        rows, total = await _search(repo, tenant_id, q="pur/2026-27")
        assert total == 1
        assert rows[0].id == target.id

    async def test_matches_via_pre_resolved_supplier_ids(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        matching = await _make_bill(db_session, tenant_id, supplier_id)
        other_supplier = await _make_supplier(db_session, tenant_id)
        await _make_bill(db_session, tenant_id, other_supplier.id)

        # q_supplier_ids is pre-resolved by the service (via
        # SupplierService.find_ids_by_name) - the repository just OR's a
        # supplier_id IN (...) onto the bill_number ILIKE match.
        rows, total = await _search(repo, tenant_id, q="ocean", q_supplier_ids=[supplier_id])
        assert total == 1
        assert rows[0].id == matching.id

    async def test_q_with_no_matching_supplier_ids_still_matches_bill_number(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        target = await _make_bill(db_session, tenant_id, supplier_id, bill_number="SEARCHME-001")
        rows, total = await _search(repo, tenant_id, q="searchme", q_supplier_ids=[])
        assert total == 1
        assert rows[0].id == target.id

    async def test_no_match_returns_empty(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_bill(db_session, tenant_id, supplier_id, bill_number="NUMBER-001")
        rows, total = await _search(repo, tenant_id, q="no-such-bill", q_supplier_ids=[])
        assert total == 0
        assert rows == []

    async def test_blank_query_returns_everything(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_bill(db_session, tenant_id, supplier_id)
        await _make_bill(db_session, tenant_id, supplier_id)

        rows, total = await _search(repo, tenant_id, q="   ")
        assert total == 2


class TestSearchSorting:
    async def _seed_three(
        self, db_session: AsyncSession, tenant_id: uuid.UUID, supplier_id: uuid.UUID
    ) -> None:
        await _make_bill(
            db_session,
            tenant_id,
            supplier_id,
            bill_date=date(2026, 2, 1),
            bill_number="PUR-B",
        )
        await _make_bill(
            db_session,
            tenant_id,
            supplier_id,
            bill_date=date(2026, 1, 1),
            bill_number="PUR-A",
        )
        await _make_bill(
            db_session,
            tenant_id,
            supplier_id,
            bill_date=date(2026, 3, 1),
            bill_number="PUR-C",
        )

    async def test_sort_by_bill_date_ascending(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, supplier_id)
        rows, _ = await _search(repo, tenant_id, sort="bill_date")
        assert [r.bill_date for r in rows] == [
            date(2026, 1, 1),
            date(2026, 2, 1),
            date(2026, 3, 1),
        ]

    async def test_sort_by_bill_number_descending(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, supplier_id)
        rows, _ = await _search(repo, tenant_id, sort="-bill_number")
        assert [r.bill_number for r in rows] == ["PUR-C", "PUR-B", "PUR-A"]

    async def test_sort_by_created_at_accepted(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, supplier_id)
        for sort in ("created_at", "-created_at"):
            rows, total = await _search(repo, tenant_id, sort=sort)
            assert total == 3
            assert len(rows) == 3


class TestSearchPagination:
    async def test_page_size_limits_rows_and_total_reflects_full_count(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        for i in range(5):
            await _make_bill(db_session, tenant_id, supplier_id, bill_number=f"P-{i}")

        rows, total = await _search(repo, tenant_id, sort="bill_number", page=1, page_size=2)
        assert total == 5
        assert len(rows) == 2

    async def test_pages_do_not_overlap_and_cover_all_rows(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        for i in range(5):
            await _make_bill(db_session, tenant_id, supplier_id, bill_number=f"Q-{i}")

        seen_ids: set[uuid.UUID] = set()
        for page in (1, 2, 3):
            rows, _ = await _search(repo, tenant_id, sort="bill_number", page=page, page_size=2)
            page_ids = {r.id for r in rows}
            assert not (page_ids & seen_ids), "pages overlapped"
            seen_ids |= page_ids
        assert len(seen_ids) == 5

    async def test_page_past_the_end_returns_empty(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_bill(db_session, tenant_id, supplier_id)
        rows, total = await _search(repo, tenant_id, page=99, page_size=10)
        assert total == 1
        assert rows == []


class TestSearchTenantScoping:
    async def test_never_returns_rows_from_another_tenant(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        other_tenant = Tenant(name="Other Tenant Purch", slug=f"other-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_supplier = await _make_supplier(db_session, other_tenant.id)

        mine = await _make_bill(db_session, tenant_id, supplier_id, bill_number="MINE-001")
        await _make_bill(db_session, other_tenant.id, other_supplier.id, bill_number="NOT-MINE-001")

        rows, total = await _search(repo, tenant_id)
        assert total == 1
        assert rows[0].id == mine.id


class TestAdd:
    async def test_stages_a_new_bill(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = PurchaseBill(
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            bill_date=_BILL_DATE,
            status=PurchaseStatus.DRAFT,
            subtotal=Decimal("0"),
            discount_amount=Decimal("0"),
            tax_amount=Decimal("0"),
            transport_charge=Decimal("0"),
            other_charge=Decimal("0"),
            round_off=Decimal("0"),
            total_amount=Decimal("0"),
            paid_amount=Decimal("0"),
            balance_amount=Decimal("0"),
        )
        await repo.add(bill)
        await db_session.commit()

        found = await repo.get_by_id(bill.id, tenant_id)
        assert found is not None
        assert found.supplier_id == supplier_id


def _make_item(
    tenant_id: uuid.UUID, purchase_bill_id: uuid.UUID, line_number: int, **overrides: Any
) -> PurchaseBillItem:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "purchase_bill_id": purchase_bill_id,
        "line_number": line_number,
        "quantity": Decimal("1.000"),
        "unit": "KG",
        "rate": Decimal("1.0000"),
    }
    defaults.update(overrides)
    return PurchaseBillItem(**defaults)


class TestGetItemById:
    async def test_finds_item_scoped_to_bill_and_tenant(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        item = _make_item(tenant_id, bill.id, 1, description="Findable")
        db_session.add(item)
        await db_session.commit()

        found = await repo.get_item_by_id(item.id, bill.id, tenant_id)
        assert found is not None
        assert found.description == "Findable"

    async def test_returns_none_for_a_different_bill(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        other_bill = await _make_bill(db_session, tenant_id, supplier_id)
        item = _make_item(tenant_id, bill.id, 1)
        db_session.add(item)
        await db_session.commit()

        assert await repo.get_item_by_id(item.id, other_bill.id, tenant_id) is None

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        item = _make_item(tenant_id, bill.id, 1)
        db_session.add(item)
        await db_session.commit()

        assert await repo.get_item_by_id(item.id, bill.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        assert await repo.get_item_by_id(uuid.uuid4(), bill.id, tenant_id) is None


class TestAllocateNextLineNumber:
    async def test_first_allocation_returns_one(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        line_number = await repo.allocate_next_line_number(bill.id, tenant_id)
        await db_session.commit()
        assert line_number == 1

    async def test_sequential_allocations_increment(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        first = await repo.allocate_next_line_number(bill.id, tenant_id)
        second = await repo.allocate_next_line_number(bill.id, tenant_id)
        third = await repo.allocate_next_line_number(bill.id, tenant_id)
        await db_session.commit()
        assert [first, second, third] == [1, 2, 3]

    async def test_number_is_never_reused_after_the_item_is_deleted(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        first = await repo.allocate_next_line_number(bill.id, tenant_id)
        item = _make_item(tenant_id, bill.id, first)
        db_session.add(item)
        await db_session.commit()

        await repo.delete_item(item)
        await db_session.commit()

        next_number = await repo.allocate_next_line_number(bill.id, tenant_id)
        await db_session.commit()
        assert next_number == first + 1

    async def test_scoped_to_its_own_bill(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill_a = await _make_bill(db_session, tenant_id, supplier_id)
        bill_b = await _make_bill(db_session, tenant_id, supplier_id)
        await repo.allocate_next_line_number(bill_a.id, tenant_id)
        await repo.allocate_next_line_number(bill_a.id, tenant_id)
        first_on_b = await repo.allocate_next_line_number(bill_b.id, tenant_id)
        await db_session.commit()
        assert first_on_b == 1


class TestSearchItems:
    async def test_returns_items_ordered_by_line_number_by_default(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        for line_number in (3, 1, 2):
            db_session.add(_make_item(tenant_id, bill.id, line_number))
        await db_session.commit()

        items = await repo.search_items(bill.id, tenant_id, q=None, sort="line_number")
        assert [i.line_number for i in items] == [1, 2, 3]

    async def test_scoped_to_bill_and_tenant(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        other_bill = await _make_bill(db_session, tenant_id, supplier_id)
        item = _make_item(tenant_id, bill.id, 1)
        db_session.add(item)
        db_session.add(_make_item(tenant_id, other_bill.id, 1))
        await db_session.commit()

        items = await repo.search_items(bill.id, tenant_id, q=None, sort="line_number")
        assert [i.id for i in items] == [item.id]

    async def test_q_matches_description_case_insensitively(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        target = _make_item(tenant_id, bill.id, 1, description="Pomfret - Grade A")
        db_session.add(target)
        db_session.add(_make_item(tenant_id, bill.id, 2, description="Sardine"))
        await db_session.commit()

        items = await repo.search_items(bill.id, tenant_id, q="pomfret", sort="line_number")
        assert [i.id for i in items] == [target.id]

    async def test_blank_query_returns_everything(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        db_session.add(_make_item(tenant_id, bill.id, 1))
        db_session.add(_make_item(tenant_id, bill.id, 2))
        await db_session.commit()

        items = await repo.search_items(bill.id, tenant_id, q="   ", sort="line_number")
        assert len(items) == 2

    async def test_sort_by_description_descending(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        db_session.add(_make_item(tenant_id, bill.id, 1, description="Alpha"))
        db_session.add(_make_item(tenant_id, bill.id, 2, description="Charlie"))
        db_session.add(_make_item(tenant_id, bill.id, 3, description="Bravo"))
        await db_session.commit()

        items = await repo.search_items(bill.id, tenant_id, q=None, sort="-description")
        assert [i.description for i in items] == ["Charlie", "Bravo", "Alpha"]


class TestSearchItemsAggregation:
    """search_items(q=None, sort="line_number") is what
    PurchaseService._recalculate_purchase_bill (Session 4) uses to fetch
    every item on a bill before summing their totals - this exercises that
    exact call shape, distinct from TestSearchItems' filter/sort coverage."""

    async def test_returns_every_item_for_aggregation(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        db_session.add(_make_item(tenant_id, bill.id, 1, quantity=Decimal("10.000")))
        db_session.add(_make_item(tenant_id, bill.id, 2, quantity=Decimal("5.000")))
        db_session.add(_make_item(tenant_id, bill.id, 3, quantity=Decimal("2.500")))
        await db_session.commit()

        items = await repo.search_items(bill.id, tenant_id, q=None, sort="line_number")
        total_quantity = sum((i.quantity for i in items), Decimal("0"))
        assert total_quantity == Decimal("17.500")

    async def test_empty_bill_aggregates_to_nothing(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        items = await repo.search_items(bill.id, tenant_id, q=None, sort="line_number")
        assert items == []

    async def test_excludes_items_from_other_bills_from_aggregation(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        other_bill = await _make_bill(db_session, tenant_id, supplier_id)
        db_session.add(_make_item(tenant_id, bill.id, 1, quantity=Decimal("10.000")))
        db_session.add(_make_item(tenant_id, other_bill.id, 1, quantity=Decimal("999.000")))
        await db_session.commit()

        items = await repo.search_items(bill.id, tenant_id, q=None, sort="line_number")
        assert [i.quantity for i in items] == [Decimal("10.000")]


class TestAddAndDeleteItem:
    async def test_add_item_stages_and_persists(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        item = _make_item(tenant_id, bill.id, 1, description="New Item")
        await repo.add_item(item)
        await db_session.commit()

        found = await repo.get_item_by_id(item.id, bill.id, tenant_id)
        assert found is not None
        assert found.description == "New Item"

    async def test_delete_item_hard_deletes_the_row(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        item = _make_item(tenant_id, bill.id, 1)
        db_session.add(item)
        await db_session.commit()
        item_id = item.id

        await repo.delete_item(item)
        await db_session.commit()

        assert await repo.get_item_by_id(item_id, bill.id, tenant_id) is None


class TestGetByIdForUpdate:
    async def test_finds_bill_in_own_tenant(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id, remarks="Lockable")
        found = await repo.get_by_id_for_update(bill.id, tenant_id)
        assert found is not None
        assert found.remarks == "Lockable"

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        assert await repo.get_by_id_for_update(bill.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: PurchaseRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id_for_update(uuid.uuid4(), tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id, deleted_at=datetime.now(UTC))
        assert await repo.get_by_id_for_update(bill.id, tenant_id) is None

    async def test_mutations_on_the_locked_row_persist_after_commit(
        self,
        repo: PurchaseRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier_id)
        locked = await repo.get_by_id_for_update(bill.id, tenant_id)
        assert locked is not None
        locked.bill_number = "PUR/2026-27/00001"
        locked.status = PurchaseStatus.POSTED
        await db_session.commit()

        refetched = await repo.get_by_id(bill.id, tenant_id)
        assert refetched is not None
        assert refetched.bill_number == "PUR/2026-27/00001"
        assert refetched.status == PurchaseStatus.POSTED


class TestSequenceRow:
    """The Session 5 posting workflow's purchase bill numbering counter -
    ensure_sequence_row (`INSERT ... ON CONFLICT DO NOTHING`) followed by
    get_sequence_for_update (`SELECT ... FOR UPDATE`). Mirrors
    InvoiceRepository's own TestSequenceRow exactly."""

    async def test_ensure_creates_a_row_starting_at_zero(
        self, repo: PurchaseRepository, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "PUR", "2026-27")
        sequence = await repo.get_sequence_for_update(tenant_id, "PUR", "2026-27")
        assert sequence.last_number == 0

    async def test_ensure_is_idempotent_and_does_not_reset_an_existing_counter(
        self, repo: PurchaseRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "PUR", "2026-27")
        sequence = await repo.get_sequence_for_update(tenant_id, "PUR", "2026-27")
        sequence.last_number += 1
        await db_session.commit()

        # A second ensure_sequence_row call (as post() makes on every
        # purchase bill, not just the first per fiscal year) must not
        # clobber the counter back to zero.
        await repo.ensure_sequence_row(tenant_id, "PUR", "2026-27")
        relocked = await repo.get_sequence_for_update(tenant_id, "PUR", "2026-27")
        assert relocked.last_number == 1

    async def test_increment_persists_after_commit(
        self, repo: PurchaseRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "PUR", "2026-27")
        sequence = await repo.get_sequence_for_update(tenant_id, "PUR", "2026-27")
        sequence.last_number += 1
        await db_session.commit()

        result = await db_session.execute(
            select(PurchaseSequence).where(
                PurchaseSequence.tenant_id == tenant_id,
                PurchaseSequence.prefix == "PUR",
                PurchaseSequence.fiscal_year == "2026-27",
            )
        )
        assert result.scalar_one().last_number == 1

    async def test_different_fiscal_years_are_independent_counters(
        self, repo: PurchaseRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "PUR", "2025-26")
        early = await repo.get_sequence_for_update(tenant_id, "PUR", "2025-26")
        early.last_number += 1
        await db_session.commit()

        await repo.ensure_sequence_row(tenant_id, "PUR", "2026-27")
        late = await repo.get_sequence_for_update(tenant_id, "PUR", "2026-27")
        assert late.last_number == 0

    async def test_different_tenants_are_independent_counters(
        self, repo: PurchaseRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Purchase Sequence Tenant", slug=f"other-pur-seq-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()

        await repo.ensure_sequence_row(tenant_id, "PUR", "2026-27")
        mine = await repo.get_sequence_for_update(tenant_id, "PUR", "2026-27")
        mine.last_number += 1
        await db_session.commit()

        await repo.ensure_sequence_row(other_tenant.id, "PUR", "2026-27")
        theirs = await repo.get_sequence_for_update(other_tenant.id, "PUR", "2026-27")
        assert theirs.last_number == 0
