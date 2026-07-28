import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Tenant
from app.modules.boats.models import Boat
from app.modules.companies.models import Company
from app.modules.dashboard.repository import DashboardRepository
from app.modules.fish.models import Fish
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.models import Invoice, InvoiceItem
from app.modules.payments.constants import PaymentStatus
from app.modules.payments.models import Payment
from app.modules.purchase.constants import PurchaseStatus
from app.modules.purchase.models import PurchaseBill
from app.modules.supplier_payments.constants import SupplierPaymentStatus
from app.modules.supplier_payments.models import SupplierPayment
from app.modules.suppliers.models import Supplier
from app.modules.trip_catches.models import TripCatch
from app.modules.trips.constants import TripStatus, TripType
from app.modules.trips.models import Trip

_TODAY = date(2026, 7, 28)
_MONTH_START = _TODAY.replace(day=1)
_NOW = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)
_STALE_CUTOFF = _NOW - timedelta(days=3)


@pytest.fixture
async def repo(db_session: AsyncSession) -> DashboardRepository:
    return DashboardRepository(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - isolates every aggregate assertion here from
    the seeded default tenant's own data and from other tests in this file."""
    tenant = Tenant(
        name="Dashboard Repo Test Tenant", slug=f"dash-repo-test-{uuid.uuid4().hex[:8]}"
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant.id


@pytest.fixture
async def other_tenant_id(db_session: AsyncSession) -> uuid.UUID:
    tenant = Tenant(name="Other Tenant", slug=f"dash-repo-other-{uuid.uuid4().hex[:8]}")
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
        "outstanding_amount": Decimal("0"),
    }
    defaults.update(overrides)
    company = Company(**defaults)
    db_session.add(company)
    await db_session.commit()
    return company


async def _make_supplier(
    db_session: AsyncSession, tenant_id: uuid.UUID, **overrides: Any
) -> Supplier:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "code": f"SUP-{uuid.uuid4().hex[:8]}",
        "name": f"Supplier {uuid.uuid4().hex[:8]}",
        "outstanding_amount": Decimal("0"),
    }
    defaults.update(overrides)
    supplier = Supplier(**defaults)
    db_session.add(supplier)
    await db_session.commit()
    return supplier


async def _make_boat(db_session: AsyncSession, tenant_id: uuid.UUID, **overrides: Any) -> Boat:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "code": f"B-{uuid.uuid4().hex[:8]}",
        "name": f"Boat {uuid.uuid4().hex[:8]}",
        "registration_number": f"REG-{uuid.uuid4().hex[:8]}",
        "is_active": True,
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
        "departure_datetime": datetime(2026, 7, 27, 4, 0, tzinfo=UTC),
        "status": TripStatus.PLANNED,
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
        "unit": "kg",
    }
    defaults.update(overrides)
    fish = Fish(**defaults)
    db_session.add(fish)
    await db_session.commit()
    return fish


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
        "sold_quantity": Decimal("0"),
        "waste_quantity": Decimal("0"),
        "landing_date": _TODAY,
    }
    defaults.update(overrides)
    trip_catch = TripCatch(**defaults)
    db_session.add(trip_catch)
    await db_session.commit()
    return trip_catch


async def _make_invoice(
    db_session: AsyncSession, tenant_id: uuid.UUID, company_id: uuid.UUID, **overrides: Any
) -> Invoice:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "company_id": company_id,
        "invoice_date": _TODAY,
        "status": InvoiceStatus.ISSUED,
        "subtotal": Decimal("0"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("0"),
        "tax_amount": Decimal("0"),
        "transport_charge": Decimal("0"),
        "other_charge": Decimal("0"),
        "round_off": Decimal("0"),
        "total_amount": Decimal("1000.00"),
        "paid_amount": Decimal("0"),
        "balance_amount": Decimal("1000.00"),
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
    **overrides: Any,
) -> InvoiceItem:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "fish_id": fish_id,
        "line_number": 1,
        "quantity": Decimal("100.000"),
        "unit": "kg",
        "rate": Decimal("100.0000"),
        "discount_percent": Decimal("0"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("10000.00"),
        "tax_rate": Decimal("0"),
        "tax_amount": Decimal("0"),
        "line_total": Decimal("10000.00"),
    }
    defaults.update(overrides)
    item = InvoiceItem(**defaults)
    db_session.add(item)
    await db_session.commit()
    return item


