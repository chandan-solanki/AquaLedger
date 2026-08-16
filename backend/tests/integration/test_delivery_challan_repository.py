import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Tenant
from app.modules.companies.models import Company
from app.modules.delivery_challans.constants import DeliveryChallanStatus
from app.modules.delivery_challans.models import DeliveryChallan, DeliveryChallanItem
from app.modules.delivery_challans.repository import DeliveryChallanRepository
from app.modules.fish.models import Fish
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.models import Invoice, InvoiceItem

_CHALLAN_DATE = date(2026, 8, 16)
_INVOICE_DATE = date(2026, 7, 1)


@pytest.fixture
async def repo(db_session: AsyncSession) -> DeliveryChallanRepository:
    return DeliveryChallanRepository(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - the seeded default tenant may already carry
    delivery challans from manual/exploratory testing, which would silently
    pollute any count-based assertion here."""
    tenant = Tenant(
        name="Delivery Challan Repo Test Tenant",
        slug=f"delivery-challan-repo-test-{uuid.uuid4().hex[:8]}",
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


async def _make_invoice(
    db_session: AsyncSession, tenant_id: uuid.UUID, company_id: uuid.UUID, **overrides: Any
) -> Invoice:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "company_id": company_id,
        "invoice_date": _INVOICE_DATE,
        "status": InvoiceStatus.ISSUED,
        "invoice_number": f"INV/2026-27/{uuid.uuid4().hex[:5]}",
        "subtotal": Decimal("0"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("0"),
        "tax_amount": Decimal("0"),
        "transport_charge": Decimal("0"),
        "other_charge": Decimal("0"),
        "round_off": Decimal("0"),
        "total_amount": Decimal("0"),
        "paid_amount": Decimal("0"),
        "balance_amount": Decimal("0"),
    }
    defaults.update(overrides)
    invoice = Invoice(**defaults)
    db_session.add(invoice)
    await db_session.commit()
    return invoice


async def _make_invoice_item(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
    fish_id: uuid.UUID,
    *,
    line_number: int = 1,
    **overrides: Any,
) -> InvoiceItem:
    # trip_catch_id is left NULL - it's nullable at the DB level, and these
    # tests only exercise DeliveryChallanRepository, never InvoiceService's
    # own item-creation validation (which is what actually requires it).
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "line_number": line_number,
        "fish_id": fish_id,
        "quantity": Decimal("100.000"),
        "unit": "kg",
        "rate": Decimal("100.0000"),
    }
    defaults.update(overrides)
    item = InvoiceItem(**defaults)
    db_session.add(item)
    await db_session.commit()
    return item


@pytest.fixture
async def invoice_item_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    company = await _make_company(db_session, tenant_id)
    fish = await _make_fish(db_session, tenant_id)
    invoice = await _make_invoice(db_session, tenant_id, company.id)
    item = await _make_invoice_item(db_session, tenant_id, invoice.id, fish.id)
    return item.id


async def _make_delivery_challan(
    db_session: AsyncSession, tenant_id: uuid.UUID, invoice_id: uuid.UUID, **overrides: Any
) -> DeliveryChallan:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "challan_date": _CHALLAN_DATE,
        "status": DeliveryChallanStatus.DRAFT,
    }
    defaults.update(overrides)
    challan = DeliveryChallan(**defaults)
    db_session.add(challan)
    await db_session.commit()
    return challan


@pytest.fixture
async def invoice_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    company = await _make_company(db_session, tenant_id)
    invoice = await _make_invoice(db_session, tenant_id, company.id)
    return invoice.id


def _make_challan_item(
    tenant_id: uuid.UUID,
    delivery_challan_id: uuid.UUID,
    invoice_item_id: uuid.UUID,
    line_number: int,
    **overrides: Any,
) -> DeliveryChallanItem:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "delivery_challan_id": delivery_challan_id,
        "invoice_item_id": invoice_item_id,
        "line_number": line_number,
        "quantity": Decimal("10.000"),
        "unit": "kg",
    }
    defaults.update(overrides)
    return DeliveryChallanItem(**defaults)


class TestGetById:
    async def test_finds_challan_in_own_tenant(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        challan = await _make_delivery_challan(
            db_session, tenant_id, invoice_id, remarks="Findable"
        )
        found = await repo.get_by_id(challan.id, tenant_id)
        assert found is not None
        assert found.remarks == "Findable"

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        challan = await _make_delivery_challan(db_session, tenant_id, invoice_id)
        assert await repo.get_by_id(challan.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: DeliveryChallanRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id(uuid.uuid4(), tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        challan = await _make_delivery_challan(
            db_session, tenant_id, invoice_id, deleted_at=datetime.now(UTC)
        )
        assert await repo.get_by_id(challan.id, tenant_id) is None


class TestGetByIdForUpdate:
    async def test_mutations_on_the_locked_row_persist_after_commit(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        challan = await _make_delivery_challan(db_session, tenant_id, invoice_id)
        locked = await repo.get_by_id_for_update(challan.id, tenant_id)
        assert locked is not None
        locked.challan_number = "DC/2026-27/00001"
        locked.status = DeliveryChallanStatus.DISPATCHED
        await db_session.commit()

        refetched = await repo.get_by_id(challan.id, tenant_id)
        assert refetched is not None
        assert refetched.challan_number == "DC/2026-27/00001"
        assert refetched.status == DeliveryChallanStatus.DISPATCHED

    async def test_returns_none_for_unknown_id(
        self, repo: DeliveryChallanRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id_for_update(uuid.uuid4(), tenant_id) is None


class TestSearchFilters:
    async def test_filters_by_status(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        await _make_delivery_challan(
            db_session, tenant_id, invoice_id, status=DeliveryChallanStatus.DRAFT
        )
        dispatched = await _make_delivery_challan(
            db_session, tenant_id, invoice_id, status=DeliveryChallanStatus.DISPATCHED
        )

        rows, total = await repo.search(
            tenant_id,
            q=None,
            status=DeliveryChallanStatus.DISPATCHED,
            invoice_id=None,
            challan_date_from=None,
            challan_date_to=None,
            sort="-created_at",
            page=1,
            page_size=50,
        )
        assert total == 1
        assert rows[0].id == dispatched.id

    async def test_filters_by_invoice_id(
        self, repo: DeliveryChallanRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        invoice_a = await _make_invoice(db_session, tenant_id, company.id)
        invoice_b = await _make_invoice(db_session, tenant_id, company.id)
        target = await _make_delivery_challan(db_session, tenant_id, invoice_a.id)
        await _make_delivery_challan(db_session, tenant_id, invoice_b.id)

        rows, total = await repo.search(
            tenant_id,
            q=None,
            status=None,
            invoice_id=invoice_a.id,
            challan_date_from=None,
            challan_date_to=None,
            sort="-created_at",
            page=1,
            page_size=50,
        )
        assert total == 1
        assert rows[0].id == target.id

    async def test_filters_by_challan_date_range(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        in_range = await _make_delivery_challan(
            db_session, tenant_id, invoice_id, challan_date=date(2026, 6, 15)
        )
        await _make_delivery_challan(
            db_session, tenant_id, invoice_id, challan_date=date(2026, 1, 1)
        )

        rows, total = await repo.search(
            tenant_id,
            q=None,
            status=None,
            invoice_id=None,
            challan_date_from=date(2026, 6, 1),
            challan_date_to=date(2026, 6, 30),
            sort="-created_at",
            page=1,
            page_size=50,
        )
        assert total == 1
        assert rows[0].id == in_range.id

    async def test_excludes_soft_deleted_from_results(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        await _make_delivery_challan(
            db_session, tenant_id, invoice_id, deleted_at=datetime.now(UTC)
        )
        rows, total = await repo.search(
            tenant_id,
            q=None,
            status=None,
            invoice_id=None,
            challan_date_from=None,
            challan_date_to=None,
            sort="-created_at",
            page=1,
            page_size=50,
        )
        assert total == 0
        assert rows == []


class TestSearchQuery:
    async def test_matches_challan_number_case_insensitively(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        target = await _make_delivery_challan(
            db_session, tenant_id, invoice_id, challan_number="DC/2026-27/00042"
        )
        await _make_delivery_challan(db_session, tenant_id, invoice_id)  # noise, no number

        rows, total = await repo.search(
            tenant_id,
            q="dc/2026-27",
            status=None,
            invoice_id=None,
            challan_date_from=None,
            challan_date_to=None,
            sort="-created_at",
            page=1,
            page_size=50,
        )
        assert total == 1
        assert rows[0].id == target.id

    async def test_blank_query_returns_everything(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        await _make_delivery_challan(db_session, tenant_id, invoice_id)
        await _make_delivery_challan(db_session, tenant_id, invoice_id)

        rows, total = await repo.search(
            tenant_id,
            q="   ",
            status=None,
            invoice_id=None,
            challan_date_from=None,
            challan_date_to=None,
            sort="-created_at",
            page=1,
            page_size=50,
        )
        assert total == 2


class TestSearchSorting:
    async def test_sort_by_challan_date_ascending(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        await _make_delivery_challan(
            db_session, tenant_id, invoice_id, challan_date=date(2026, 2, 1)
        )
        await _make_delivery_challan(
            db_session, tenant_id, invoice_id, challan_date=date(2026, 1, 1)
        )
        await _make_delivery_challan(
            db_session, tenant_id, invoice_id, challan_date=date(2026, 3, 1)
        )

        rows, _ = await repo.search(
            tenant_id,
            q=None,
            status=None,
            invoice_id=None,
            challan_date_from=None,
            challan_date_to=None,
            sort="challan_date",
            page=1,
            page_size=50,
        )
        assert [r.challan_date for r in rows] == [
            date(2026, 1, 1),
            date(2026, 2, 1),
            date(2026, 3, 1),
        ]


class TestSearchTenantScoping:
    async def test_never_returns_rows_from_another_tenant(
        self, repo: DeliveryChallanRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        mine = await _make_delivery_challan(db_session, tenant_id, invoice.id)

        other_tenant = Tenant(name="Other DC Tenant", slug=f"other-dc-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_company = await _make_company(db_session, other_tenant.id)
        other_invoice = await _make_invoice(db_session, other_tenant.id, other_company.id)
        await _make_delivery_challan(db_session, other_tenant.id, other_invoice.id)

        rows, total = await repo.search(
            tenant_id,
            q=None,
            status=None,
            invoice_id=None,
            challan_date_from=None,
            challan_date_to=None,
            sort="-created_at",
            page=1,
            page_size=50,
        )
        assert total == 1
        assert rows[0].id == mine.id


class TestAdd:
    async def test_stages_a_new_challan(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        challan = DeliveryChallan(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            challan_date=_CHALLAN_DATE,
            status=DeliveryChallanStatus.DRAFT,
        )
        await repo.add(challan)
        await db_session.commit()

        found = await repo.get_by_id(challan.id, tenant_id)
        assert found is not None
        assert found.invoice_id == invoice_id


class TestGetItemById:
    async def test_finds_item_scoped_to_challan_and_tenant(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        invoice_item_id: uuid.UUID,
    ) -> None:
        challan = await _make_delivery_challan(db_session, tenant_id, invoice_id)
        item = _make_challan_item(tenant_id, challan.id, invoice_item_id, 1)
        db_session.add(item)
        await db_session.commit()

        found = await repo.get_item_by_id(item.id, challan.id, tenant_id)
        assert found is not None
        assert found.quantity == Decimal("10.000")

    async def test_returns_none_for_a_different_challan(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        invoice_item_id: uuid.UUID,
    ) -> None:
        challan = await _make_delivery_challan(db_session, tenant_id, invoice_id)
        other_challan = await _make_delivery_challan(db_session, tenant_id, invoice_id)
        item = _make_challan_item(tenant_id, challan.id, invoice_item_id, 1)
        db_session.add(item)
        await db_session.commit()

        assert await repo.get_item_by_id(item.id, other_challan.id, tenant_id) is None

    async def test_returns_none_for_unknown_id(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        challan = await _make_delivery_challan(db_session, tenant_id, invoice_id)
        assert await repo.get_item_by_id(uuid.uuid4(), challan.id, tenant_id) is None


class TestAllocateNextLineNumber:
    async def test_first_allocation_returns_one(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        challan = await _make_delivery_challan(db_session, tenant_id, invoice_id)
        line_number = await repo.allocate_next_line_number(challan.id, tenant_id)
        await db_session.commit()
        assert line_number == 1

    async def test_sequential_allocations_increment(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        challan = await _make_delivery_challan(db_session, tenant_id, invoice_id)
        first = await repo.allocate_next_line_number(challan.id, tenant_id)
        second = await repo.allocate_next_line_number(challan.id, tenant_id)
        await db_session.commit()
        assert [first, second] == [1, 2]

    async def test_number_is_never_reused_after_the_item_is_deleted(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        invoice_item_id: uuid.UUID,
    ) -> None:
        challan = await _make_delivery_challan(db_session, tenant_id, invoice_id)
        first = await repo.allocate_next_line_number(challan.id, tenant_id)
        item = _make_challan_item(tenant_id, challan.id, invoice_item_id, first)
        db_session.add(item)
        await db_session.commit()

        await repo.delete_item(item)
        await db_session.commit()

        next_number = await repo.allocate_next_line_number(challan.id, tenant_id)
        await db_session.commit()
        assert next_number == first + 1


class TestSearchItems:
    async def test_returns_items_ordered_by_line_number_by_default(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        invoice_item_id: uuid.UUID,
    ) -> None:
        challan = await _make_delivery_challan(db_session, tenant_id, invoice_id)
        for line_number in (3, 1, 2):
            db_session.add(_make_challan_item(tenant_id, challan.id, invoice_item_id, line_number))
        await db_session.commit()

        items = await repo.search_items(challan.id, tenant_id, sort="line_number")
        assert [i.line_number for i in items] == [1, 2, 3]

    async def test_scoped_to_challan_and_tenant(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        invoice_item_id: uuid.UUID,
    ) -> None:
        challan = await _make_delivery_challan(db_session, tenant_id, invoice_id)
        other_challan = await _make_delivery_challan(db_session, tenant_id, invoice_id)
        item = _make_challan_item(tenant_id, challan.id, invoice_item_id, 1)
        db_session.add(item)
        db_session.add(_make_challan_item(tenant_id, other_challan.id, invoice_item_id, 1))
        await db_session.commit()

        items = await repo.search_items(challan.id, tenant_id, sort="line_number")
        assert [i.id for i in items] == [item.id]


class TestAddAndDeleteItem:
    async def test_add_item_stages_and_persists(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        invoice_item_id: uuid.UUID,
    ) -> None:
        challan = await _make_delivery_challan(db_session, tenant_id, invoice_id)
        item = _make_challan_item(
            tenant_id, challan.id, invoice_item_id, 1, quantity=Decimal("25.000")
        )
        await repo.add_item(item)
        await db_session.commit()

        found = await repo.get_item_by_id(item.id, challan.id, tenant_id)
        assert found is not None
        assert found.quantity == Decimal("25.000")

    async def test_delete_item_hard_deletes_the_row(
        self,
        repo: DeliveryChallanRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        invoice_item_id: uuid.UUID,
    ) -> None:
        challan = await _make_delivery_challan(db_session, tenant_id, invoice_id)
        item = _make_challan_item(tenant_id, challan.id, invoice_item_id, 1)
        db_session.add(item)
        await db_session.commit()
        item_id = item.id

        await repo.delete_item(item)
        await db_session.commit()

        assert await repo.get_item_by_id(item_id, challan.id, tenant_id) is None


class TestSumDeliveredQuantityForInvoiceItem:
    """DeliveryChallanRepository.sum_delivered_quantity_for_invoice_item -
    the write-time over-delivery guard's single-item aggregation."""

    async def test_sums_across_draft_dispatched_and_delivered_challans(
        self, repo: DeliveryChallanRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        fish = await _make_fish(db_session, tenant_id)
        item = await _make_invoice_item(db_session, tenant_id, invoice.id, fish.id)

        draft = await _make_delivery_challan(db_session, tenant_id, invoice.id)
        dispatched = await _make_delivery_challan(
            db_session, tenant_id, invoice.id, status=DeliveryChallanStatus.DISPATCHED
        )
        delivered = await _make_delivery_challan(
            db_session, tenant_id, invoice.id, status=DeliveryChallanStatus.DELIVERED
        )
        for challan, qty in ((draft, "10.000"), (dispatched, "20.000"), (delivered, "30.000")):
            db_session.add(
                _make_challan_item(tenant_id, challan.id, item.id, 1, quantity=Decimal(qty))
            )
        await db_session.commit()

        total = await repo.sum_delivered_quantity_for_invoice_item(item.id, tenant_id)
        assert total == Decimal("60.000")

    async def test_excludes_cancelled_challans(
        self, repo: DeliveryChallanRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        fish = await _make_fish(db_session, tenant_id)
        item = await _make_invoice_item(db_session, tenant_id, invoice.id, fish.id)

        cancelled = await _make_delivery_challan(
            db_session, tenant_id, invoice.id, status=DeliveryChallanStatus.CANCELLED
        )
        db_session.add(
            _make_challan_item(tenant_id, cancelled.id, item.id, 1, quantity=Decimal("50.000"))
        )
        await db_session.commit()

        total = await repo.sum_delivered_quantity_for_invoice_item(item.id, tenant_id)
        assert total == Decimal("0")

    async def test_excludes_soft_deleted_challans(
        self, repo: DeliveryChallanRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        fish = await _make_fish(db_session, tenant_id)
        item = await _make_invoice_item(db_session, tenant_id, invoice.id, fish.id)

        deleted = await _make_delivery_challan(
            db_session, tenant_id, invoice.id, deleted_at=datetime.now(UTC)
        )
        db_session.add(
            _make_challan_item(tenant_id, deleted.id, item.id, 1, quantity=Decimal("50.000"))
        )
        await db_session.commit()

        total = await repo.sum_delivered_quantity_for_invoice_item(item.id, tenant_id)
        assert total == Decimal("0")

    async def test_exclude_item_id_omits_its_own_prior_contribution(
        self, repo: DeliveryChallanRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        fish = await _make_fish(db_session, tenant_id)
        item = await _make_invoice_item(db_session, tenant_id, invoice.id, fish.id)

        challan = await _make_delivery_challan(db_session, tenant_id, invoice.id)
        challan_item = _make_challan_item(
            tenant_id, challan.id, item.id, 1, quantity=Decimal("40.000")
        )
        db_session.add(challan_item)
        await db_session.commit()

        total_including = await repo.sum_delivered_quantity_for_invoice_item(item.id, tenant_id)
        assert total_including == Decimal("40.000")

        total_excluding = await repo.sum_delivered_quantity_for_invoice_item(
            item.id, tenant_id, exclude_item_id=challan_item.id
        )
        assert total_excluding == Decimal("0")

    async def test_zero_when_nothing_delivered(
        self, repo: DeliveryChallanRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.sum_delivered_quantity_for_invoice_item(
            uuid.uuid4(), tenant_id
        ) == Decimal("0")


class TestSumDeliveredByInvoiceItems:
    """DeliveryChallanRepository.sum_delivered_by_invoice_items - the
    batched aggregation used to avoid N+1 across an invoice's items."""

    async def test_aggregates_per_item_in_one_query(
        self, repo: DeliveryChallanRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        fish = await _make_fish(db_session, tenant_id)
        item_a = await _make_invoice_item(db_session, tenant_id, invoice.id, fish.id, line_number=1)
        item_b = await _make_invoice_item(db_session, tenant_id, invoice.id, fish.id, line_number=2)

        challan = await _make_delivery_challan(db_session, tenant_id, invoice.id)
        db_session.add(
            _make_challan_item(tenant_id, challan.id, item_a.id, 1, quantity=Decimal("15.000"))
        )
        db_session.add(
            _make_challan_item(tenant_id, challan.id, item_b.id, 2, quantity=Decimal("25.000"))
        )
        await db_session.commit()

        totals = await repo.sum_delivered_by_invoice_items([item_a.id, item_b.id], tenant_id)
        assert totals == {item_a.id: Decimal("15.000"), item_b.id: Decimal("25.000")}

    async def test_item_with_nothing_delivered_is_absent_from_the_result(
        self, repo: DeliveryChallanRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        fish = await _make_fish(db_session, tenant_id)
        item = await _make_invoice_item(db_session, tenant_id, invoice.id, fish.id)

        totals = await repo.sum_delivered_by_invoice_items([item.id], tenant_id)
        assert totals == {}

    async def test_excludes_cancelled_challans(
        self, repo: DeliveryChallanRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        fish = await _make_fish(db_session, tenant_id)
        item = await _make_invoice_item(db_session, tenant_id, invoice.id, fish.id)

        cancelled = await _make_delivery_challan(
            db_session, tenant_id, invoice.id, status=DeliveryChallanStatus.CANCELLED
        )
        db_session.add(
            _make_challan_item(tenant_id, cancelled.id, item.id, 1, quantity=Decimal("99.000"))
        )
        await db_session.commit()

        totals = await repo.sum_delivered_by_invoice_items([item.id], tenant_id)
        assert totals == {}

    async def test_empty_input_list_returns_empty_dict_without_querying(
        self, repo: DeliveryChallanRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.sum_delivered_by_invoice_items([], tenant_id) == {}


class TestSequenceRow:
    async def test_ensure_creates_a_row_starting_at_zero(
        self, repo: DeliveryChallanRepository, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "DC", "2026-27")
        sequence = await repo.get_sequence_for_update(tenant_id, "DC", "2026-27")
        assert sequence.last_number == 0

    async def test_ensure_is_idempotent_and_does_not_reset_an_existing_counter(
        self, repo: DeliveryChallanRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "DC", "2026-27")
        sequence = await repo.get_sequence_for_update(tenant_id, "DC", "2026-27")
        sequence.last_number += 1
        await db_session.commit()

        await repo.ensure_sequence_row(tenant_id, "DC", "2026-27")
        relocked = await repo.get_sequence_for_update(tenant_id, "DC", "2026-27")
        assert relocked.last_number == 1

    async def test_different_fiscal_years_are_independent_counters(
        self, repo: DeliveryChallanRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "DC", "2025-26")
        early = await repo.get_sequence_for_update(tenant_id, "DC", "2025-26")
        early.last_number += 1
        await db_session.commit()

        await repo.ensure_sequence_row(tenant_id, "DC", "2026-27")
        late = await repo.get_sequence_for_update(tenant_id, "DC", "2026-27")
        assert late.last_number == 0
