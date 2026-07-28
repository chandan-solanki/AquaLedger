import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.modules.dashboard.constants import AlertType
from app.modules.dashboard.repository import (
    BoatAggregates,
    InvoiceAggregates,
    PaymentAggregates,
    PurchaseBillAggregates,
    TripAggregates,
)
from app.modules.dashboard.schemas import _RecentActivityRow
from app.modules.dashboard.service import DashboardService, _last_n_month_starts
from app.modules.trips.constants import TripStatus

_ZERO_INVOICE_AGG = InvoiceAggregates(
    todays_sales=Decimal("0"),
    monthly_sales=Decimal("0"),
    draft_count=0,
    issued_this_month_count=0,
    overdue_count=0,
    overdue_amount=Decimal("0"),
    stale_draft_count=0,
)
_ZERO_PAYMENT_AGG = PaymentAggregates(
    customer_payments_today=Decimal("0"), draft_count=0, stale_draft_count=0
)
_ZERO_PURCHASE_BILL_AGG = PurchaseBillAggregates(
    posted_this_month_count=0, overdue_count=0, overdue_amount=Decimal("0")
)
_ZERO_TRIP_AGG = TripAggregates(
    trips_today=0, trips_active=0, trips_completed_today=0, boats_at_sea=0
)
_ZERO_BOAT_AGG = BoatAggregates(
    active_count=0, maintenance_count=0, license_expiring_count=0, insurance_expiring_count=0
)