async def _make_payment(
    db_session: AsyncSession, tenant_id: uuid.UUID, company_id: uuid.UUID, **overrides: Any
) -> Payment:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "company_id": company_id,
        "payment_date": _TODAY,
        "payment_method": "cash",
        "amount": Decimal("500.00"),
        "allocated_amount": Decimal("0"),
        "unallocated_amount": Decimal("500.00"),
        "status": PaymentStatus.POSTED,
    }
    defaults.update(overrides)
    payment = Payment(**defaults)
    db_session.add(payment)
    await db_session.commit()
    return payment


async def _make_purchase_bill(
    db_session: AsyncSession, tenant_id: uuid.UUID, supplier_id: uuid.UUID, **overrides: Any
) -> PurchaseBill:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "supplier_id": supplier_id,
        "bill_date": _TODAY,
        "status": PurchaseStatus.POSTED,
        "subtotal": Decimal("0"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("0"),
        "tax_amount": Decimal("0"),
        "transport_charge": Decimal("0"),
        "other_charge": Decimal("0"),
        "round_off": Decimal("0"),
        "total_amount": Decimal("800.00"),
        "paid_amount": Decimal("0"),
        "balance_amount": Decimal("800.00"),
    }
    defaults.update(overrides)
    bill = PurchaseBill(**defaults)
    db_session.add(bill)
    await db_session.commit()
    return bill


async def _make_supplier_payment(
    db_session: AsyncSession, tenant_id: uuid.UUID, supplier_id: uuid.UUID, **overrides: Any
) -> SupplierPayment:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "supplier_id": supplier_id,
        "payment_date": _TODAY,
        "payment_method": "cash",
        "amount": Decimal("300.00"),
        "allocated_amount": Decimal("0"),
        "unallocated_amount": Decimal("300.00"),
        "status": SupplierPaymentStatus.POSTED,
    }
    defaults.update(overrides)
    payment = SupplierPayment(**defaults)
    db_session.add(payment)
    await db_session.commit()
    return payment


class TestInvoiceAggregates:
    async def test_todays_and_monthly_sales_exclude_draft_and_cancelled(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        await _make_invoice(
            db_session, tenant_id, company.id, invoice_date=_TODAY, total_amount=Decimal("100.00")
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            invoice_date=_TODAY,
            total_amount=Decimal("999.00"),
            status=InvoiceStatus.DRAFT,
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            invoice_date=_TODAY,
            total_amount=Decimal("999.00"),
            status=InvoiceStatus.CANCELLED,
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            invoice_date=_TODAY - timedelta(days=5),
            total_amount=Decimal("50.00"),
        )

        agg = await repo.get_invoice_aggregates(
            tenant_id, today=_TODAY, month_start=_MONTH_START, stale_draft_cutoff=_STALE_CUTOFF
        )
        assert agg.todays_sales == Decimal("100.00")
        assert agg.monthly_sales == Decimal("150.00")

    async def test_draft_count_and_stale_draft_count(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        fresh_draft = await _make_invoice(
            db_session, tenant_id, company.id, status=InvoiceStatus.DRAFT
        )
        stale_draft = await _make_invoice(
            db_session, tenant_id, company.id, status=InvoiceStatus.DRAFT
        )
        # created_at has a server default - backdate it directly for the
        # "older than threshold" assertion.
        stale_draft.created_at = _STALE_CUTOFF - timedelta(days=1)
        fresh_draft.created_at = _NOW
        await db_session.commit()

        agg = await repo.get_invoice_aggregates(
            tenant_id, today=_TODAY, month_start=_MONTH_START, stale_draft_cutoff=_STALE_CUTOFF
        )
        assert agg.draft_count == 2
        assert agg.stale_draft_count == 1

    async def test_overdue_count_requires_open_status_past_due_date_and_balance(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        # Overdue: issued, due in the past, balance outstanding.
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            status=InvoiceStatus.ISSUED,
            due_date=_TODAY - timedelta(days=1),
            balance_amount=Decimal("100.00"),
        )
        # Not overdue: fully paid (balance zero).
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            status=InvoiceStatus.PAID,
            due_date=_TODAY - timedelta(days=1),
            balance_amount=Decimal("0"),
        )
        # Not overdue: due date in the future.
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            status=InvoiceStatus.ISSUED,
            due_date=_TODAY + timedelta(days=5),
            balance_amount=Decimal("100.00"),
        )

        agg = await repo.get_invoice_aggregates(
            tenant_id, today=_TODAY, month_start=_MONTH_START, stale_draft_cutoff=_STALE_CUTOFF
        )
        assert agg.overdue_count == 1
        assert agg.overdue_amount == Decimal("100.00")

    async def test_issued_this_month_count_uses_issued_at(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            status=InvoiceStatus.ISSUED,
            issued_at=datetime(2026, 7, 5, tzinfo=UTC),
        )
        await _make_invoice(db_session, tenant_id, company.id, status=InvoiceStatus.DRAFT)

        agg = await repo.get_invoice_aggregates(
            tenant_id, today=_TODAY, month_start=_MONTH_START, stale_draft_cutoff=_STALE_CUTOFF
        )
        assert agg.issued_this_month_count == 1

    async def test_isolated_by_tenant(
        self,
        repo: DashboardRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        other_tenant_id: uuid.UUID,
    ) -> None:
        other_company = await _make_company(db_session, other_tenant_id)
        await _make_invoice(
            db_session, other_tenant_id, other_company.id, total_amount=Decimal("99999.00")
        )

        agg = await repo.get_invoice_aggregates(
            tenant_id, today=_TODAY, month_start=_MONTH_START, stale_draft_cutoff=_STALE_CUTOFF
        )
        assert agg.todays_sales == Decimal("0")
        assert agg.monthly_sales == Decimal("0")


