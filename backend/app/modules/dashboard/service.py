import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dashboard.constants import (
    CHART_MONTHS,
    DRAFT_STALE_THRESHOLD_DAYS,
    EXPIRY_WARNING_WINDOW_DAYS,
    RECENT_ACTIVITY_LIMIT,
    TOP_CUSTOMERS_LIMIT,
    TOP_FISH_LIMIT,
    TOP_FISH_WIDGET_LIMIT,
    TOP_SUPPLIERS_LIMIT,
    ActivityType,
    AlertType,
)
from app.modules.dashboard.repository import (
    BoatAggregates,
    DashboardRepository,
    InvoiceAggregates,
    PaymentAggregates,
    PurchaseBillAggregates,
)
from app.modules.dashboard.schemas import (
    AlertItem,
    DashboardCharts,
    DashboardFinancial,
    DashboardKPIs,
    DashboardOperations,
    DashboardResponse,
    DashboardWidgets,
    FishSalesPoint,
    MonthlyPurchasesPoint,
    MonthlySalesPoint,
    OutstandingSummary,
    RecentActivityItem,
    TopCustomerItem,
    TopFishItem,
    TopSupplierItem,
    TripStatusChartLabel,
    TripStatusPoint,
    _RecentActivityRow,
)
from app.modules.trips.constants import TripStatus

_ZERO_MONTH_TOTALS = (Decimal("0"), 0)

# Sprint 10 Session 3 "CHART 4"'s four slices, in the spec's own listed
# order (Active, Completed, Cancelled, Draft) - see TripStatusPoint's
# docstring for the label mapping's rationale.
_TRIP_STATUS_CHART_ORDER: list[tuple[TripStatus, TripStatusChartLabel]] = [
    (TripStatus.DEPARTED, "Active"),
    (TripStatus.RETURNED, "Completed"),
    (TripStatus.CANCELLED, "Cancelled"),
    (TripStatus.PLANNED, "Draft"),
]


def _last_n_month_starts(as_of: date, n: int) -> list[date]:
    """The first-of-month date for each of the trailing `n` months,
    ascending, ending with `as_of`'s own month - plain calendar arithmetic
    (no rows touched), used to zero-fill months a chart query has no data
    for rather than showing a gap."""
    as_of_index = as_of.year * 12 + (as_of.month - 1)
    months: list[date] = []
    for offset in range(n - 1, -1, -1):
        total = as_of_index - offset
        year, month0 = divmod(total, 12)
        months.append(date(year, month0 + 1, 1))
    return months