class _FakeDashboardRepo:
    """Stands in for DashboardRepository - every aggregate defaults to a
    "nothing happening" zero value so a test only has to override the one
    field it cares about."""

    def __init__(
        self,
        *,
        invoice_agg: InvoiceAggregates = _ZERO_INVOICE_AGG,
        payment_agg: PaymentAggregates = _ZERO_PAYMENT_AGG,
        supplier_payments_today: Decimal = Decimal("0"),
        purchase_bill_agg: PurchaseBillAggregates = _ZERO_PURCHASE_BILL_AGG,
        trip_agg: TripAggregates = _ZERO_TRIP_AGG,
        boat_agg: BoatAggregates = _ZERO_BOAT_AGG,
        todays_catch_quantity: Decimal = Decimal("0"),
        customer_outstanding: Decimal = Decimal("0"),
        supplier_outstanding: Decimal = Decimal("0"),
        invoices: list[_RecentActivityRow] | None = None,
        payments: list[_RecentActivityRow] | None = None,
        trips: list[_RecentActivityRow] | None = None,
        purchase_bills: list[_RecentActivityRow] | None = None,
        supplier_payments: list[_RecentActivityRow] | None = None,
        sales_by_month: dict[date, tuple[Decimal, int]] | None = None,
        purchases_by_month: dict[date, tuple[Decimal, int]] | None = None,
        fish_sales_rows: list[tuple[str, Decimal, Decimal]] | None = None,
        trip_status_counts: dict[TripStatus, int] | None = None,
        top_customer_rows: list[tuple[uuid.UUID, str, Decimal, int, Decimal]] | None = None,
        top_supplier_rows: list[tuple[uuid.UUID, str, Decimal, int, Decimal]] | None = None,
        top_fish_widget_rows: list[tuple[uuid.UUID, str, Decimal, Decimal]] | None = None,
    ) -> None:
        self.invoice_agg = invoice_agg
        self.payment_agg = payment_agg
        self.supplier_payments_today = supplier_payments_today
        self.purchase_bill_agg = purchase_bill_agg
        self.trip_agg = trip_agg
        self.boat_agg = boat_agg
        self.todays_catch_quantity = todays_catch_quantity
        self.customer_outstanding = customer_outstanding
        self.supplier_outstanding = supplier_outstanding
        self.invoices = invoices or []
        self.payments = payments or []
        self.trips = trips or []
        self.purchase_bills = purchase_bills or []
        self.supplier_payments = supplier_payments or []
        self.sales_by_month = sales_by_month or {}
        self.purchases_by_month = purchases_by_month or {}
        self.fish_sales_rows = fish_sales_rows or []
        self.trip_status_counts = trip_status_counts or {}
        self.top_customer_rows = top_customer_rows or []
        self.top_supplier_rows = top_supplier_rows or []
        self.top_fish_widget_rows = top_fish_widget_rows or []

    async def get_invoice_aggregates(self, *args: Any, **kwargs: Any) -> InvoiceAggregates:
        return self.invoice_agg

    async def get_payment_aggregates(self, *args: Any, **kwargs: Any) -> PaymentAggregates:
        return self.payment_agg

    async def get_supplier_payments_today(self, *args: Any, **kwargs: Any) -> Decimal:
        return self.supplier_payments_today

    async def get_purchase_bill_aggregates(
        self, *args: Any, **kwargs: Any
    ) -> PurchaseBillAggregates:
        return self.purchase_bill_agg

    async def get_trip_aggregates(self, *args: Any, **kwargs: Any) -> TripAggregates:
        return self.trip_agg

    async def get_boat_aggregates(self, *args: Any, **kwargs: Any) -> BoatAggregates:
        return self.boat_agg

    async def get_todays_catch_quantity(self, *args: Any, **kwargs: Any) -> Decimal:
        return self.todays_catch_quantity

    async def get_customer_outstanding(self, *args: Any, **kwargs: Any) -> Decimal:
        return self.customer_outstanding

    async def get_supplier_outstanding(self, *args: Any, **kwargs: Any) -> Decimal:
        return self.supplier_outstanding

    async def recent_invoices(self, *args: Any, **kwargs: Any) -> list[_RecentActivityRow]:
        return self.invoices

    async def recent_payments(self, *args: Any, **kwargs: Any) -> list[_RecentActivityRow]:
        return self.payments

    async def recent_trips(self, *args: Any, **kwargs: Any) -> list[_RecentActivityRow]:
        return self.trips

    async def recent_purchase_bills(self, *args: Any, **kwargs: Any) -> list[_RecentActivityRow]:
        return self.purchase_bills

    async def recent_supplier_payments(self, *args: Any, **kwargs: Any) -> list[_RecentActivityRow]:
        return self.supplier_payments

    async def get_monthly_sales_by_month(
        self, *args: Any, **kwargs: Any
    ) -> dict[date, tuple[Decimal, int]]:
        return self.sales_by_month

    async def get_monthly_purchases_by_month(
        self, *args: Any, **kwargs: Any
    ) -> dict[date, tuple[Decimal, int]]:
        return self.purchases_by_month

    async def get_top_fish_by_sales(
        self, *args: Any, **kwargs: Any
    ) -> list[tuple[str, Decimal, Decimal]]:
        return self.fish_sales_rows

    async def get_trip_status_counts(self, *args: Any, **kwargs: Any) -> dict[TripStatus, int]:
        return self.trip_status_counts

    async def get_top_customers(
        self, *args: Any, **kwargs: Any
    ) -> list[tuple[uuid.UUID, str, Decimal, int, Decimal]]:
        return self.top_customer_rows

    async def get_top_suppliers(
        self, *args: Any, **kwargs: Any
    ) -> list[tuple[uuid.UUID, str, Decimal, int, Decimal]]:
        return self.top_supplier_rows

    async def get_top_fish_widget(
        self, *args: Any, **kwargs: Any
    ) -> list[tuple[uuid.UUID, str, Decimal, Decimal]]:
        return self.top_fish_widget_rows


def _service_with_fake(fake_repo: _FakeDashboardRepo) -> DashboardService:
    service = DashboardService.__new__(DashboardService)
    service._repo = fake_repo  # type: ignore[assignment]
    return service


def _row(reference: str, title: str, created_at: datetime) -> _RecentActivityRow:
    return _RecentActivityRow(
        id=uuid.uuid4(), reference=reference, title=title, created_at=created_at
    )


