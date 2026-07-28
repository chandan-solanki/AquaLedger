import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.modules.dashboard.constants import ActivityType, AlertType


class DashboardKPIs(BaseModel):
    """TASKS.md Sprint 10 Session 1, "SECTION 1 KPIs"."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "todays_sales": "48250.00",
                "monthly_sales": "612400.00",
                "customer_payments_today": "35000.00",
                "supplier_payments_today": "12000.00",
                "active_trips": 3,
                "boats_at_sea": 2,
                "todays_catch_quantity": "1250.500",
                "draft_invoices": 4,
                "draft_payments": 1,
            }
        }
    )

    todays_sales: Decimal
    monthly_sales: Decimal
    customer_payments_today: Decimal
    supplier_payments_today: Decimal
    active_trips: int
    boats_at_sea: int
    todays_catch_quantity: Decimal
    draft_invoices: int
    draft_payments: int


class DashboardOperations(BaseModel):
    """TASKS.md Sprint 10 Session 1, "SECTION 2 Operations".

    `boats_maintenance` maps to `Boat.is_active is False` - the schema has no
    dedicated boat-status column (only `is_active`), so "available" +
    "at sea" + "maintenance" is the only three-way split derivable from
    existing data: at-sea boats are the subset of active boats currently on
    a departed trip, available is the active remainder, and maintenance is
    every inactive boat. See DashboardRepository.get_boat_counts.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trips_today": 2,
                "trips_active": 3,
                "trips_completed_today": 1,
                "boats_available": 4,
                "boats_at_sea": 2,
                "boats_maintenance": 1,
            }
        }
    )

    trips_today: int
    trips_active: int
    trips_completed_today: int
    boats_available: int
    boats_at_sea: int
    boats_maintenance: int


class DashboardFinancial(BaseModel):
    """TASKS.md Sprint 10 Session 1, "SECTION 3 Financial"."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_outstanding": "184200.00",
                "supplier_outstanding": "76500.00",
                "invoices_issued_this_month": 42,
                "purchase_bills_this_month": 15,
            }
        }
    )

    customer_outstanding: Decimal
    supplier_outstanding: Decimal
    invoices_issued_this_month: int
    purchase_bills_this_month: int


class RecentActivityItem(BaseModel):
    """One row of TASKS.md Sprint 10 Session 1, "SECTION 4 Recent Activity"."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "invoice",
                "reference": "INV/2026-27/00042",
                "title": "Invoice to Konkan Seafoods",
                "created_at": "2026-07-28T05:12:00Z",
            }
        }
    )

    type: ActivityType
    reference: str
    title: str
    created_at: datetime


class AlertItem(BaseModel):
    """One entry of TASKS.md Sprint 10 Session 1, "SECTION 5 Alerts".

    Emitted only when `count > 0` - an alert about nothing to alert on isn't
    an alert (DashboardService.get_dashboard filters zero-count alerts out
    before assembling the response)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "invoice_overdue",
                "count": 3,
                "message": "3 invoices are overdue",
            }
        }
    )

    type: AlertType
    count: int
    message: str


class MonthlySalesPoint(BaseModel):
    """One point of TASKS.md Sprint 10 Session 3, "CHART 1 Monthly Sales" -
    `month` is always the first day of the month (UTC calendar month), one
    entry per of the trailing `CHART_MONTHS` months, zero-filled for months
    with no issued sales rather than omitted, so the LineChart never shows a
    gap."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"month": "2026-07-01", "sales_amount": "612400.00", "invoice_count": 42}
        }
    )

    month: date
    sales_amount: Decimal
    invoice_count: int


class MonthlyPurchasesPoint(BaseModel):
    """One point of TASKS.md Sprint 10 Session 3, "CHART 2 Monthly
    Purchases" - mirrors MonthlySalesPoint's shape on the buy side, same
    zero-fill discipline."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "month": "2026-07-01",
                "purchase_amount": "241800.00",
                "purchase_bill_count": 15,
            }
        }
    )

    month: date
    purchase_amount: Decimal
    purchase_bill_count: int


class FishSalesPoint(BaseModel):
    """One row of TASKS.md Sprint 10 Session 3, "CHART 3 Fish Sales
    Distribution" - top 10 fish by `sales_amount` descending, computed from
    `invoice_items` on non-draft/cancelled invoices only."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fish_name": "Pomfret",
                "quantity_sold": "820.500",
                "sales_amount": "184320.00",
            }
        }
    )

    fish_name: str
    quantity_sold: Decimal
    sales_amount: Decimal


TripStatusChartLabel = Literal["Active", "Completed", "Cancelled", "Draft"]


class TripStatusPoint(BaseModel):
    """One slice of TASKS.md Sprint 10 Session 3, "CHART 4 Trip Status
    Distribution" - `status` relabels the trips module's four real
    `TripStatus` values for chart-friendly display (`departed` -> "Active",
    `returned` -> "Completed", `cancelled` -> "Cancelled", `planned` ->
    "Draft"); always all four, zero-filled, never a subset."""

    model_config = ConfigDict(json_schema_extra={"example": {"status": "Active", "count": 3}})

    status: TripStatusChartLabel
    count: int


