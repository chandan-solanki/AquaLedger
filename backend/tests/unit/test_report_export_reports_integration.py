"""Sprint 11 Session 5 Phase A - smoke tests for the 9
ReportsService.build_*_export_data() methods (TASKS.md's "REPORTS MODULE"
requirement: "Every existing report service must expose build_export_data()
which converts existing report DTOs -> ReportExportData"). Each method is a
pure, static DTO-to-DTO mapping (no DB, no new calculation), so these
construct a minimal, already-computed Response object directly from the
existing Pydantic schemas and assert the resulting ReportExportData is
well-formed - catching any attribute-name mismatch between a report's own
schema and its export column/summary mapping.
"""

import uuid
from datetime import date
from decimal import Decimal

from app.common.schemas import PaginationMeta
from app.modules.reports.schemas import (
    AgingReportResponse,
    AgingReportRow,
    AgingReportSummary,
    BoatProfitabilityResponse,
    BoatProfitabilityRow,
    BoatProfitabilitySummary,
    CustomerLedgerCustomer,
    CustomerLedgerEntry,
    CustomerLedgerResponse,
    CustomerLedgerSummary,
    FishSalesResponse,
    FishSalesRow,
    FishSalesSummary,
    OutstandingReportResponse,
    OutstandingReportRow,
    OutstandingReportSummary,
    PurchaseReportResponse,
    PurchaseReportRow,
    PurchaseReportSummary,
    SalesReportResponse,
    SalesReportRow,
    SalesReportSummary,
    SupplierLedgerEntry,
    SupplierLedgerResponse,
    SupplierLedgerSummary,
    SupplierLedgerSupplier,
    TripProfitabilityResponse,
    TripProfitabilityRow,
    TripProfitabilitySummary,
)
from app.modules.reports.service import ReportsService

_PAGINATION = PaginationMeta(
    total_records=1, total_pages=1, current_page=1, page_size=20, has_next=False, has_previous=False
)
_GENERATED_BY = "admin@fisherp.test"
_TENANT_NAME = "Konkan Traders"


class TestBuildCustomerLedgerExportData:
    def test_converts_response_into_export_data(self) -> None:
        response = CustomerLedgerResponse(
            customer=CustomerLedgerCustomer(
                id=uuid.uuid4(), name="Konkan Seafoods", code="CO-0001"
            ),
            summary=CustomerLedgerSummary(
                opening_balance=Decimal("100.00"),
                total_debit=Decimal("200.00"),
                total_credit=Decimal("50.00"),
                closing_balance=Decimal("250.00"),
                invoice_count=2,
                payment_count=1,
            ),
            entries=[
                CustomerLedgerEntry(
                    transaction_date=date(2026, 7, 1),
                    reference_number="INV-1",
                    transaction_type="invoice",
                    description="Sales Invoice",
                    debit=Decimal("200.00"),
                    credit=Decimal("0.00"),
                    running_balance=Decimal("300.00"),
                )
            ],
            pagination=_PAGINATION,
        )

        data = ReportsService.build_customer_ledger_export_data(
            response, generated_by=_GENERATED_BY, tenant_name=_TENANT_NAME
        )

        assert data.title == "Customer Ledger"
        assert data.subtitle == "Konkan Seafoods (CO-0001)"
        assert data.generated_by == _GENERATED_BY
        assert data.tenant_name == _TENANT_NAME
        assert len(data.rows) == 1
        assert data.rows[0].data["transaction_type"] == "invoice"
        assert len(data.summary) == 6


class TestBuildSupplierLedgerExportData:
    def test_converts_response_into_export_data(self) -> None:
        response = SupplierLedgerResponse(
            supplier=SupplierLedgerSupplier(
                id=uuid.uuid4(), name="Coastal Fish Suppliers", code="SUP-001"
            ),
            summary=SupplierLedgerSummary(
                opening_balance=Decimal("0.00"),
                total_debit=Decimal("100.00"),
                total_credit=Decimal("50.00"),
                closing_balance=Decimal("50.00"),
                purchase_bill_count=1,
                supplier_payment_count=1,
            ),
            entries=[
                SupplierLedgerEntry(
                    transaction_date=date(2026, 7, 1),
                    reference_number="PB-1",
                    transaction_type="purchase_bill",
                    description="Purchase Bill",
                    debit=Decimal("100.00"),
                    credit=Decimal("0.00"),
                    running_balance=Decimal("100.00"),
                )
            ],
            pagination=_PAGINATION,
        )

        data = ReportsService.build_supplier_ledger_export_data(
            response, generated_by=_GENERATED_BY, tenant_name=_TENANT_NAME
        )

        assert data.title == "Supplier Ledger"
        assert data.subtitle == "Coastal Fish Suppliers (SUP-001)"
        assert len(data.rows) == 1
        assert len(data.summary) == 6