class TestGetDashboardAssembly:
    async def test_zero_state_tenant_gets_all_zero_sections_and_no_alerts(self) -> None:
        service = _service_with_fake(_FakeDashboardRepo())
        response = await service.get_dashboard(tenant_id=uuid.uuid4())

        assert response.kpis.todays_sales == Decimal("0")
        assert response.kpis.active_trips == 0
        assert response.operations.boats_available == 0
        assert response.financial.customer_outstanding == Decimal("0")
        assert response.recent_activity == []
        assert response.alerts == []
        assert len(response.charts.monthly_sales) == 12
        assert all(point.sales_amount == Decimal("0") for point in response.charts.monthly_sales)
        assert len(response.charts.monthly_purchases) == 12
        assert response.charts.fish_sales == []
        assert [point.status for point in response.charts.trip_status] == [
            "Active",
            "Completed",
            "Cancelled",
            "Draft",
        ]
        assert all(point.count == 0 for point in response.charts.trip_status)

    async def test_boats_available_is_active_minus_at_sea(self) -> None:
        fake_repo = _FakeDashboardRepo(
            boat_agg=BoatAggregates(
                active_count=5,
                maintenance_count=2,
                license_expiring_count=0,
                insurance_expiring_count=0,
            ),
            trip_agg=TripAggregates(
                trips_today=0, trips_active=0, trips_completed_today=0, boats_at_sea=2
            ),
        )
        service = _service_with_fake(fake_repo)
        response = await service.get_dashboard(tenant_id=uuid.uuid4())

        assert response.operations.boats_at_sea == 2
        assert response.operations.boats_maintenance == 2
        # 5 active boats, 2 currently at sea -> 3 available.
        assert response.operations.boats_available == 3

    async def test_kpis_and_financial_pass_through_repository_values(self) -> None:
        fake_repo = _FakeDashboardRepo(
            invoice_agg=InvoiceAggregates(
                todays_sales=Decimal("48250.00"),
                monthly_sales=Decimal("612400.00"),
                draft_count=4,
                issued_this_month_count=42,
                overdue_count=0,
                overdue_amount=Decimal("0"),
                stale_draft_count=0,
            ),
            payment_agg=PaymentAggregates(
                customer_payments_today=Decimal("35000.00"), draft_count=1, stale_draft_count=0
            ),
            supplier_payments_today=Decimal("12000.00"),
            customer_outstanding=Decimal("184200.00"),
            supplier_outstanding=Decimal("76500.00"),
            purchase_bill_agg=PurchaseBillAggregates(
                posted_this_month_count=15, overdue_count=0, overdue_amount=Decimal("0")
            ),
            todays_catch_quantity=Decimal("1250.500"),
        )
        service = _service_with_fake(fake_repo)
        response = await service.get_dashboard(tenant_id=uuid.uuid4())

        assert response.kpis.todays_sales == Decimal("48250.00")
        assert response.kpis.monthly_sales == Decimal("612400.00")
        assert response.kpis.customer_payments_today == Decimal("35000.00")
        assert response.kpis.supplier_payments_today == Decimal("12000.00")
        assert response.kpis.todays_catch_quantity == Decimal("1250.500")
        assert response.kpis.draft_invoices == 4
        assert response.kpis.draft_payments == 1
        assert response.financial.customer_outstanding == Decimal("184200.00")
        assert response.financial.supplier_outstanding == Decimal("76500.00")
        assert response.financial.invoices_issued_this_month == 42
        assert response.financial.purchase_bills_this_month == 15


class TestRecentActivityMerge:
    async def test_merges_all_five_sources_sorted_newest_first(self) -> None:
        t1 = datetime(2026, 7, 28, 10, 0, tzinfo=UTC)
        t2 = datetime(2026, 7, 28, 11, 0, tzinfo=UTC)
        t3 = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)
        fake_repo = _FakeDashboardRepo(
            invoices=[_row("INV-1", "Invoice to A", t1)],
            payments=[_row("PAY-1", "Payment from A", t3)],
            trips=[_row("TRIP-1", "Trip 1", t2)],
        )
        service = _service_with_fake(fake_repo)
        response = await service.get_dashboard(tenant_id=uuid.uuid4())

        assert [item.reference for item in response.recent_activity] == [
            "PAY-1",
            "TRIP-1",
            "INV-1",
        ]

    async def test_truncates_to_the_configured_limit(self) -> None:
        base = datetime(2026, 7, 28, 0, 0, tzinfo=UTC)
        many_invoices = [
            _row(f"INV-{i}", f"Invoice {i}", base.replace(hour=i)) for i in range(1, 13)
        ]
        fake_repo = _FakeDashboardRepo(invoices=many_invoices)
        service = _service_with_fake(fake_repo)
        response = await service.get_dashboard(tenant_id=uuid.uuid4())

        assert len(response.recent_activity) == 10
        # Newest (hour=12) first.
        assert response.recent_activity[0].reference == "INV-12"