class TestPaymentAggregates:
    async def test_customer_payments_today_only_counts_posted(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        await _make_payment(
            db_session, tenant_id, company.id, amount=Decimal("500.00"), status=PaymentStatus.POSTED
        )
        await _make_payment(
            db_session, tenant_id, company.id, amount=Decimal("777.00"), status=PaymentStatus.DRAFT
        )
        await _make_payment(
            db_session,
            tenant_id,
            company.id,
            amount=Decimal("111.00"),
            status=PaymentStatus.POSTED,
            payment_date=_TODAY - timedelta(days=1),
        )

        agg = await repo.get_payment_aggregates(
            tenant_id, today=_TODAY, stale_draft_cutoff=_STALE_CUTOFF
        )
        assert agg.customer_payments_today == Decimal("500.00")
        assert agg.draft_count == 1


class TestBoatAggregates:
    async def test_active_maintenance_and_expiry_counts(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await _make_boat(db_session, tenant_id, is_active=True)
        await _make_boat(db_session, tenant_id, is_active=False)
        await _make_boat(
            db_session,
            tenant_id,
            is_active=True,
            license_expiry=_TODAY + timedelta(days=10),
        )
        await _make_boat(
            db_session,
            tenant_id,
            is_active=True,
            insurance_expiry=_TODAY + timedelta(days=45),  # outside the 30-day window
        )

        agg = await repo.get_boat_aggregates(
            tenant_id, today=_TODAY, expiry_window_end=_TODAY + timedelta(days=30)
        )
        assert agg.active_count == 3
        assert agg.maintenance_count == 1
        assert agg.license_expiring_count == 1
        assert agg.insurance_expiring_count == 0


class TestTripAggregates:
    async def test_trips_today_active_completed_and_boats_at_sea(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        boat_a = await _make_boat(db_session, tenant_id)
        boat_b = await _make_boat(db_session, tenant_id)
        await _make_trip(
            db_session,
            tenant_id,
            boat_a.id,
            status=TripStatus.DEPARTED,
            departure_datetime=datetime(2026, 7, 28, 5, 0, tzinfo=UTC),
        )
        await _make_trip(
            db_session,
            tenant_id,
            boat_b.id,
            status=TripStatus.RETURNED,
            departure_datetime=datetime(2026, 7, 20, 5, 0, tzinfo=UTC),
            actual_return_datetime=datetime(2026, 7, 28, 9, 0, tzinfo=UTC),
        )

        agg = await repo.get_trip_aggregates(tenant_id, today=_TODAY)
        assert agg.trips_today == 1
        assert agg.trips_active == 1
        assert agg.trips_completed_today == 1
        assert agg.boats_at_sea == 1


class TestCatchAndOutstanding:
    async def test_todays_catch_quantity_sums_only_todays_landings(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        boat = await _make_boat(db_session, tenant_id)
        trip = await _make_trip(db_session, tenant_id, boat.id)
        fish = await _make_fish(db_session, tenant_id)
        await _make_trip_catch(
            db_session, tenant_id, trip.id, fish.id, quantity_caught=Decimal("100.000")
        )
        await _make_trip_catch(
            db_session,
            tenant_id,
            trip.id,
            fish.id,
            quantity_caught=Decimal("50.000"),
            available_quantity=Decimal("50.000"),
            landing_date=_TODAY - timedelta(days=1),
        )

        quantity = await repo.get_todays_catch_quantity(tenant_id, today=_TODAY)
        assert quantity == Decimal("100.000")

    async def test_customer_and_supplier_outstanding_sum_cached_columns(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await _make_company(db_session, tenant_id, outstanding_amount=Decimal("1000.00"))
        await _make_company(db_session, tenant_id, outstanding_amount=Decimal("500.00"))
        await _make_supplier(db_session, tenant_id, outstanding_amount=Decimal("250.00"))

        customer_outstanding = await repo.get_customer_outstanding(tenant_id)
        supplier_outstanding = await repo.get_supplier_outstanding(tenant_id)
        assert customer_outstanding == Decimal("1500.00")
        assert supplier_outstanding == Decimal("250.00")


class TestPurchaseBillAggregates:
    async def test_posted_this_month_and_overdue(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier = await _make_supplier(db_session, tenant_id)
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            status=PurchaseStatus.POSTED,
            posted_at=datetime(2026, 7, 10, tzinfo=UTC),
        )
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            status=PurchaseStatus.POSTED,
            due_date=_TODAY - timedelta(days=2),
            balance_amount=Decimal("400.00"),
        )

        agg = await repo.get_purchase_bill_aggregates(
            tenant_id, today=_TODAY, month_start=_MONTH_START
        )
        assert agg.posted_this_month_count == 1
        assert agg.overdue_count == 1
        assert agg.overdue_amount == Decimal("400.00")

    async def test_supplier_payments_today_only_counts_posted(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier = await _make_supplier(db_session, tenant_id)
        await _make_supplier_payment(
            db_session,
            tenant_id,
            supplier.id,
            amount=Decimal("300.00"),
            status=SupplierPaymentStatus.POSTED,
        )
        await _make_supplier_payment(
            db_session,
            tenant_id,
            supplier.id,
            amount=Decimal("999.00"),
            status=SupplierPaymentStatus.DRAFT,
        )

        total = await repo.get_supplier_payments_today(tenant_id, today=_TODAY)
        assert total == Decimal("300.00")


class TestRecentActivity:
    async def test_recent_invoices_orders_newest_first_and_respects_limit(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id, name="Konkan Seafoods")
        older = await _make_invoice(db_session, tenant_id, company.id, invoice_number="INV-1")
        newer = await _make_invoice(db_session, tenant_id, company.id, invoice_number="INV-2")
        older.created_at = _NOW - timedelta(hours=2)
        newer.created_at = _NOW - timedelta(hours=1)
        await db_session.commit()

        rows = await repo.recent_invoices(tenant_id, limit=10)
        assert [row.reference for row in rows] == ["INV-2", "INV-1"]
        assert rows[0].title == "Invoice to Konkan Seafoods"

    async def test_recent_invoices_respects_limit(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        for i in range(15):
            await _make_invoice(db_session, tenant_id, company.id, invoice_number=f"INV-{i}")

        rows = await repo.recent_invoices(tenant_id, limit=10)
        assert len(rows) == 10


class TestMonthlySalesChart:
    async def test_groups_by_month_and_excludes_draft_and_cancelled(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        await _make_invoice(
            db_session, tenant_id, company.id, invoice_date=_TODAY, total_amount=Decimal("100.00")
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            invoice_date=_TODAY,
            total_amount=Decimal("999.00"),
            status=InvoiceStatus.DRAFT,
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            invoice_date=date(2026, 6, 15),
            total_amount=Decimal("50.00"),
        )

        by_month = await repo.get_monthly_sales_by_month(tenant_id, earliest_month=date(2026, 1, 1))

        assert by_month[date(2026, 7, 1)] == (Decimal("100.00"), 1)
        assert by_month[date(2026, 6, 1)] == (Decimal("50.00"), 1)

    async def test_months_before_earliest_are_excluded(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        await _make_invoice(db_session, tenant_id, company.id, invoice_date=date(2025, 1, 1))

        by_month = await repo.get_monthly_sales_by_month(tenant_id, earliest_month=date(2026, 1, 1))
        assert date(2025, 1, 1) not in by_month


class TestMonthlyPurchasesChart:
    async def test_groups_by_bill_date_and_excludes_draft_and_cancelled(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier = await _make_supplier(db_session, tenant_id)
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            bill_date=_TODAY,
            total_amount=Decimal("800.00"),
            status=PurchaseStatus.POSTED,
        )
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            bill_date=_TODAY,
            total_amount=Decimal("999.00"),
            status=PurchaseStatus.DRAFT,
        )
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            bill_date=_TODAY,
            total_amount=Decimal("111.00"),
            status=PurchaseStatus.CANCELLED,
        )

        by_month = await repo.get_monthly_purchases_by_month(
            tenant_id, earliest_month=date(2026, 1, 1)
        )
        assert by_month[date(2026, 7, 1)] == (Decimal("800.00"), 1)


class TestFishSalesChart:
    async def test_orders_by_sales_amount_descending_and_respects_limit(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        pomfret = await _make_fish(db_session, tenant_id, name="Pomfret")
        mackerel = await _make_fish(db_session, tenant_id, name="Mackerel")
        await _make_invoice_item(
            db_session,
            tenant_id,
            invoice.id,
            pomfret.id,
            line_number=1,
            quantity=Decimal("820.500"),
            line_total=Decimal("184320.00"),
        )
        await _make_invoice_item(
            db_session,
            tenant_id,
            invoice.id,
            mackerel.id,
            line_number=2,
            quantity=Decimal("500.000"),
            line_total=Decimal("62000.00"),
        )

        rows = await repo.get_top_fish_by_sales(tenant_id, limit=10)

        assert rows[0] == ("Pomfret", Decimal("820.500"), Decimal("184320.00"))
        assert rows[1] == ("Mackerel", Decimal("500.000"), Decimal("62000.00"))

    async def test_excludes_items_on_draft_invoices(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        draft_invoice = await _make_invoice(
            db_session, tenant_id, company.id, status=InvoiceStatus.DRAFT
        )
        fish = await _make_fish(db_session, tenant_id, name="Draft-only Fish")
        await _make_invoice_item(db_session, tenant_id, draft_invoice.id, fish.id)

        rows = await repo.get_top_fish_by_sales(tenant_id, limit=10)
        assert rows == []

    async def test_respects_limit(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        for i in range(15):
            fish = await _make_fish(db_session, tenant_id, name=f"Fish {i}")
            await _make_invoice_item(
                db_session,
                tenant_id,
                invoice.id,
                fish.id,
                line_number=i + 1,
                line_total=Decimal(f"{1000 + i}.00"),
            )

        rows = await repo.get_top_fish_by_sales(tenant_id, limit=10)
        assert len(rows) == 10


class TestTripStatusChart:
    async def test_groups_by_status(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        # PLANNED/DEPARTED are both "active" (ix_trips_boat_single_active) -
        # a boat can only have one such trip at a time, so each trip here
        # needs its own boat.
        boat_a = await _make_boat(db_session, tenant_id)
        boat_b = await _make_boat(db_session, tenant_id)
        boat_c = await _make_boat(db_session, tenant_id)
        await _make_trip(db_session, tenant_id, boat_a.id, status=TripStatus.DEPARTED)
        await _make_trip(db_session, tenant_id, boat_b.id, status=TripStatus.PLANNED)
        await _make_trip(db_session, tenant_id, boat_c.id, status=TripStatus.PLANNED)

        counts = await repo.get_trip_status_counts(tenant_id)

        assert counts[TripStatus.DEPARTED] == 1
        assert counts[TripStatus.PLANNED] == 2
        assert TripStatus.RETURNED not in counts

    async def test_isolated_by_tenant(
        self,
        repo: DashboardRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        other_tenant_id: uuid.UUID,
    ) -> None:
        other_boat = await _make_boat(db_session, other_tenant_id)
        await _make_trip(db_session, other_tenant_id, other_boat.id, status=TripStatus.DEPARTED)

        counts = await repo.get_trip_status_counts(tenant_id)
        assert counts == {}


class TestTopCustomers:
    async def test_orders_by_total_sales_descending_and_respects_limit(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        big = await _make_company(
            db_session, tenant_id, name="Konkan Seafoods", outstanding_amount=Decimal("500.00")
        )
        small = await _make_company(
            db_session, tenant_id, name="Small Traders", outstanding_amount=Decimal("100.00")
        )
        await _make_invoice(db_session, tenant_id, big.id, total_amount=Decimal("2000.00"))
        await _make_invoice(db_session, tenant_id, big.id, total_amount=Decimal("500.00"))
        await _make_invoice(db_session, tenant_id, small.id, total_amount=Decimal("300.00"))

        rows = await repo.get_top_customers(tenant_id, limit=5)

        assert rows[0][0] == big.id
        assert rows[0][1] == "Konkan Seafoods"
        assert rows[0][2] == Decimal("2500.00")
        assert rows[0][3] == 2
        assert rows[0][4] == Decimal("500.00")
        assert rows[1][0] == small.id

    async def test_excludes_draft_and_cancelled_invoices(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            status=InvoiceStatus.DRAFT,
            total_amount=Decimal("999.00"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            status=InvoiceStatus.CANCELLED,
            total_amount=Decimal("999.00"),
        )

        rows = await repo.get_top_customers(tenant_id, limit=5)
        assert rows == []

    async def test_respects_limit(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        for i in range(8):
            company = await _make_company(db_session, tenant_id, name=f"Company {i}")
            await _make_invoice(
                db_session, tenant_id, company.id, total_amount=Decimal(f"{1000 + i}.00")
            )

        rows = await repo.get_top_customers(tenant_id, limit=5)
        assert len(rows) == 5


class TestTopSuppliers:
    async def test_orders_by_purchase_total_descending(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        big = await _make_supplier(
            db_session,
            tenant_id,
            name="Ratnagiri Fish Traders",
            outstanding_amount=Decimal("200.00"),
        )
        small = await _make_supplier(db_session, tenant_id, name="Small Supplier")
        await _make_purchase_bill(db_session, tenant_id, big.id, total_amount=Decimal("1500.00"))
        await _make_purchase_bill(db_session, tenant_id, small.id, total_amount=Decimal("300.00"))

        rows = await repo.get_top_suppliers(tenant_id, limit=5)

        assert rows[0][0] == big.id
        assert rows[0][1] == "Ratnagiri Fish Traders"
        assert rows[0][2] == Decimal("1500.00")
        assert rows[0][3] == 1
        assert rows[0][4] == Decimal("200.00")

    async def test_excludes_draft_and_cancelled_bills(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier = await _make_supplier(db_session, tenant_id)
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            status=PurchaseStatus.DRAFT,
            total_amount=Decimal("999.00"),
        )

        rows = await repo.get_top_suppliers(tenant_id, limit=5)
        assert rows == []


class TestTopFishWidget:
    async def test_includes_fish_id_and_orders_by_sales_amount_descending(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        pomfret = await _make_fish(db_session, tenant_id, name="Pomfret")
        await _make_invoice_item(
            db_session,
            tenant_id,
            invoice.id,
            pomfret.id,
            quantity=Decimal("820.500"),
            line_total=Decimal("184320.00"),
        )

        rows = await repo.get_top_fish_widget(tenant_id, limit=5)

        assert rows[0] == (pomfret.id, "Pomfret", Decimal("820.500"), Decimal("184320.00"))

    async def test_respects_limit(
        self, repo: DashboardRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        for i in range(8):
            fish = await _make_fish(db_session, tenant_id, name=f"Fish {i}")
            await _make_invoice_item(
                db_session,
                tenant_id,
                invoice.id,
                fish.id,
                line_number=i + 1,
                line_total=Decimal(f"{1000 + i}.00"),
            )

        rows = await repo.get_top_fish_widget(tenant_id, limit=5)
        assert len(rows) == 5