class TestBuildSalesReportExportData:
    def test_converts_response_into_export_data(self) -> None:
        response = SalesReportResponse(
            summary=SalesReportSummary(
                total_sales=Decimal("100.00"),
                total_paid=Decimal("50.00"),
                outstanding=Decimal("50.00"),
                invoice_count=1,
                average_invoice=Decimal("100.00"),
                largest_invoice=Decimal("100.00"),
            ),
            rows=[
                SalesReportRow(
                    invoice_id=uuid.uuid4(),
                    invoice_number="INV-1",
                    invoice_date=date(2026, 7, 1),
                    due_date=date(2026, 7, 15),
                    customer_name="Konkan Seafoods",
                    invoice_amount=Decimal("100.00"),
                    paid_amount=Decimal("50.00"),
                    outstanding_amount=Decimal("50.00"),
                    status="partially_paid",
                )
            ],
            pagination=_PAGINATION,
        )

        data = ReportsService.build_sales_report_export_data(
            response, generated_by=_GENERATED_BY, tenant_name=_TENANT_NAME
        )

        assert data.title == "Sales Report"
        assert data.rows[0].data["status"] == "partially_paid"
        assert len(data.summary) == 6


class TestBuildPurchaseReportExportData:
    def test_converts_response_into_export_data(self) -> None:
        response = PurchaseReportResponse(
            summary=PurchaseReportSummary(
                total_purchases=Decimal("100.00"),
                total_paid=Decimal("50.00"),
                outstanding=Decimal("50.00"),
                bill_count=1,
                average_bill=Decimal("100.00"),
                largest_bill=Decimal("100.00"),
            ),
            rows=[
                PurchaseReportRow(
                    bill_id=uuid.uuid4(),
                    bill_number="PUR-1",
                    bill_date=date(2026, 7, 1),
                    due_date=date(2026, 8, 1),
                    supplier_name="Coastal Fish Suppliers",
                    bill_amount=Decimal("100.00"),
                    paid_amount=Decimal("50.00"),
                    outstanding_amount=Decimal("50.00"),
                    status="partially_paid",
                )
            ],
            pagination=_PAGINATION,
        )

        data = ReportsService.build_purchase_report_export_data(
            response, generated_by=_GENERATED_BY, tenant_name=_TENANT_NAME
        )

        assert data.title == "Purchase Report"
        assert len(data.rows) == 1
        assert len(data.summary) == 6