class DashboardCharts(BaseModel):
    """TASKS.md Sprint 10 Session 3's "charts" section - four backend-
    aggregated series added to the existing GET /dashboard response. No new
    endpoint: the frontend's `useDashboard()` is extended, not duplicated."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "monthly_sales": [
                    {"month": "2026-07-01", "sales_amount": "612400.00", "invoice_count": 42}
                ],
                "monthly_purchases": [
                    {
                        "month": "2026-07-01",
                        "purchase_amount": "241800.00",
                        "purchase_bill_count": 15,
                    }
                ],
                "fish_sales": [
                    {
                        "fish_name": "Pomfret",
                        "quantity_sold": "820.500",
                        "sales_amount": "184320.00",
                    }
                ],
                "trip_status": [
                    {"status": "Active", "count": 3},
                    {"status": "Completed", "count": 12},
                    {"status": "Cancelled", "count": 1},
                    {"status": "Draft", "count": 2},
                ],
            }
        }
    )

    monthly_sales: list[MonthlySalesPoint]
    monthly_purchases: list[MonthlyPurchasesPoint]
    fish_sales: list[FishSalesPoint]
    trip_status: list[TripStatusPoint]


class TopCustomerItem(BaseModel):
    """One row of TASKS.md Sprint 10 Session 4 "WIDGET 1 Top Customers" -
    top 5 by `total_sales` descending, computed from non-draft/cancelled
    invoices only. `outstanding_amount` is the same reconciled
    `companies.outstanding_amount` cache `DashboardFinancial.
    customer_outstanding` sums, never re-derived here."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "company_id": "3d6f6c2e-2b7e-4b0a-9b0e-8f4b2a1c9d10",
                "company_name": "Konkan Seafoods",
                "total_sales": "184320.00",
                "invoice_count": 12,
                "outstanding_amount": "24500.00",
            }
        }
    )

    company_id: uuid.UUID
    company_name: str
    total_sales: Decimal
    invoice_count: int
    outstanding_amount: Decimal


class TopSupplierItem(BaseModel):
    """One row of TASKS.md Sprint 10 Session 4 "WIDGET 2 Top Suppliers" -
    mirrors TopCustomerItem on the buy side, ordered by `purchase_total`
    descending."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "supplier_id": "9c1a4b7d-5e2f-4a6b-8c3d-1f0e9a8b7c6d",
                "supplier_name": "Ratnagiri Fish Traders",
                "purchase_total": "96400.00",
                "purchase_bill_count": 8,
                "outstanding_amount": "12800.00",
            }
        }
    )

    supplier_id: uuid.UUID
    supplier_name: str
    purchase_total: Decimal
    purchase_bill_count: int
    outstanding_amount: Decimal


class TopFishItem(BaseModel):
    """One row of TASKS.md Sprint 10 Session 4 "WIDGET 3 Top Fish" - top 5
    by `sales_amount` descending, same non-draft/cancelled definition as
    the Session 3 chart's FishSalesPoint, plus `fish_id` for the widget's
    own drill-down navigation to `/fish/{id}`."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fish_id": "5a4b3c2d-1e0f-4a9b-8c7d-6e5f4a3b2c1d",
                "fish_name": "Pomfret",
                "quantity_sold": "820.500",
                "sales_amount": "184320.00",
            }
        }
    )

    fish_id: uuid.UUID
    fish_name: str
    quantity_sold: Decimal
    sales_amount: Decimal


class OutstandingSummary(BaseModel):
    """TASKS.md Sprint 10 Session 4 "WIDGET 4 Outstanding Summary" -
    `customer_outstanding`/`supplier_outstanding` are the same totals
    already in `DashboardFinancial` (read once, reused here rather than
    re-queried); `customer_overdue`/`supplier_overdue` are the overdue
    subset of each (open status, past due date, balance outstanding) -
    the same amounts summed alongside `InvoiceAggregates.overdue_count`/
    `PurchaseBillAggregates.overdue_count`."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_outstanding": "184200.00",
                "customer_overdue": "42300.00",
                "supplier_outstanding": "76500.00",
                "supplier_overdue": "15400.00",
            }
        }
    )

    customer_outstanding: Decimal
    customer_overdue: Decimal
    supplier_outstanding: Decimal
    supplier_overdue: Decimal


class DashboardWidgets(BaseModel):
    """TASKS.md Sprint 10 Session 4's "widgets" section - four business-
    intelligence widgets added to the existing GET /dashboard response. No
    new endpoint: `useDashboard()` is extended, not duplicated."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "top_customers": [
                    {
                        "company_id": "3d6f6c2e-2b7e-4b0a-9b0e-8f4b2a1c9d10",
                        "company_name": "Konkan Seafoods",
                        "total_sales": "184320.00",
                        "invoice_count": 12,
                        "outstanding_amount": "24500.00",
                    }
                ],
                "top_suppliers": [
                    {
                        "supplier_id": "9c1a4b7d-5e2f-4a6b-8c3d-1f0e9a8b7c6d",
                        "supplier_name": "Ratnagiri Fish Traders",
                        "purchase_total": "96400.00",
                        "purchase_bill_count": 8,
                        "outstanding_amount": "12800.00",
                    }
                ],
                "top_fish": [
                    {
                        "fish_id": "5a4b3c2d-1e0f-4a9b-8c7d-6e5f4a3b2c1d",
                        "fish_name": "Pomfret",
                        "quantity_sold": "820.500",
                        "sales_amount": "184320.00",
                    }
                ],
                "outstanding_summary": {
                    "customer_outstanding": "184200.00",
                    "customer_overdue": "42300.00",
                    "supplier_outstanding": "76500.00",
                    "supplier_overdue": "15400.00",
                },
            }
        }
    )

    top_customers: list[TopCustomerItem]
    top_suppliers: list[TopSupplierItem]
    top_fish: list[TopFishItem]
    outstanding_summary: OutstandingSummary