class TestBuildAlerts:
    def test_no_alerts_when_every_count_is_zero(self) -> None:
        alerts = DashboardService._build_alerts(
            _ZERO_INVOICE_AGG, _ZERO_PAYMENT_AGG, _ZERO_PURCHASE_BILL_AGG, _ZERO_BOAT_AGG
        )
        assert alerts == []

    def test_only_nonzero_counts_produce_alerts(self) -> None:
        invoice_agg = InvoiceAggregates(
            todays_sales=Decimal("0"),
            monthly_sales=Decimal("0"),
            draft_count=0,
            issued_this_month_count=0,
            overdue_count=3,
            overdue_amount=Decimal("300.00"),
            stale_draft_count=2,
        )
        alerts = DashboardService._build_alerts(
            invoice_agg, _ZERO_PAYMENT_AGG, _ZERO_PURCHASE_BILL_AGG, _ZERO_BOAT_AGG
        )
        alert_types = {alert.type for alert in alerts}
        assert alert_types == {AlertType.INVOICE_OVERDUE, AlertType.DRAFT_INVOICE_STALE}

        overdue = next(a for a in alerts if a.type == AlertType.INVOICE_OVERDUE)
        assert overdue.count == 3
        assert "3" in overdue.message

    def test_boat_insurance_message_pluralizes_correctly(self) -> None:
        singular = BoatAggregates(
            active_count=0,
            maintenance_count=0,
            license_expiring_count=0,
            insurance_expiring_count=1,
        )
        plural = BoatAggregates(
            active_count=0,
            maintenance_count=0,
            license_expiring_count=0,
            insurance_expiring_count=2,
        )
        singular_alert = DashboardService._build_alerts(
            _ZERO_INVOICE_AGG, _ZERO_PAYMENT_AGG, _ZERO_PURCHASE_BILL_AGG, singular
        )[0]
        plural_alert = DashboardService._build_alerts(
            _ZERO_INVOICE_AGG, _ZERO_PAYMENT_AGG, _ZERO_PURCHASE_BILL_AGG, plural
        )[0]
        assert "policy" in singular_alert.message
        assert "policies" in plural_alert.message


class TestLastNMonthStarts:
    def test_returns_twelve_ascending_month_starts_ending_at_as_of_month(self) -> None:
        months = _last_n_month_starts(date(2026, 7, 28), 12)
        assert len(months) == 12
        assert months[-1] == date(2026, 7, 1)
        assert months[0] == date(2025, 8, 1)
        assert months == sorted(months)

    def test_crosses_the_year_boundary_correctly(self) -> None:
        months = _last_n_month_starts(date(2026, 1, 15), 3)
        assert months == [date(2025, 11, 1), date(2025, 12, 1), date(2026, 1, 1)]


class TestBuildCharts:
    async def test_zero_fills_months_with_no_data(self) -> None:
        fake_repo = _FakeDashboardRepo(
            sales_by_month={date(2026, 7, 1): (Decimal("612400.00"), 42)}
        )
        service = _service_with_fake(fake_repo)
        response = await service.get_dashboard(tenant_id=uuid.uuid4())

        by_month = {point.month: point for point in response.charts.monthly_sales}
        assert by_month[date(2026, 7, 28).replace(day=1)].sales_amount == Decimal("612400.00")
        assert by_month[date(2026, 7, 28).replace(day=1)].invoice_count == 42
        other_months = [p for m, p in by_month.items() if m != date(2026, 7, 1)]
        assert all(p.sales_amount == Decimal("0") and p.invoice_count == 0 for p in other_months)

    async def test_fish_sales_passes_through_repository_order(self) -> None:
        fake_repo = _FakeDashboardRepo(
            fish_sales_rows=[
                ("Pomfret", Decimal("820.500"), Decimal("184320.00")),
                ("Mackerel", Decimal("500.000"), Decimal("62000.00")),
            ]
        )
        service = _service_with_fake(fake_repo)
        response = await service.get_dashboard(tenant_id=uuid.uuid4())

        assert [p.fish_name for p in response.charts.fish_sales] == ["Pomfret", "Mackerel"]
        assert response.charts.fish_sales[0].sales_amount == Decimal("184320.00")

    async def test_trip_status_relabels_and_zero_fills_missing_statuses(self) -> None:
        fake_repo = _FakeDashboardRepo(
            trip_status_counts={TripStatus.DEPARTED: 3, TripStatus.RETURNED: 12}
        )
        service = _service_with_fake(fake_repo)
        response = await service.get_dashboard(tenant_id=uuid.uuid4())

        counts = {point.status: point.count for point in response.charts.trip_status}
        assert counts == {"Active": 3, "Completed": 12, "Cancelled": 0, "Draft": 0}