class TestBuildOutstandingReportExportData:
    def test_customer_variant_uses_customer_labels(self) -> None:
        response = OutstandingReportResponse(
            entity_type="customer",
            summary=OutstandingReportSummary(
                accounts_receivable=Decimal("100.00"),
                accounts_payable=Decimal("50.00"),
                net_position=Decimal("50.00"),
                overdue_receivable=Decimal("10.00"),
                overdue_payable=Decimal("5.00"),
                customers_with_outstanding=1,
                suppliers_with_outstanding=1,
            ),
            rows=[
                OutstandingReportRow(
                    entity_id=uuid.uuid4(),
                    entity_name="Konkan Seafoods",
                    entity_code="CO-0001",
                    outstanding_amount=Decimal("100.00"),
                    overdue_amount=Decimal("10.00"),
                    current_amount=Decimal("90.00"),
                    last_transaction_date=date(2026, 7, 1),
                    last_payment_date=date(2026, 6, 1),
                    pending_count=2,
                    risk_level="medium",
                )
            ],
            pagination=_PAGINATION,
        )

        data = ReportsService.build_outstanding_report_export_data(
            response, generated_by=_GENERATED_BY, tenant_name=_TENANT_NAME
        )

        assert data.subtitle == "Customer Outstanding"
        assert data.columns[0].title == "Customer"
        assert data.rows[0].data["risk_level"] == "medium"
        assert len(data.summary) == 7

    def test_supplier_variant_uses_supplier_labels(self) -> None:
        response = OutstandingReportResponse(
            entity_type="supplier",
            summary=OutstandingReportSummary(
                accounts_receivable=Decimal("100.00"),
                accounts_payable=Decimal("50.00"),
                net_position=Decimal("50.00"),
                overdue_receivable=Decimal("10.00"),
                overdue_payable=Decimal("5.00"),
                customers_with_outstanding=1,
                suppliers_with_outstanding=1,
            ),
            rows=[
                OutstandingReportRow(
                    entity_id=uuid.uuid4(),
                    entity_name="Coastal Fish Suppliers",
                    entity_code="SUP-001",
                    outstanding_amount=Decimal("50.00"),
                    overdue_amount=Decimal("5.00"),
                    current_amount=Decimal("45.00"),
                    last_transaction_date=None,
                    last_payment_date=None,
                    pending_count=1,
                    risk_level="low",
                )
            ],
            pagination=_PAGINATION,
        )

        data = ReportsService.build_outstanding_report_export_data(
            response, generated_by=_GENERATED_BY, tenant_name=_TENANT_NAME
        )

        assert data.subtitle == "Supplier Outstanding"
        assert data.columns[0].title == "Supplier"
        assert data.rows[0].data["last_transaction_date"] is None


class TestBuildAgingReportExportData:
    def test_converts_response_into_export_data(self) -> None:
        response = AgingReportResponse(
            entity_type="customer",
            summary=AgingReportSummary(
                current_total=Decimal("10.00"),
                days_1_30_total=Decimal("5.00"),
                days_31_60_total=Decimal("0.00"),
                days_61_90_total=Decimal("0.00"),
                days_90_plus_total=Decimal("0.00"),
                grand_total=Decimal("15.00"),
            ),
            rows=[
                AgingReportRow(
                    entity_id=uuid.uuid4(),
                    entity_name="Konkan Seafoods",
                    entity_code="CO-0001",
                    current_amount=Decimal("10.00"),
                    days_1_30=Decimal("5.00"),
                    days_31_60=Decimal("0.00"),
                    days_61_90=Decimal("0.00"),
                    days_90_plus=Decimal("0.00"),
                    total=Decimal("15.00"),
                    risk_level="low",
                )
            ],
            pagination=_PAGINATION,
        )

        data = ReportsService.build_aging_report_export_data(
            response, generated_by=_GENERATED_BY, tenant_name=_TENANT_NAME
        )

        assert data.title == "Aging Report"
        assert data.subtitle == "Customer Aging"
        assert len(data.summary) == 6
        # risk_level is not one of this report's displayed columns
        assert "risk_level" not in {column.key for column in data.columns}


class TestBuildTripProfitabilityExportData:
    def test_converts_response_into_export_data(self) -> None:
        response = TripProfitabilityResponse(
            summary=TripProfitabilitySummary(
                total_revenue=Decimal("100.00"),
                total_expenses=Decimal("20.00"),
                total_profit=Decimal("80.00"),
                average_profit_per_trip=Decimal("80.00"),
                average_revenue_per_trip=Decimal("100.00"),
                most_profitable_trip_number="TRIP-1",
                most_profitable_trip_profit=Decimal("80.00"),
                loss_making_trips=0,
            ),
            rows=[
                TripProfitabilityRow(
                    trip_id=uuid.uuid4(),
                    trip_number="TRIP-1",
                    boat_id=uuid.uuid4(),
                    boat_name="MV Sagar Kanya",
                    departure_date=date(2026, 7, 1),
                    return_date=date(2026, 7, 5),
                    status="returned",
                    revenue=Decimal("100.00"),
                    expenses=Decimal("20.00"),
                    profit=Decimal("80.00"),
                    profit_margin_percent=Decimal("80.00"),
                )
            ],
            pagination=_PAGINATION,
        )

        data = ReportsService.build_trip_profitability_export_data(
            response, generated_by=_GENERATED_BY, tenant_name=_TENANT_NAME
        )

        assert data.title == "Trip Profitability"
        assert data.rows[0].data["status"] == "returned"
        assert len(data.summary) == 8


