import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Tenant
from app.modules.purchase_orders.constants import PurchaseOrderStatus
from app.modules.purchase_orders.models import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderSequence,
)
from app.modules.purchase_orders.repository import PurchaseOrderRepository
from app.modules.suppliers.models import Supplier

_ORDER_DATE = date(2026, 8, 1)


@pytest.fixture
async def repo(db_session: AsyncSession) -> PurchaseOrderRepository:
    return PurchaseOrderRepository(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - the seeded default tenant may already carry
    purchase orders from manual/exploratory testing, which would silently
    pollute any count-based assertion here."""
    tenant = Tenant(
        name="Purchase Order Repo Test Tenant",
        slug=f"purchase-order-repo-test-{uuid.uuid4().hex[:8]}",
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


async def _make_order(
    db_session: AsyncSession, tenant_id: uuid.UUID, supplier_id: uuid.UUID, **overrides: Any
) -> PurchaseOrder:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "supplier_id": supplier_id,
        "order_date": _ORDER_DATE,
        "status": PurchaseOrderStatus.DRAFT,
        "subtotal": Decimal("0"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("0"),
        "tax_amount": Decimal("0"),
        "transport_charge": Decimal("0"),
        "other_charge": Decimal("0"),
        "round_off": Decimal("0"),
        "total_amount": Decimal("0"),
    }
    defaults.update(overrides)
    order = PurchaseOrder(**defaults)
    db_session.add(order)
    await db_session.commit()
    return order


async def _search(
    repo: PurchaseOrderRepository,
    tenant_id: uuid.UUID,
    *,
    q: str | None = None,
    q_supplier_ids: list[uuid.UUID] | None = None,
    status: PurchaseOrderStatus | None = None,
    supplier_id: uuid.UUID | None = None,
    order_date_from: date | None = None,
    order_date_to: date | None = None,
    sort: str = "-created_at",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[PurchaseOrder], int]:
    return await repo.search(
        tenant_id,
        q=q,
        q_supplier_ids=q_supplier_ids,
        status=status,
        supplier_id=supplier_id,
        order_date_from=order_date_from,
        order_date_to=order_date_to,
        sort=sort,
        page=page,
        page_size=page_size,
    )


class TestGetById:
    async def test_finds_order_in_own_tenant(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id, remarks="Findable")
        found = await repo.get_by_id(order.id, tenant_id)
        assert found is not None
        assert found.remarks == "Findable"

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        assert await repo.get_by_id(order.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: PurchaseOrderRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id(uuid.uuid4(), tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id, deleted_at=datetime.now(UTC))
        assert await repo.get_by_id(order.id, tenant_id) is None


class TestSearchFilters:
    async def test_filters_by_status(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_order(db_session, tenant_id, supplier_id, status=PurchaseOrderStatus.DRAFT)
        confirmed = await _make_order(
            db_session, tenant_id, supplier_id, status=PurchaseOrderStatus.CONFIRMED
        )

        rows, total = await _search(repo, tenant_id, status=PurchaseOrderStatus.CONFIRMED)
        assert total == 1
        assert rows[0].id == confirmed.id

    async def test_filters_by_supplier_id(
        self, repo: PurchaseOrderRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier_a = await _make_supplier(db_session, tenant_id)
        supplier_b = await _make_supplier(db_session, tenant_id)
        target = await _make_order(db_session, tenant_id, supplier_a.id)
        await _make_order(db_session, tenant_id, supplier_b.id)

        rows, total = await _search(repo, tenant_id, supplier_id=supplier_a.id)
        assert total == 1
        assert rows[0].id == target.id

    async def test_filters_by_order_date_range(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        in_range = await _make_order(
            db_session, tenant_id, supplier_id, order_date=date(2026, 6, 15)
        )
        await _make_order(db_session, tenant_id, supplier_id, order_date=date(2026, 1, 1))
        await _make_order(db_session, tenant_id, supplier_id, order_date=date(2026, 12, 31))

        rows, total = await _search(
            repo,
            tenant_id,
            order_date_from=date(2026, 6, 1),
            order_date_to=date(2026, 6, 30),
        )
        assert total == 1
        assert rows[0].id == in_range.id

    async def test_combines_filters(
        self, repo: PurchaseOrderRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier_a = await _make_supplier(db_session, tenant_id)
        supplier_b = await _make_supplier(db_session, tenant_id)
        target = await _make_order(
            db_session, tenant_id, supplier_a.id, status=PurchaseOrderStatus.DRAFT
        )
        await _make_order(
            db_session, tenant_id, supplier_a.id, status=PurchaseOrderStatus.CONFIRMED
        )
        await _make_order(db_session, tenant_id, supplier_b.id, status=PurchaseOrderStatus.DRAFT)

        rows, total = await _search(
            repo, tenant_id, supplier_id=supplier_a.id, status=PurchaseOrderStatus.DRAFT
        )
        assert total == 1
        assert rows[0].id == target.id

    async def test_excludes_soft_deleted_from_results(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_order(db_session, tenant_id, supplier_id, deleted_at=datetime.now(UTC))
        rows, total = await _search(repo, tenant_id)
        assert total == 0
        assert rows == []


class TestSearchQuery:
    async def test_matches_po_number_case_insensitively(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        target = await _make_order(db_session, tenant_id, supplier_id, po_number="PO/2026-27/00042")
        await _make_order(db_session, tenant_id, supplier_id)  # noise row, no po number

        rows, total = await _search(repo, tenant_id, q="po/2026-27")
        assert total == 1
        assert rows[0].id == target.id

    async def test_matches_via_pre_resolved_supplier_ids(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        matching = await _make_order(db_session, tenant_id, supplier_id)
        other_supplier = await _make_supplier(db_session, tenant_id)
        await _make_order(db_session, tenant_id, other_supplier.id)

        # q_supplier_ids is pre-resolved by the service (via
        # SupplierService.find_ids_by_name) - the repository just OR's a
        # supplier_id IN (...) onto the po_number ILIKE match.
        rows, total = await _search(repo, tenant_id, q="ocean", q_supplier_ids=[supplier_id])
        assert total == 1
        assert rows[0].id == matching.id

    async def test_q_with_no_matching_supplier_ids_still_matches_po_number(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        target = await _make_order(db_session, tenant_id, supplier_id, po_number="SEARCHME-001")
        rows, total = await _search(repo, tenant_id, q="searchme", q_supplier_ids=[])
        assert total == 1
        assert rows[0].id == target.id

    async def test_no_match_returns_empty(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_order(db_session, tenant_id, supplier_id, po_number="NUMBER-001")
        rows, total = await _search(repo, tenant_id, q="no-such-order", q_supplier_ids=[])
        assert total == 0
        assert rows == []

    async def test_blank_query_returns_everything(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_order(db_session, tenant_id, supplier_id)
        await _make_order(db_session, tenant_id, supplier_id)

        rows, total = await _search(repo, tenant_id, q="   ")
        assert total == 2


class TestSearchSorting:
    async def _seed_three(
        self, db_session: AsyncSession, tenant_id: uuid.UUID, supplier_id: uuid.UUID
    ) -> None:
        await _make_order(
            db_session, tenant_id, supplier_id, order_date=date(2026, 2, 1), po_number="PO-B"
        )
        await _make_order(
            db_session, tenant_id, supplier_id, order_date=date(2026, 1, 1), po_number="PO-A"
        )
        await _make_order(
            db_session, tenant_id, supplier_id, order_date=date(2026, 3, 1), po_number="PO-C"
        )

    async def test_sort_by_order_date_ascending(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, supplier_id)
        rows, _ = await _search(repo, tenant_id, sort="order_date")
        assert [r.order_date for r in rows] == [
            date(2026, 1, 1),
            date(2026, 2, 1),
            date(2026, 3, 1),
        ]

    async def test_sort_by_po_number_descending(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, supplier_id)
        rows, _ = await _search(repo, tenant_id, sort="-po_number")
        assert [r.po_number for r in rows] == ["PO-C", "PO-B", "PO-A"]

    async def test_sort_by_created_at_accepted(
        self,
        repo: PurchaseOrderRepository,
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
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        for i in range(5):
            await _make_order(db_session, tenant_id, supplier_id, po_number=f"P-{i}")

        rows, total = await _search(repo, tenant_id, sort="po_number", page=1, page_size=2)
        assert total == 5
        assert len(rows) == 2

    async def test_pages_do_not_overlap_and_cover_all_rows(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        for i in range(5):
            await _make_order(db_session, tenant_id, supplier_id, po_number=f"Q-{i}")

        seen_ids: set[uuid.UUID] = set()
        for page in (1, 2, 3):
            rows, _ = await _search(repo, tenant_id, sort="po_number", page=page, page_size=2)
            page_ids = {r.id for r in rows}
            assert not (page_ids & seen_ids), "pages overlapped"
            seen_ids |= page_ids
        assert len(seen_ids) == 5

    async def test_page_past_the_end_returns_empty(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_order(db_session, tenant_id, supplier_id)
        rows, total = await _search(repo, tenant_id, page=99, page_size=10)
        assert total == 1
        assert rows == []


class TestSearchTenantScoping:
    async def test_never_returns_rows_from_another_tenant(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        other_tenant = Tenant(name="Other Tenant PO", slug=f"other-po-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_supplier = await _make_supplier(db_session, other_tenant.id)

        mine = await _make_order(db_session, tenant_id, supplier_id, po_number="MINE-001")
        await _make_order(db_session, other_tenant.id, other_supplier.id, po_number="NOT-MINE-001")

        rows, total = await _search(repo, tenant_id)
        assert total == 1
        assert rows[0].id == mine.id


class TestAdd:
    async def test_stages_a_new_order(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = PurchaseOrder(
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            order_date=_ORDER_DATE,
            status=PurchaseOrderStatus.DRAFT,
            subtotal=Decimal("0"),
            discount_amount=Decimal("0"),
            taxable_amount=Decimal("0"),
            tax_amount=Decimal("0"),
            transport_charge=Decimal("0"),
            other_charge=Decimal("0"),
            round_off=Decimal("0"),
            total_amount=Decimal("0"),
        )
        await repo.add(order)
        await db_session.commit()

        found = await repo.get_by_id(order.id, tenant_id)
        assert found is not None
        assert found.supplier_id == supplier_id


def _make_item(
    tenant_id: uuid.UUID, purchase_order_id: uuid.UUID, line_number: int, **overrides: Any
) -> PurchaseOrderItem:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "purchase_order_id": purchase_order_id,
        "line_number": line_number,
        "quantity": Decimal("1.000"),
        "unit": "KG",
        "rate": Decimal("1.0000"),
    }
    defaults.update(overrides)
    return PurchaseOrderItem(**defaults)


class TestGetItemById:
    async def test_finds_item_scoped_to_order_and_tenant(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        item = _make_item(tenant_id, order.id, 1, description="Findable")
        db_session.add(item)
        await db_session.commit()

        found = await repo.get_item_by_id(item.id, order.id, tenant_id)
        assert found is not None
        assert found.description == "Findable"

    async def test_returns_none_for_a_different_order(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        other_order = await _make_order(db_session, tenant_id, supplier_id)
        item = _make_item(tenant_id, order.id, 1)
        db_session.add(item)
        await db_session.commit()

        assert await repo.get_item_by_id(item.id, other_order.id, tenant_id) is None

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        item = _make_item(tenant_id, order.id, 1)
        db_session.add(item)
        await db_session.commit()

        assert await repo.get_item_by_id(item.id, order.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        assert await repo.get_item_by_id(uuid.uuid4(), order.id, tenant_id) is None


class TestAllocateNextLineNumber:
    async def test_first_allocation_returns_one(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        line_number = await repo.allocate_next_line_number(order.id, tenant_id)
        await db_session.commit()
        assert line_number == 1

    async def test_sequential_allocations_increment(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        first = await repo.allocate_next_line_number(order.id, tenant_id)
        second = await repo.allocate_next_line_number(order.id, tenant_id)
        third = await repo.allocate_next_line_number(order.id, tenant_id)
        await db_session.commit()
        assert [first, second, third] == [1, 2, 3]

    async def test_number_is_never_reused_after_the_item_is_deleted(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        first = await repo.allocate_next_line_number(order.id, tenant_id)
        item = _make_item(tenant_id, order.id, first)
        db_session.add(item)
        await db_session.commit()

        await repo.delete_item(item)
        await db_session.commit()

        next_number = await repo.allocate_next_line_number(order.id, tenant_id)
        await db_session.commit()
        assert next_number == first + 1

    async def test_scoped_to_its_own_order(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order_a = await _make_order(db_session, tenant_id, supplier_id)
        order_b = await _make_order(db_session, tenant_id, supplier_id)
        await repo.allocate_next_line_number(order_a.id, tenant_id)
        await repo.allocate_next_line_number(order_a.id, tenant_id)
        first_on_b = await repo.allocate_next_line_number(order_b.id, tenant_id)
        await db_session.commit()
        assert first_on_b == 1


class TestSearchItems:
    async def test_returns_items_ordered_by_line_number_by_default(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        for line_number in (3, 1, 2):
            db_session.add(_make_item(tenant_id, order.id, line_number))
        await db_session.commit()

        items = await repo.search_items(order.id, tenant_id, q=None, sort="line_number")
        assert [i.line_number for i in items] == [1, 2, 3]

    async def test_scoped_to_order_and_tenant(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        other_order = await _make_order(db_session, tenant_id, supplier_id)
        item = _make_item(tenant_id, order.id, 1)
        db_session.add(item)
        db_session.add(_make_item(tenant_id, other_order.id, 1))
        await db_session.commit()

        items = await repo.search_items(order.id, tenant_id, q=None, sort="line_number")
        assert [i.id for i in items] == [item.id]

    async def test_q_matches_description_case_insensitively(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        target = _make_item(tenant_id, order.id, 1, description="Pomfret - Grade A")
        db_session.add(target)
        db_session.add(_make_item(tenant_id, order.id, 2, description="Sardine"))
        await db_session.commit()

        items = await repo.search_items(order.id, tenant_id, q="pomfret", sort="line_number")
        assert [i.id for i in items] == [target.id]

    async def test_blank_query_returns_everything(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        db_session.add(_make_item(tenant_id, order.id, 1))
        db_session.add(_make_item(tenant_id, order.id, 2))
        await db_session.commit()

        items = await repo.search_items(order.id, tenant_id, q="   ", sort="line_number")
        assert len(items) == 2

    async def test_sort_by_description_descending(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        db_session.add(_make_item(tenant_id, order.id, 1, description="Alpha"))
        db_session.add(_make_item(tenant_id, order.id, 2, description="Charlie"))
        db_session.add(_make_item(tenant_id, order.id, 3, description="Bravo"))
        await db_session.commit()

        items = await repo.search_items(order.id, tenant_id, q=None, sort="-description")
        assert [i.description for i in items] == ["Charlie", "Bravo", "Alpha"]


class TestSearchItemsAggregation:
    """search_items(q=None, sort="line_number") is what
    PurchaseOrderService._recalculate_purchase_order uses to fetch every
    item on an order before summing their totals - this exercises that
    exact call shape, distinct from TestSearchItems' filter/sort coverage."""

    async def test_returns_every_item_for_aggregation(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        db_session.add(_make_item(tenant_id, order.id, 1, quantity=Decimal("10.000")))
        db_session.add(_make_item(tenant_id, order.id, 2, quantity=Decimal("5.000")))
        db_session.add(_make_item(tenant_id, order.id, 3, quantity=Decimal("2.500")))
        await db_session.commit()

        items = await repo.search_items(order.id, tenant_id, q=None, sort="line_number")
        total_quantity = sum((i.quantity for i in items), Decimal("0"))
        assert total_quantity == Decimal("17.500")

    async def test_empty_order_aggregates_to_nothing(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        items = await repo.search_items(order.id, tenant_id, q=None, sort="line_number")
        assert items == []

    async def test_excludes_items_from_other_orders_from_aggregation(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        other_order = await _make_order(db_session, tenant_id, supplier_id)
        db_session.add(_make_item(tenant_id, order.id, 1, quantity=Decimal("10.000")))
        db_session.add(_make_item(tenant_id, other_order.id, 1, quantity=Decimal("999.000")))
        await db_session.commit()

        items = await repo.search_items(order.id, tenant_id, q=None, sort="line_number")
        assert [i.quantity for i in items] == [Decimal("10.000")]


class TestAddAndDeleteItem:
    async def test_add_item_stages_and_persists(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        item = _make_item(tenant_id, order.id, 1, description="New Item")
        await repo.add_item(item)
        await db_session.commit()

        found = await repo.get_item_by_id(item.id, order.id, tenant_id)
        assert found is not None
        assert found.description == "New Item"

    async def test_delete_item_hard_deletes_the_row(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        item = _make_item(tenant_id, order.id, 1)
        db_session.add(item)
        await db_session.commit()
        item_id = item.id

        await repo.delete_item(item)
        await db_session.commit()

        assert await repo.get_item_by_id(item_id, order.id, tenant_id) is None


class TestGetByIdForUpdate:
    async def test_finds_order_in_own_tenant(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id, remarks="Lockable")
        found = await repo.get_by_id_for_update(order.id, tenant_id)
        assert found is not None
        assert found.remarks == "Lockable"

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        assert await repo.get_by_id_for_update(order.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: PurchaseOrderRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id_for_update(uuid.uuid4(), tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id, deleted_at=datetime.now(UTC))
        assert await repo.get_by_id_for_update(order.id, tenant_id) is None

    async def test_mutations_on_the_locked_row_persist_after_commit(
        self,
        repo: PurchaseOrderRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        order = await _make_order(db_session, tenant_id, supplier_id)
        locked = await repo.get_by_id_for_update(order.id, tenant_id)
        assert locked is not None
        locked.po_number = "PO/2026-27/00001"
        locked.status = PurchaseOrderStatus.CONFIRMED
        await db_session.commit()

        refetched = await repo.get_by_id(order.id, tenant_id)
        assert refetched is not None
        assert refetched.po_number == "PO/2026-27/00001"
        assert refetched.status == PurchaseOrderStatus.CONFIRMED


class TestSequenceRow:
    """The confirm workflow's purchase order numbering counter -
    ensure_sequence_row (`INSERT ... ON CONFLICT DO NOTHING`) followed by
    get_sequence_for_update (`SELECT ... FOR UPDATE`). Mirrors
    PurchaseRepository's own TestSequenceRow exactly."""

    async def test_ensure_creates_a_row_starting_at_zero(
        self, repo: PurchaseOrderRepository, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "PO", "2026-27")
        sequence = await repo.get_sequence_for_update(tenant_id, "PO", "2026-27")
        assert sequence.last_number == 0

    async def test_ensure_is_idempotent_and_does_not_reset_an_existing_counter(
        self, repo: PurchaseOrderRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "PO", "2026-27")
        sequence = await repo.get_sequence_for_update(tenant_id, "PO", "2026-27")
        sequence.last_number += 1
        await db_session.commit()

        # A second ensure_sequence_row call (as confirm() makes on every
        # purchase order, not just the first per fiscal year) must not
        # clobber the counter back to zero.
        await repo.ensure_sequence_row(tenant_id, "PO", "2026-27")
        relocked = await repo.get_sequence_for_update(tenant_id, "PO", "2026-27")
        assert relocked.last_number == 1

    async def test_increment_persists_after_commit(
        self, repo: PurchaseOrderRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "PO", "2026-27")
        sequence = await repo.get_sequence_for_update(tenant_id, "PO", "2026-27")
        sequence.last_number += 1
        await db_session.commit()

        result = await db_session.execute(
            select(PurchaseOrderSequence).where(
                PurchaseOrderSequence.tenant_id == tenant_id,
                PurchaseOrderSequence.prefix == "PO",
                PurchaseOrderSequence.fiscal_year == "2026-27",
            )
        )
        assert result.scalar_one().last_number == 1

    async def test_different_fiscal_years_are_independent_counters(
        self, repo: PurchaseOrderRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "PO", "2025-26")
        early = await repo.get_sequence_for_update(tenant_id, "PO", "2025-26")
        early.last_number += 1
        await db_session.commit()

        await repo.ensure_sequence_row(tenant_id, "PO", "2026-27")
        late = await repo.get_sequence_for_update(tenant_id, "PO", "2026-27")
        assert late.last_number == 0

    async def test_different_tenants_are_independent_counters(
        self, repo: PurchaseOrderRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Purchase Order Sequence Tenant",
            slug=f"other-po-seq-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()

        await repo.ensure_sequence_row(tenant_id, "PO", "2026-27")
        mine = await repo.get_sequence_for_update(tenant_id, "PO", "2026-27")
        mine.last_number += 1
        await db_session.commit()

        await repo.ensure_sequence_row(other_tenant.id, "PO", "2026-27")
        theirs = await repo.get_sequence_for_update(other_tenant.id, "PO", "2026-27")
        assert theirs.last_number == 0