class DashboardResponse(BaseModel):
    """GET /dashboard's single consolidated response body. Five sections
    from TASKS.md Sprint 10 Session 1, plus `charts` added by Session 3
    (the sketch at the top of Session 1's spec also lists a separate
    "outstanding" key, but Section 3 folds customer/supplier outstanding
    into `financial` instead - the numbered section list is the
    authoritative shape), plus `widgets` added by Session 4 (top
    customers/suppliers/fish, outstanding summary)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "kpis": {
                    "todays_sales": "48250.00",
                    "monthly_sales": "612400.00",
                    "customer_payments_today": "35000.00",
                    "supplier_payments_today": "12000.00",
                    "active_trips": 3,
                    "boats_at_sea": 2,
                    "todays_catch_quantity": "1250.500",
                    "draft_invoices": 4,
                    "draft_payments": 1,
                },
                "operations": {
                    "trips_today": 2,
                    "trips_active": 3,
                    "trips_completed_today": 1,
                    "boats_available": 4,
                    "boats_at_sea": 2,
                    "boats_maintenance": 1,
                },
                "financial": {
                    "customer_outstanding": "184200.00",
                    "supplier_outstanding": "76500.00",
                    "invoices_issued_this_month": 42,
                    "purchase_bills_this_month": 15,
                },
                "recent_activity": [
                    {
                        "type": "invoice",
                        "reference": "INV/2026-27/00042",
                        "title": "Invoice to Konkan Seafoods",
                        "created_at": "2026-07-28T05:12:00Z",
                    }
                ],
                "alerts": [
                    {
                        "type": "invoice_overdue",
                        "count": 3,
                        "message": "3 invoices are overdue",
                    }
                ],
                "charts": {
                    "monthly_sales": [
                        {"month": "2026-07-01", "sales_amount": "612400.00", "invoice_count": 42}
                    ],
                    "monthly_purchases": [
                        {
                            "month": "2026-07-01",
                            "purchase_amount": "241800.00",
                            "purchase_bill_count": 15,
                        }
                    ],
                    "fish_sales": [
                        {
                            "fish_name": "Pomfret",
                            "quantity_sold": "820.500",
                            "sales_amount": "184320.00",
                        }
                    ],
                    "trip_status": [
                        {"status": "Active", "count": 3},
                        {"status": "Completed", "count": 12},
                        {"status": "Cancelled", "count": 1},
                        {"status": "Draft", "count": 2},
                    ],
                },
                "widgets": {
                    "top_customers": [
                        {
                            "company_id": "3d6f6c2e-2b7e-4b0a-9b0e-8f4b2a1c9d10",
                            "company_name": "Konkan Seafoods",
                            "total_sales": "184320.00",
                            "invoice_count": 12,
                            "outstanding_amount": "24500.00",
                        }
                    ],
                    "top_suppliers": [
                        {
                            "supplier_id": "9c1a4b7d-5e2f-4a6b-8c3d-1f0e9a8b7c6d",
                            "supplier_name": "Ratnagiri Fish Traders",
                            "purchase_total": "96400.00",
                            "purchase_bill_count": 8,
                            "outstanding_amount": "12800.00",
                        }
                    ],
                    "top_fish": [
                        {
                            "fish_id": "5a4b3c2d-1e0f-4a9b-8c7d-6e5f4a3b2c1d",
                            "fish_name": "Pomfret",
                            "quantity_sold": "820.500",
                            "sales_amount": "184320.00",
                        }
                    ],
                    "outstanding_summary": {
                        "customer_outstanding": "184200.00",
                        "customer_overdue": "42300.00",
                        "supplier_outstanding": "76500.00",
                        "supplier_overdue": "15400.00",
                    },
                },
            }
        }
    )

    kpis: DashboardKPIs
    operations: DashboardOperations
    financial: DashboardFinancial
    recent_activity: list[RecentActivityItem]
    alerts: list[AlertItem]
    charts: DashboardCharts
    widgets: DashboardWidgets


class _RecentActivityRow(BaseModel):
    """Internal shape a single-table recent-activity query maps its row
    into, before DashboardService merges the five sources and sorts.
    Not part of the public API - never returned directly by the router."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    reference: str
    title: str
    created_at: datetime