class DashboardService:
    """Assembles the single GET /dashboard response.

    Every number is either returned directly by one grouped aggregate query
    (DashboardRepository) or derived by simple arithmetic/sorting over a
    handful of those already-aggregated results (e.g. `boats_available =
    boats.active_count - trips.boats_at_sea`, and merging five 10-row
    "recent" lists into one). Nothing here re-aggregates raw rows in
    Python - that work already happened in SQL.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = DashboardRepository(session)

    async def get_dashboard(self, *, tenant_id: uuid.UUID) -> DashboardResponse:
        now = datetime.now(UTC)
        today = now.date()
        month_start = today.replace(day=1)
        stale_draft_cutoff = now - timedelta(days=DRAFT_STALE_THRESHOLD_DAYS)
        expiry_window_end = today + timedelta(days=EXPIRY_WARNING_WINDOW_DAYS)

        invoice_agg = await self._repo.get_invoice_aggregates(
            tenant_id, today=today, month_start=month_start, stale_draft_cutoff=stale_draft_cutoff
        )
        payment_agg = await self._repo.get_payment_aggregates(
            tenant_id, today=today, stale_draft_cutoff=stale_draft_cutoff
        )
        supplier_payments_today = await self._repo.get_supplier_payments_today(
            tenant_id, today=today
        )
        purchase_bill_agg = await self._repo.get_purchase_bill_aggregates(
            tenant_id, today=today, month_start=month_start
        )
        trip_agg = await self._repo.get_trip_aggregates(tenant_id, today=today)
        boat_agg = await self._repo.get_boat_aggregates(
            tenant_id, today=today, expiry_window_end=expiry_window_end
        )
        todays_catch_quantity = await self._repo.get_todays_catch_quantity(tenant_id, today=today)
        customer_outstanding = await self._repo.get_customer_outstanding(tenant_id)
        supplier_outstanding = await self._repo.get_supplier_outstanding(tenant_id)

        boats_available = boat_agg.active_count - trip_agg.boats_at_sea

        kpis = DashboardKPIs(
            todays_sales=invoice_agg.todays_sales,
            monthly_sales=invoice_agg.monthly_sales,
            customer_payments_today=payment_agg.customer_payments_today,
            supplier_payments_today=supplier_payments_today,
            active_trips=trip_agg.trips_active,
            boats_at_sea=trip_agg.boats_at_sea,
            todays_catch_quantity=todays_catch_quantity,
            draft_invoices=invoice_agg.draft_count,
            draft_payments=payment_agg.draft_count,
        )
        operations = DashboardOperations(
            trips_today=trip_agg.trips_today,
            trips_active=trip_agg.trips_active,
            trips_completed_today=trip_agg.trips_completed_today,
            boats_available=boats_available,
            boats_at_sea=trip_agg.boats_at_sea,
            boats_maintenance=boat_agg.maintenance_count,
        )
        financial = DashboardFinancial(
            customer_outstanding=customer_outstanding,
            supplier_outstanding=supplier_outstanding,
            invoices_issued_this_month=invoice_agg.issued_this_month_count,
            purchase_bills_this_month=purchase_bill_agg.posted_this_month_count,
        )

        recent_activity = await self._build_recent_activity(tenant_id)
        alerts = self._build_alerts(invoice_agg, payment_agg, purchase_bill_agg, boat_agg)
        charts = await self._build_charts(tenant_id, today=today)
        widgets = await self._build_widgets(
            tenant_id,
            customer_outstanding=customer_outstanding,
            supplier_outstanding=supplier_outstanding,
            customer_overdue=invoice_agg.overdue_amount,
            supplier_overdue=purchase_bill_agg.overdue_amount,
        )

        return DashboardResponse(
            kpis=kpis,
            operations=operations,
            financial=financial,
            recent_activity=recent_activity,
            alerts=alerts,
            charts=charts,
            widgets=widgets,
        )

    async def _build_recent_activity(self, tenant_id: uuid.UUID) -> list[RecentActivityItem]:
        # Five bounded (LIMIT 10) queries, one per source table, merged and
        # re-sorted in Python - the "recent activity" equivalent of the
        # per-table aggregate queries above. Never loads a whole table.
        limit = RECENT_ACTIVITY_LIMIT
        sources: list[tuple[ActivityType, list[_RecentActivityRow]]] = [
            (ActivityType.INVOICE, await self._repo.recent_invoices(tenant_id, limit=limit)),
            (ActivityType.PAYMENT, await self._repo.recent_payments(tenant_id, limit=limit)),
            (ActivityType.TRIP, await self._repo.recent_trips(tenant_id, limit=limit)),
            (
                ActivityType.PURCHASE_BILL,
                await self._repo.recent_purchase_bills(tenant_id, limit=limit),
            ),
            (
                ActivityType.SUPPLIER_PAYMENT,
                await self._repo.recent_supplier_payments(tenant_id, limit=limit),
            ),
        ]
        merged = [
            RecentActivityItem(
                type=activity_type,
                reference=row.reference,
                title=row.title,
                created_at=row.created_at,
            )
            for activity_type, rows in sources
            for row in rows
        ]
        merged.sort(key=lambda item: item.created_at, reverse=True)
        return merged[:RECENT_ACTIVITY_LIMIT]

    @staticmethod
    def _build_alerts(
        invoice_agg: InvoiceAggregates,
        payment_agg: PaymentAggregates,
        purchase_bill_agg: PurchaseBillAggregates,
        boat_agg: BoatAggregates,
    ) -> list[AlertItem]:
        candidates = [
            (
                AlertType.BOAT_LICENSE_EXPIRING,
                boat_agg.license_expiring_count,
                f"{boat_agg.license_expiring_count} boat license(s) expiring within "
                f"{EXPIRY_WARNING_WINDOW_DAYS} days",
            ),
            (
                AlertType.BOAT_INSURANCE_EXPIRING,
                boat_agg.insurance_expiring_count,
                "{count} boat insurance polic{plural} expiring within {days} days".format(
                    count=boat_agg.insurance_expiring_count,
                    plural="y" if boat_agg.insurance_expiring_count == 1 else "ies",
                    days=EXPIRY_WARNING_WINDOW_DAYS,
                ),
            ),
            (
                AlertType.INVOICE_OVERDUE,
                invoice_agg.overdue_count,
                f"{invoice_agg.overdue_count} invoice(s) are overdue",
            ),
            (
                AlertType.PURCHASE_BILL_OVERDUE,
                purchase_bill_agg.overdue_count,
                f"{purchase_bill_agg.overdue_count} purchase bill(s) are overdue",
            ),
            (
                AlertType.DRAFT_INVOICE_STALE,
                invoice_agg.stale_draft_count,
                f"{invoice_agg.stale_draft_count} draft invoice(s) older than "
                f"{DRAFT_STALE_THRESHOLD_DAYS} days",
            ),
            (
                AlertType.DRAFT_PAYMENT_STALE,
                payment_agg.stale_draft_count,
                f"{payment_agg.stale_draft_count} draft payment(s) older than "
                f"{DRAFT_STALE_THRESHOLD_DAYS} days",
            ),
        ]
        return [
            AlertItem(type=alert_type, count=count, message=message)
            for alert_type, count, message in candidates
            if count > 0
        ]

    async def _build_charts(self, tenant_id: uuid.UUID, *, today: date) -> DashboardCharts:
        """Sprint 10 Session 3's four chart series - each backed by one
        grouped aggregate query (DashboardRepository), with the trailing-
        12-month and all-four-trip-status zero-filling done here in Python
        over an already-tiny, already-aggregated result set (never raw
        business rows)."""
        month_starts = _last_n_month_starts(today, CHART_MONTHS)

        sales_by_month = await self._repo.get_monthly_sales_by_month(
            tenant_id, earliest_month=month_starts[0]
        )
        purchases_by_month = await self._repo.get_monthly_purchases_by_month(
            tenant_id, earliest_month=month_starts[0]
        )
        fish_sales_rows = await self._repo.get_top_fish_by_sales(tenant_id, limit=TOP_FISH_LIMIT)
        trip_status_counts = await self._repo.get_trip_status_counts(tenant_id)

        monthly_sales = [
            MonthlySalesPoint(
                month=month,
                sales_amount=sales_by_month.get(month, _ZERO_MONTH_TOTALS)[0],
                invoice_count=sales_by_month.get(month, _ZERO_MONTH_TOTALS)[1],
            )
            for month in month_starts
        ]
        monthly_purchases = [
            MonthlyPurchasesPoint(
                month=month,
                purchase_amount=purchases_by_month.get(month, _ZERO_MONTH_TOTALS)[0],
                purchase_bill_count=purchases_by_month.get(month, _ZERO_MONTH_TOTALS)[1],
            )
            for month in month_starts
        ]
        fish_sales = [
            FishSalesPoint(fish_name=name, quantity_sold=quantity, sales_amount=amount)
            for name, quantity, amount in fish_sales_rows
        ]
        trip_status = [
            TripStatusPoint(status=label, count=trip_status_counts.get(status, 0))
            for status, label in _TRIP_STATUS_CHART_ORDER
        ]

        return DashboardCharts(
            monthly_sales=monthly_sales,
            monthly_purchases=monthly_purchases,
            fish_sales=fish_sales,
            trip_status=trip_status,
        )

    async def _build_widgets(
        self,
        tenant_id: uuid.UUID,
        *,
        customer_outstanding: Decimal,
        supplier_outstanding: Decimal,
        customer_overdue: Decimal,
        supplier_overdue: Decimal,
    ) -> DashboardWidgets:
        """Sprint 10 Session 4's "ERP Command Center" widgets - top
        customers/suppliers/fish are each one grouped `ORDER BY ... LIMIT`
        aggregate query (DashboardRepository); the outstanding summary
        reuses figures the caller already computed earlier in
        get_dashboard rather than re-querying them."""
        top_customer_rows = await self._repo.get_top_customers(
            tenant_id, limit=TOP_CUSTOMERS_LIMIT
        )
        top_supplier_rows = await self._repo.get_top_suppliers(
            tenant_id, limit=TOP_SUPPLIERS_LIMIT
        )
        top_fish_rows = await self._repo.get_top_fish_widget(
            tenant_id, limit=TOP_FISH_WIDGET_LIMIT
        )

        top_customers = [
            TopCustomerItem(
                company_id=row[0],
                company_name=row[1],
                total_sales=row[2],
                invoice_count=row[3],
                outstanding_amount=row[4],
            )
            for row in top_customer_rows
        ]
        top_suppliers = [
            TopSupplierItem(
                supplier_id=row[0],
                supplier_name=row[1],
                purchase_total=row[2],
                purchase_bill_count=row[3],
                outstanding_amount=row[4],
            )
            for row in top_supplier_rows
        ]
        top_fish = [
            TopFishItem(fish_id=row[0], fish_name=row[1], quantity_sold=row[2], sales_amount=row[3])
            for row in top_fish_rows
        ]

        return DashboardWidgets(
            top_customers=top_customers,
            top_suppliers=top_suppliers,
            top_fish=top_fish,
            outstanding_summary=OutstandingSummary(
                customer_outstanding=customer_outstanding,
                customer_overdue=customer_overdue,
                supplier_outstanding=supplier_outstanding,
                supplier_overdue=supplier_overdue,
            ),
        )