class TestBuildBoatProfitabilityExportData:
    def test_converts_response_into_export_data(self) -> None:
        response = BoatProfitabilityResponse(
            summary=BoatProfitabilitySummary(
                fleet_revenue=Decimal("100.00"),
                fleet_expenses=Decimal("20.00"),
                fleet_profit=Decimal("80.00"),
                fleet_margin_percent=Decimal("80.00"),
                total_boats=1,
                active_boats=1,
                average_profit_per_boat=Decimal("80.00"),
                most_profitable_boat_name="MV Sagar Kanya",
                most_profitable_boat_profit=Decimal("80.00"),
            ),
            rows=[
                BoatProfitabilityRow(
                    boat_id=uuid.uuid4(),
                    boat_name="MV Sagar Kanya",
                    registration_number="REG-2026-0007",
                    total_trips=1,
                    revenue=Decimal("100.00"),
                    expenses=Decimal("20.00"),
                    profit=Decimal("80.00"),
                    profit_margin_percent=Decimal("80.00"),
                    average_profit_per_trip=Decimal("80.00"),
                    average_revenue_per_trip=Decimal("100.00"),
                    best_trip_profit=Decimal("80.00"),
                    worst_trip_profit=Decimal("80.00"),
                    last_trip_date=date(2026, 7, 5),
                )
            ],
            pagination=_PAGINATION,
        )

        data = ReportsService.build_boat_profitability_export_data(
            response, generated_by=_GENERATED_BY, tenant_name=_TENANT_NAME
        )

        assert data.title == "Boat Profitability"
        assert len(data.columns) == 12
        assert len(data.summary) == 9


class TestBuildFishSalesExportData:
    def test_converts_response_into_export_data(self) -> None:
        response = FishSalesResponse(
            summary=FishSalesSummary(
                total_fish_sold=Decimal("10.000"),
                total_revenue=Decimal("1000.00"),
                average_selling_price=Decimal("100.0000"),
                best_selling_fish_name="Pomfret",
                best_selling_fish_quantity=Decimal("10.000"),
                highest_revenue_fish_name="Pomfret",
                highest_revenue_fish_revenue=Decimal("1000.00"),
                total_fish_types_sold=1,
            ),
            rows=[
                FishSalesRow(
                    fish_id=uuid.uuid4(),
                    fish_name="Pomfret",
                    scientific_name="Pampus argenteus",
                    unit="kg",
                    quantity_sold=Decimal("10.000"),
                    revenue=Decimal("1000.00"),
                    average_selling_price=Decimal("100.0000"),
                    invoice_count=1,
                    trip_count=1,
                    customer_count=1,
                    last_sold_date=date(2026, 7, 1),
                )
            ],
            pagination=_PAGINATION,
        )

        data = ReportsService.build_fish_sales_export_data(
            response, generated_by=_GENERATED_BY, tenant_name=_TENANT_NAME
        )

        assert data.title == "Fish Sales Analytics"
        assert data.rows[0].data["unit"] == "kg"
        assert len(data.summary) == 8

    def test_zero_rows_still_produces_valid_export_data(self) -> None:
        """A tenant with no sales yet - every summary figure is None/zero,
        never a crash (mirrors FishSalesSummary's own zero-safe posture)."""
        response = FishSalesResponse(
            summary=FishSalesSummary(
                total_fish_sold=Decimal("0"),
                total_revenue=Decimal("0.00"),
                average_selling_price=Decimal("0.0000"),
                best_selling_fish_name=None,
                best_selling_fish_quantity=None,
                highest_revenue_fish_name=None,
                highest_revenue_fish_revenue=None,
                total_fish_types_sold=0,
            ),
            rows=[],
            pagination=_PAGINATION,
        )

        data = ReportsService.build_fish_sales_export_data(
            response, generated_by=_GENERATED_BY, tenant_name=_TENANT_NAME
        )

        assert data.rows == []
        assert data.summary[3].value is None