class TestBuildWidgets:
    async def test_zero_state_yields_empty_lists_and_zero_outstanding(self) -> None:
        service = _service_with_fake(_FakeDashboardRepo())
        response = await service.get_dashboard(tenant_id=uuid.uuid4())

        assert response.widgets.top_customers == []
        assert response.widgets.top_suppliers == []
        assert response.widgets.top_fish == []
        assert response.widgets.outstanding_summary.customer_outstanding == Decimal("0")
        assert response.widgets.outstanding_summary.customer_overdue == Decimal("0")
        assert response.widgets.outstanding_summary.supplier_outstanding == Decimal("0")
        assert response.widgets.outstanding_summary.supplier_overdue == Decimal("0")

    async def test_top_customers_and_suppliers_pass_through_repository_order(self) -> None:
        company_id = uuid.uuid4()
        supplier_id = uuid.uuid4()
        fish_id = uuid.uuid4()
        fake_repo = _FakeDashboardRepo(
            top_customer_rows=[
                (company_id, "Konkan Seafoods", Decimal("184320.00"), 12, Decimal("24500.00"))
            ],
            top_supplier_rows=[
                (supplier_id, "Ratnagiri Fish Traders", Decimal("96400.00"), 8, Decimal("12800.00"))
            ],
            top_fish_widget_rows=[(fish_id, "Pomfret", Decimal("820.500"), Decimal("184320.00"))],
        )
        service = _service_with_fake(fake_repo)
        response = await service.get_dashboard(tenant_id=uuid.uuid4())

        customer = response.widgets.top_customers[0]
        assert customer.company_id == company_id
        assert customer.company_name == "Konkan Seafoods"
        assert customer.total_sales == Decimal("184320.00")
        assert customer.invoice_count == 12
        assert customer.outstanding_amount == Decimal("24500.00")

        supplier = response.widgets.top_suppliers[0]
        assert supplier.supplier_id == supplier_id
        assert supplier.purchase_total == Decimal("96400.00")
        assert supplier.purchase_bill_count == 8

        fish = response.widgets.top_fish[0]
        assert fish.fish_id == fish_id
        assert fish.fish_name == "Pomfret"

    async def test_outstanding_summary_reuses_already_computed_figures(self) -> None:
        fake_repo = _FakeDashboardRepo(
            customer_outstanding=Decimal("184200.00"),
            supplier_outstanding=Decimal("76500.00"),
            invoice_agg=InvoiceAggregates(
                todays_sales=Decimal("0"),
                monthly_sales=Decimal("0"),
                draft_count=0,
                issued_this_month_count=0,
                overdue_count=2,
                overdue_amount=Decimal("42300.00"),
                stale_draft_count=0,
            ),
            purchase_bill_agg=PurchaseBillAggregates(
                posted_this_month_count=0, overdue_count=1, overdue_amount=Decimal("15400.00")
            ),
        )
        service = _service_with_fake(fake_repo)
        response = await service.get_dashboard(tenant_id=uuid.uuid4())

        summary = response.widgets.outstanding_summary
        assert summary.customer_outstanding == Decimal("184200.00")
        assert summary.customer_overdue == Decimal("42300.00")
        assert summary.supplier_outstanding == Decimal("76500.00")
        assert summary.supplier_overdue == Decimal("15400.00")
