import math
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import PaginationMeta
from app.core.report_export.export_models import (
    ColumnAlignment,
    ColumnFormat,
    ReportColumn,
    ReportExportData,
    ReportFilterDisplay,
    ReportRow,
    ReportSummary,
)
from app.modules.companies.exceptions import CompanyNotFoundError
from app.modules.companies.schemas import CompanyResponse
from app.modules.companies.service import CompanyService
from app.modules.reports.exceptions import ReportCustomerNotFoundError, ReportSupplierNotFoundError
from app.modules.reports.repository import (
    BoatProfitabilityRowData,
    FishSalesHistoryRowData,
    FishSalesRowData,
    LedgerRow,
    ReportsRepository,
    TripProfitabilityRowData,
)
from app.modules.reports.schemas import (
    AgingReportParams,
    AgingReportResponse,
    AgingReportRow,
    AgingReportSummary,
    BoatProfitabilityParams,
    BoatProfitabilityResponse,
    BoatProfitabilityRow,
    BoatProfitabilitySummary,
    CustomerLedgerCustomer,
    CustomerLedgerEntry,
    CustomerLedgerParams,
    CustomerLedgerResponse,
    CustomerLedgerSummary,
    FishSalesHistoryParams,
    FishSalesHistoryResponse,
    FishSalesHistoryRow,
    FishSalesParams,
    FishSalesResponse,
    FishSalesRow,
    FishSalesSummary,
    OutstandingReportParams,
    OutstandingReportResponse,
    OutstandingReportRow,
    OutstandingReportSummary,
    PurchaseReportParams,
    PurchaseReportResponse,
    PurchaseReportRow,
    PurchaseReportSummary,
    SalesReportParams,
    SalesReportResponse,
    SalesReportRow,
    SalesReportSummary,
    SupplierLedgerEntry,
    SupplierLedgerParams,
    SupplierLedgerResponse,
    SupplierLedgerSummary,
    SupplierLedgerSupplier,
    TripProfitabilityParams,
    TripProfitabilityResponse,
    TripProfitabilityRow,
    TripProfitabilitySummary,
)
from app.modules.suppliers.exceptions import SupplierNotFoundError
from app.modules.suppliers.schemas import SupplierResponse
from app.modules.suppliers.service import SupplierService


class ReportsService:
    """Sprint 11 Session 1 - the Customer Ledger, the first report this
    module builds. Read-only: no create/update/delete anywhere in this
    module. Every number returned is computed server-side from the
    invoices/payments modules' own tables (via ReportsRepository) - never
    from a cached/denormalized balance. `Company.outstanding_amount` is
    deliberately never read here (TASKS.md: "Do NOT calculate the ledger
    from cached outstanding balances").

    Opening Balance, each entry's running_balance, Closing Balance, Total
    Debit/Credit and Invoice/Payment Count in the summary always reflect the
    customer's true account balance for the requested date range - the
    `transaction_type` filter only narrows which rows come back in
    `entries` (and which rows count toward `pagination`), it never changes
    any of those summary/balance figures. See
    ReportsRepository.get_ledger_page's docstring for how the running
    balance stays correct under that filter.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ReportsRepository(session)
        # Cross-module reference validation goes through the other module's
        # service, never its repository (ARCHITECTURE.md §2).
        self._company_service = CompanyService(session)
        self._supplier_service = SupplierService(session)

    async def get_customer_ledger(
        self, params: CustomerLedgerParams, *, tenant_id: uuid.UUID
    ) -> CustomerLedgerResponse:
        customer = await self._ensure_customer(params.customer_id, tenant_id)

        opening_balance = await self._repo.get_opening_balance(
            tenant_id, params.customer_id, before_date=params.from_date
        )
        aggregates = await self._repo.get_summary_aggregates(
            tenant_id, params.customer_id, from_date=params.from_date, to_date=params.to_date
        )
        rows, total = await self._repo.get_ledger_page(
            tenant_id,
            params.customer_id,
            from_date=params.from_date,
            to_date=params.to_date,
            transaction_type=params.transaction_type,
            page=params.page,
            page_size=params.page_size,
        )

        opening_balance = self._money(opening_balance)
        total_debit = self._money(aggregates.total_debit)
        total_credit = self._money(aggregates.total_credit)
        closing_balance = self._money(opening_balance + total_debit - total_credit)
        total_pages = math.ceil(total / params.page_size) if total else 0
        pagination = PaginationMeta(
            total_records=total,
            total_pages=total_pages,
            current_page=params.page,
            page_size=params.page_size,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )

        return CustomerLedgerResponse(
            customer=CustomerLedgerCustomer(id=customer.id, name=customer.name, code=customer.code),
            summary=CustomerLedgerSummary(
                opening_balance=opening_balance,
                total_debit=total_debit,
                total_credit=total_credit,
                closing_balance=closing_balance,
                invoice_count=aggregates.invoice_count,
                payment_count=aggregates.payment_count,
            ),
            entries=[self._to_entry(row, opening_balance) for row in rows],
            pagination=pagination,
        )

    async def get_supplier_ledger(
        self, params: SupplierLedgerParams, *, tenant_id: uuid.UUID
    ) -> SupplierLedgerResponse:
        """Mirrors get_customer_ledger exactly, on the buy side - generated
        entirely from posted purchase bills (debit) and posted supplier
        payments (credit), never from `Supplier.outstanding_amount`."""
        supplier = await self._ensure_supplier(params.supplier_id, tenant_id)

        opening_balance = await self._repo.get_supplier_opening_balance(
            tenant_id, params.supplier_id, before_date=params.from_date
        )
        aggregates = await self._repo.get_supplier_summary_aggregates(
            tenant_id, params.supplier_id, from_date=params.from_date, to_date=params.to_date
        )
        rows, total = await self._repo.get_supplier_ledger_page(
            tenant_id,
            params.supplier_id,
            from_date=params.from_date,
            to_date=params.to_date,
            transaction_type=params.transaction_type,
            page=params.page,
            page_size=params.page_size,
        )

        opening_balance = self._money(opening_balance)
        total_debit = self._money(aggregates.total_debit)
        total_credit = self._money(aggregates.total_credit)
        closing_balance = self._money(opening_balance + total_debit - total_credit)
        total_pages = math.ceil(total / params.page_size) if total else 0
        pagination = PaginationMeta(
            total_records=total,
            total_pages=total_pages,
            current_page=params.page,
            page_size=params.page_size,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )

        return SupplierLedgerResponse(
            supplier=SupplierLedgerSupplier(id=supplier.id, name=supplier.name, code=supplier.code),
            summary=SupplierLedgerSummary(
                opening_balance=opening_balance,
                total_debit=total_debit,
                total_credit=total_credit,
                closing_balance=closing_balance,
                purchase_bill_count=aggregates.purchase_bill_count,
                supplier_payment_count=aggregates.supplier_payment_count,
            ),
            entries=[self._to_supplier_entry(row, opening_balance) for row in rows],
            pagination=pagination,
        )

    async def get_sales_report(
        self, params: SalesReportParams, *, tenant_id: uuid.UUID
    ) -> SalesReportResponse:
        """Sprint 11 Session 3 - a plain filtered list of issued invoices,
        unlike the Ledgers above: one row per invoice, no running balance.
        No customer-existence validation - `customer_id` is an optional
        filter here (not the single required resource key a Ledger request
        revolves around), mirroring InvoiceListParams.company_id's own
        posture: an unmatched id simply yields zero rows."""
        rows, aggregates, total = await self._repo.get_sales_report(
            tenant_id,
            customer_id=params.customer_id,
            status=params.status,
            paid_status=params.paid_status,
            from_date=params.from_date,
            to_date=params.to_date,
            q=params.q,
            page=params.page,
            page_size=params.page_size,
        )
        total_pages = math.ceil(total / params.page_size) if total else 0
        pagination = PaginationMeta(
            total_records=total,
            total_pages=total_pages,
            current_page=params.page,
            page_size=params.page_size,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )

        return SalesReportResponse(
            summary=SalesReportSummary(
                total_sales=self._money(aggregates.total_sales),
                total_paid=self._money(aggregates.total_paid),
                outstanding=self._money(aggregates.outstanding),
                invoice_count=aggregates.invoice_count,
                average_invoice=self._money(aggregates.average_invoice),
                largest_invoice=self._money(aggregates.largest_invoice),
            ),
            rows=[
                SalesReportRow(
                    invoice_id=row.invoice_id,
                    invoice_number=row.invoice_number,
                    invoice_date=row.invoice_date,
                    due_date=row.due_date,
                    customer_name=row.customer_name,
                    invoice_amount=self._money(row.invoice_amount),
                    paid_amount=self._money(row.paid_amount),
                    outstanding_amount=self._money(row.outstanding_amount),
                    status=row.status,
                )
                for row in rows
            ],
            pagination=pagination,
        )

    async def get_purchase_report(
        self, params: PurchaseReportParams, *, tenant_id: uuid.UUID
    ) -> PurchaseReportResponse:
        """Mirrors get_sales_report exactly, on the buy side."""
        rows, aggregates, total = await self._repo.get_purchase_report(
            tenant_id,
            supplier_id=params.supplier_id,
            status=params.status,
            paid_status=params.paid_status,
            from_date=params.from_date,
            to_date=params.to_date,
            q=params.q,
            page=params.page,
            page_size=params.page_size,
        )
        total_pages = math.ceil(total / params.page_size) if total else 0
        pagination = PaginationMeta(
            total_records=total,
            total_pages=total_pages,
            current_page=params.page,
            page_size=params.page_size,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )

        return PurchaseReportResponse(
            summary=PurchaseReportSummary(
                total_purchases=self._money(aggregates.total_purchases),
                total_paid=self._money(aggregates.total_paid),
                outstanding=self._money(aggregates.outstanding),
                bill_count=aggregates.bill_count,
                average_bill=self._money(aggregates.average_bill),
                largest_bill=self._money(aggregates.largest_bill),
            ),
            rows=[
                PurchaseReportRow(
                    bill_id=row.bill_id,
                    bill_number=row.bill_number,
                    bill_date=row.bill_date,
                    due_date=row.due_date,
                    supplier_name=row.supplier_name,
                    bill_amount=self._money(row.bill_amount),
                    paid_amount=self._money(row.paid_amount),
                    outstanding_amount=self._money(row.outstanding_amount),
                    status=row.status,
                )
                for row in rows
            ],
            pagination=pagination,
        )

    async def get_outstanding_report(
        self, params: OutstandingReportParams, *, tenant_id: uuid.UUID
    ) -> OutstandingReportResponse:
        """Sprint 11 Session 3 Phase B - one row per customer or supplier,
        never per transaction. `summary` is always the full, unfiltered
        AR/AP picture (ReportsRepository.get_outstanding_summary's own
        docstring) - it does not change when `entity_type` or any row
        filter changes, only `rows`/`pagination` do. `today` is computed
        once here and passed to the repository (mirrors
        DashboardService's own today/month_start pattern) so every overdue/
        risk comparison in this request is based on the same instant."""
        today = datetime.now(UTC).date()

        summary_agg = await self._repo.get_outstanding_summary(tenant_id, today=today)
        rows, total = await self._repo.get_outstanding_rows(
            tenant_id,
            entity_type=params.entity_type,
            today=today,
            from_date=params.from_date,
            to_date=params.to_date,
            outstanding_only=params.outstanding_only,
            overdue_only=params.overdue_only,
            risk_level=params.risk_level,
            q=params.q,
            page=params.page,
            page_size=params.page_size,
        )

        total_pages = math.ceil(total / params.page_size) if total else 0
        pagination = PaginationMeta(
            total_records=total,
            total_pages=total_pages,
            current_page=params.page,
            page_size=params.page_size,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )

        accounts_receivable = self._money(summary_agg.accounts_receivable)
        accounts_payable = self._money(summary_agg.accounts_payable)
        return OutstandingReportResponse(
            entity_type=params.entity_type,
            summary=OutstandingReportSummary(
                accounts_receivable=accounts_receivable,
                accounts_payable=accounts_payable,
                net_position=accounts_receivable - accounts_payable,
                overdue_receivable=self._money(summary_agg.overdue_receivable),
                overdue_payable=self._money(summary_agg.overdue_payable),
                customers_with_outstanding=summary_agg.customers_with_outstanding,
                suppliers_with_outstanding=summary_agg.suppliers_with_outstanding,
            ),
            rows=[
                OutstandingReportRow(
                    entity_id=row.entity_id,
                    entity_name=row.entity_name,
                    entity_code=row.entity_code,
                    outstanding_amount=self._money(row.outstanding_amount),
                    overdue_amount=self._money(row.overdue_amount),
                    current_amount=self._money(row.current_amount),
                    last_transaction_date=row.last_transaction_date,
                    last_payment_date=row.last_payment_date,
                    pending_count=row.pending_count,
                    risk_level=row.risk_level,
                )
                for row in rows
            ],
            pagination=pagination,
        )

    async def get_aging_report(
        self, params: AgingReportParams, *, tenant_id: uuid.UUID
    ) -> AgingReportResponse:
        """Sprint 11 Session 3 Phase B - unlike get_outstanding_report,
        `summary` here IS scoped to `entity_type` and every row filter
        (outstanding_only/risk_level/q) - see AgingReportSummary's own
        docstring for why that asymmetry is intentional."""
        today = datetime.now(UTC).date()

        rows, summary_agg, total = await self._repo.get_aging_report(
            tenant_id,
            entity_type=params.entity_type,
            today=today,
            outstanding_only=params.outstanding_only,
            risk_level=params.risk_level,
            q=params.q,
            page=params.page,
            page_size=params.page_size,
        )

        total_pages = math.ceil(total / params.page_size) if total else 0
        pagination = PaginationMeta(
            total_records=total,
            total_pages=total_pages,
            current_page=params.page,
            page_size=params.page_size,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )

        return AgingReportResponse(
            entity_type=params.entity_type,
            summary=AgingReportSummary(
                current_total=self._money(summary_agg.current_total),
                days_1_30_total=self._money(summary_agg.days_1_30_total),
                days_31_60_total=self._money(summary_agg.days_31_60_total),
                days_61_90_total=self._money(summary_agg.days_61_90_total),
                days_90_plus_total=self._money(summary_agg.days_90_plus_total),
                grand_total=self._money(summary_agg.grand_total),
            ),
            rows=[
                AgingReportRow(
                    entity_id=row.entity_id,
                    entity_name=row.entity_name,
                    entity_code=row.entity_code,
                    current_amount=self._money(row.current_amount),
                    days_1_30=self._money(row.days_1_30),
                    days_31_60=self._money(row.days_31_60),
                    days_61_90=self._money(row.days_61_90),
                    days_90_plus=self._money(row.days_90_plus),
                    total=self._money(row.total),
                    risk_level=row.risk_level,
                )
                for row in rows
            ],
            pagination=pagination,
        )

    async def get_trip_profitability(
        self, params: TripProfitabilityParams, *, tenant_id: uuid.UUID
    ) -> TripProfitabilityResponse:
        """Sprint 11 Session 4 Phase A - one row per completed trip. Revenue/
        expenses/profit are entirely SQL-aggregated
        (ReportsRepository.get_trip_profitability); `profit_margin_percent`
        is the one piece of arithmetic done here, in Python, not React
        (mirrors OutstandingReportResponse's own `net_position`) - a plain
        ratio of two already-fetched Decimals, guarded against a zero-
        revenue trip."""
        rows, aggregates, total = await self._repo.get_trip_profitability(
            tenant_id,
            boat_id=params.boat_id,
            from_date=params.from_date,
            to_date=params.to_date,
            profitability=params.profitability,
            q=params.q,
            page=params.page,
            page_size=params.page_size,
        )

        total_pages = math.ceil(total / params.page_size) if total else 0
        pagination = PaginationMeta(
            total_records=total,
            total_pages=total_pages,
            current_page=params.page,
            page_size=params.page_size,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )

        return TripProfitabilityResponse(
            summary=TripProfitabilitySummary(
                total_revenue=self._money(aggregates.total_revenue),
                total_expenses=self._money(aggregates.total_expenses),
                total_profit=self._money(aggregates.total_profit),
                average_profit_per_trip=self._money(aggregates.average_profit_per_trip),
                average_revenue_per_trip=self._money(aggregates.average_revenue_per_trip),
                most_profitable_trip_number=aggregates.most_profitable_trip_number,
                most_profitable_trip_profit=(
                    self._money(aggregates.most_profitable_trip_profit)
                    if aggregates.most_profitable_trip_profit is not None
                    else None
                ),
                loss_making_trips=aggregates.loss_making_trips,
            ),
            rows=[self._to_trip_profitability_row(row) for row in rows],
            pagination=pagination,
        )

    async def get_boat_profitability(
        self, params: BoatProfitabilityParams, *, tenant_id: uuid.UUID
    ) -> BoatProfitabilityResponse:
        """Sprint 11 Session 4 Phase A - one row per boat, aggregating every
        one of its completed trips (ReportsRepository.get_boat_profitability,
        built directly on top of the same per-trip base query
        get_trip_profitability uses - no duplicated calculation).
        `fleet_margin_percent` is computed here in Python from the already-
        fetched fleet_revenue/fleet_profit, guarded against zero fleet
        revenue."""
        rows, aggregates, total = await self._repo.get_boat_profitability(
            tenant_id,
            boat_id=params.boat_id,
            from_date=params.from_date,
            to_date=params.to_date,
            min_trips=params.min_trips,
            profitability=params.profitability,
            q=params.q,
            page=params.page,
            page_size=params.page_size,
        )

        total_pages = math.ceil(total / params.page_size) if total else 0
        pagination = PaginationMeta(
            total_records=total,
            total_pages=total_pages,
            current_page=params.page,
            page_size=params.page_size,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )

        fleet_revenue = self._money(aggregates.fleet_revenue)
        fleet_profit = self._money(aggregates.fleet_profit)
        average_profit_per_boat = (
            self._money(fleet_profit / aggregates.total_boats)
            if aggregates.total_boats
            else Decimal("0.00")
        )
        return BoatProfitabilityResponse(
            summary=BoatProfitabilitySummary(
                fleet_revenue=fleet_revenue,
                fleet_expenses=self._money(aggregates.fleet_expenses),
                fleet_profit=fleet_profit,
                fleet_margin_percent=self._margin(fleet_profit, fleet_revenue),
                total_boats=aggregates.total_boats,
                active_boats=aggregates.active_boats,
                average_profit_per_boat=average_profit_per_boat,
                most_profitable_boat_name=aggregates.most_profitable_boat_name,
                most_profitable_boat_profit=(
                    self._money(aggregates.most_profitable_boat_profit)
                    if aggregates.most_profitable_boat_profit is not None
                    else None
                ),
            ),
            rows=[self._to_boat_profitability_row(row) for row in rows],
            pagination=pagination,
        )

    @classmethod
    def _to_trip_profitability_row(cls, row: TripProfitabilityRowData) -> TripProfitabilityRow:
        revenue = cls._money(row.revenue)
        profit = cls._money(row.profit)
        return TripProfitabilityRow(
            trip_id=row.trip_id,
            trip_number=row.trip_number,
            boat_id=row.boat_id,
            boat_name=row.boat_name,
            departure_date=row.departure_datetime.date(),
            return_date=row.actual_return_datetime.date() if row.actual_return_datetime else None,
            status=row.status,
            revenue=revenue,
            expenses=cls._money(row.expenses),
            profit=profit,
            profit_margin_percent=cls._margin(profit, revenue),
        )

    @classmethod
    def _to_boat_profitability_row(cls, row: BoatProfitabilityRowData) -> BoatProfitabilityRow:
        revenue = cls._money(row.revenue)
        profit = cls._money(row.profit)
        return BoatProfitabilityRow(
            boat_id=row.boat_id,
            boat_name=row.boat_name,
            registration_number=row.registration_number,
            total_trips=row.total_trips,
            revenue=revenue,
            expenses=cls._money(row.expenses),
            profit=profit,
            profit_margin_percent=cls._margin(profit, revenue),
            average_profit_per_trip=cls._money(row.average_profit_per_trip),
            average_revenue_per_trip=cls._money(row.average_revenue_per_trip),
            best_trip_profit=cls._money(row.best_trip_profit),
            worst_trip_profit=cls._money(row.worst_trip_profit),
            last_trip_date=row.last_trip_date.date() if row.last_trip_date else None,
        )

    async def get_fish_sales(
        self, params: FishSalesParams, *, tenant_id: uuid.UUID
    ) -> FishSalesResponse:
        """Sprint 11 Session 4 Phase B - one row per fish, aggregated
        entirely from invoice items (never catch quantity). `summary` is
        computed over the full filtered set, not just the current page -
        the module's dominant discipline. `average_selling_price` (both
        per-row and fleet-wide) is the one piece of arithmetic done here,
        in Python, not React - a plain ratio of two already-fetched
        Decimals, zero-safe."""
        rows, aggregates, total = await self._repo.get_fish_sales(
            tenant_id,
            fish_id=params.fish_id,
            customer_id=params.customer_id,
            boat_id=params.boat_id,
            trip_id=params.trip_id,
            from_date=params.from_date,
            to_date=params.to_date,
            min_quantity=params.min_quantity,
            min_revenue=params.min_revenue,
            q=params.q,
            page=params.page,
            page_size=params.page_size,
        )

        total_pages = math.ceil(total / params.page_size) if total else 0
        pagination = PaginationMeta(
            total_records=total,
            total_pages=total_pages,
            current_page=params.page,
            page_size=params.page_size,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )

        total_fish_sold = aggregates.total_fish_sold
        total_revenue = self._money(aggregates.total_revenue)
        return FishSalesResponse(
            summary=FishSalesSummary(
                total_fish_sold=total_fish_sold,
                total_revenue=total_revenue,
                average_selling_price=self._average_price(total_revenue, total_fish_sold),
                best_selling_fish_name=aggregates.best_selling_fish_name,
                best_selling_fish_quantity=aggregates.best_selling_fish_quantity,
                highest_revenue_fish_name=aggregates.highest_revenue_fish_name,
                highest_revenue_fish_revenue=(
                    self._money(aggregates.highest_revenue_fish_revenue)
                    if aggregates.highest_revenue_fish_revenue is not None
                    else None
                ),
                total_fish_types_sold=aggregates.total_fish_types_sold,
            ),
            rows=[self._to_fish_sales_row(row) for row in rows],
            pagination=pagination,
        )

    @classmethod
    def _to_fish_sales_row(cls, row: FishSalesRowData) -> FishSalesRow:
        revenue = cls._money(row.revenue)
        return FishSalesRow(
            fish_id=row.fish_id,
            fish_name=row.fish_name,
            scientific_name=row.scientific_name,
            unit=row.unit,
            quantity_sold=row.quantity_sold,
            revenue=revenue,
            average_selling_price=cls._average_price(revenue, row.quantity_sold),
            invoice_count=row.invoice_count,
            trip_count=row.trip_count,
            customer_count=row.customer_count,
            last_sold_date=row.last_sold_date,
        )

    async def get_fish_sales_history(
        self, params: FishSalesHistoryParams, *, tenant_id: uuid.UUID
    ) -> FishSalesHistoryResponse:
        """The Fish Detail page's own Sales History section - one row per
        individual sale, never aggregated. No `fish_id` existence check:
        mirrors SalesReportParams.customer_id's own posture - an unmatched
        id simply yields zero rows, it never 404s."""
        rows, total = await self._repo.get_fish_sales_history(
            tenant_id, fish_id=params.fish_id, page=params.page, page_size=params.page_size
        )

        total_pages = math.ceil(total / params.page_size) if total else 0
        pagination = PaginationMeta(
            total_records=total,
            total_pages=total_pages,
            current_page=params.page,
            page_size=params.page_size,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )

        return FishSalesHistoryResponse(
            rows=[self._to_fish_sales_history_row(row) for row in rows],
            pagination=pagination,
        )

    @classmethod
    def _to_fish_sales_history_row(cls, row: FishSalesHistoryRowData) -> FishSalesHistoryRow:
        return FishSalesHistoryRow(
            invoice_id=row.invoice_id,
            invoice_number=row.invoice_number,
            invoice_date=row.invoice_date,
            customer_name=row.customer_name,
            boat_name=row.boat_name,
            trip_number=row.trip_number,
            quantity=row.quantity,
            unit_price=row.unit_price.quantize(Decimal("0.0001")),
            revenue=cls._money(row.revenue),
        )

    @staticmethod
    def _average_price(revenue: Decimal, quantity: Decimal) -> Decimal:
        """revenue / quantity, quantized to Rate scale (ARCHITECTURE.md
        §5.1 NUMERIC(12,4)) - guarded against zero quantity (a fish with no
        sold quantity has no meaningful average price, not a division
        error)."""
        if quantity == 0:
            return Decimal("0.0000")
        return (revenue / quantity).quantize(Decimal("0.0001"))

    @staticmethod
    def _margin(profit: Decimal, revenue: Decimal) -> Decimal:
        """profit / revenue * 100, quantized like every other money/percent
        figure in this report - guarded against a zero-revenue trip/boat
        (a trip with expenses but no sales yet is a 0% margin, not a
        division error)."""
        if revenue == 0:
            return Decimal("0.00")
        return (profit / revenue * 100).quantize(Decimal("0.01"))

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        """Quantizes to NUMERIC(14,2)'s 2 decimal places (ARCHITECTURE.md
        §5.1) before it ever reaches a response - money values computed
        entirely from real NUMERIC(14,2) columns already carry that scale
        after a DB round trip, but the `opening_balance == 0` shortcut
        (before_date is None) and a `SUM(...)` returning NULL over zero
        matching rows both produce a bare, unscaled Python `Decimal("0")` -
        this normalizes both cases to "0.00" instead of "0" so every money
        field in this report is consistently 2 decimals, never mixed."""
        return value.quantize(Decimal("0.01"))

    async def _ensure_customer(
        self, customer_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> CompanyResponse:
        # CompanyService.get() is already tenant-scoped, so a company
        # belonging to another tenant surfaces as "not found" here too - the
        # same "must belong to the current tenant" rule InvoiceService
        # applies to its own company_id. Status (active/inactive) is
        # deliberately not checked - a report is a read-only historical
        # view, unlike creating a new invoice, so it must stay viewable for
        # an inactive/closed customer too.
        try:
            return await self._company_service.get(customer_id, tenant_id=tenant_id)
        except CompanyNotFoundError as exc:
            raise ReportCustomerNotFoundError("The specified customer does not exist") from exc

    @classmethod
    def _to_entry(cls, row: LedgerRow, opening_balance: Decimal) -> CustomerLedgerEntry:
        return CustomerLedgerEntry(
            transaction_date=row.transaction_date,
            reference_number=row.reference_number,
            transaction_type=row.transaction_type,
            description=row.description,
            debit=cls._money(row.debit),
            credit=cls._money(row.credit),
            running_balance=cls._money(opening_balance + row.cumulative),
        )

    async def _ensure_supplier(
        self, supplier_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> SupplierResponse:
        # SupplierService.get() is already tenant-scoped, so a supplier
        # belonging to another tenant surfaces as "not found" here too.
        # Status is deliberately not checked - mirrors _ensure_customer's own
        # reasoning: a report is a read-only historical view.
        try:
            return await self._supplier_service.get(supplier_id, tenant_id=tenant_id)
        except SupplierNotFoundError as exc:
            raise ReportSupplierNotFoundError("The specified supplier does not exist") from exc

    @classmethod
    def _to_supplier_entry(cls, row: LedgerRow, opening_balance: Decimal) -> SupplierLedgerEntry:
        return SupplierLedgerEntry(
            transaction_date=row.transaction_date,
            reference_number=row.reference_number,
            transaction_type=row.transaction_type,
            description=row.description,
            debit=cls._money(row.debit),
            credit=cls._money(row.credit),
            running_balance=cls._money(opening_balance + row.cumulative),
        )

    # -- Export (TASKS.md Sprint 11 Session 5 Phase A) ----------------------
    #
    # Every report below gets a build_*_export_data() method converting its
    # own already-fetched Response into the shared engine's ReportExportData
    # (app.core.report_export.export_models) - pure DTO-to-DTO mapping, never
    # a new calculation and never a second DB round trip. `generated_by`/
    # `tenant_name`/`filters` are supplied by the caller (a future Phase B
    # export endpoint) since this service has no request/user context of its
    # own - only the already-computed Response is report-specific here.

    @staticmethod
    def _assemble_export_data(
        *,
        title: str,
        columns: list[ReportColumn],
        rows: list[ReportRow],
        summary: list[ReportSummary],
        generated_by: str,
        tenant_name: str,
        subtitle: str | None = None,
        filters: list[ReportFilterDisplay] | None = None,
    ) -> ReportExportData:
        return ReportExportData(
            title=title,
            subtitle=subtitle,
            filters=filters or [],
            columns=columns,
            rows=rows,
            summary=summary,
            generated_at=datetime.now(UTC),
            generated_by=generated_by,
            tenant_name=tenant_name,
        )

    @staticmethod
    def build_customer_ledger_export_data(
        response: CustomerLedgerResponse,
        *,
        generated_by: str,
        tenant_name: str,
        filters: list[ReportFilterDisplay] | None = None,
    ) -> ReportExportData:
        columns = [
            ReportColumn(title="Date", key="transaction_date", format=ColumnFormat.DATE),
            ReportColumn(title="Reference", key="reference_number"),
            ReportColumn(title="Transaction Type", key="transaction_type"),
            ReportColumn(title="Description", key="description"),
            ReportColumn(
                title="Debit",
                key="debit",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Credit",
                key="credit",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Running Balance",
                key="running_balance",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
        ]
        rows = [
            ReportRow(
                data={
                    "transaction_date": entry.transaction_date,
                    "reference_number": entry.reference_number,
                    "transaction_type": entry.transaction_type.value,
                    "description": entry.description,
                    "debit": entry.debit,
                    "credit": entry.credit,
                    "running_balance": entry.running_balance,
                }
            )
            for entry in response.entries
        ]
        summary = [
            ReportSummary(label="Opening Balance", value=response.summary.opening_balance),
            ReportSummary(label="Total Debit", value=response.summary.total_debit),
            ReportSummary(label="Total Credit", value=response.summary.total_credit),
            ReportSummary(label="Closing Balance", value=response.summary.closing_balance),
            ReportSummary(label="Invoice Count", value=response.summary.invoice_count),
            ReportSummary(label="Payment Count", value=response.summary.payment_count),
        ]
        return ReportsService._assemble_export_data(
            title="Customer Ledger",
            subtitle=f"{response.customer.name} ({response.customer.code})",
            columns=columns,
            rows=rows,
            summary=summary,
            generated_by=generated_by,
            tenant_name=tenant_name,
            filters=filters,
        )

    @staticmethod
    def build_supplier_ledger_export_data(
        response: SupplierLedgerResponse,
        *,
        generated_by: str,
        tenant_name: str,
        filters: list[ReportFilterDisplay] | None = None,
    ) -> ReportExportData:
        columns = [
            ReportColumn(title="Date", key="transaction_date", format=ColumnFormat.DATE),
            ReportColumn(title="Reference", key="reference_number"),
            ReportColumn(title="Transaction Type", key="transaction_type"),
            ReportColumn(title="Description", key="description"),
            ReportColumn(
                title="Debit",
                key="debit",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Credit",
                key="credit",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Running Balance",
                key="running_balance",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
        ]
        rows = [
            ReportRow(
                data={
                    "transaction_date": entry.transaction_date,
                    "reference_number": entry.reference_number,
                    "transaction_type": entry.transaction_type.value,
                    "description": entry.description,
                    "debit": entry.debit,
                    "credit": entry.credit,
                    "running_balance": entry.running_balance,
                }
            )
            for entry in response.entries
        ]
        summary = [
            ReportSummary(label="Opening Balance", value=response.summary.opening_balance),
            ReportSummary(label="Total Debit", value=response.summary.total_debit),
            ReportSummary(label="Total Credit", value=response.summary.total_credit),
            ReportSummary(label="Closing Balance", value=response.summary.closing_balance),
            ReportSummary(label="Purchase Bill Count", value=response.summary.purchase_bill_count),
            ReportSummary(
                label="Supplier Payment Count", value=response.summary.supplier_payment_count
            ),
        ]
        return ReportsService._assemble_export_data(
            title="Supplier Ledger",
            subtitle=f"{response.supplier.name} ({response.supplier.code})",
            columns=columns,
            rows=rows,
            summary=summary,
            generated_by=generated_by,
            tenant_name=tenant_name,
            filters=filters,
        )

    @staticmethod
    def build_sales_report_export_data(
        response: SalesReportResponse,
        *,
        generated_by: str,
        tenant_name: str,
        filters: list[ReportFilterDisplay] | None = None,
    ) -> ReportExportData:
        columns = [
            ReportColumn(title="Invoice Number", key="invoice_number"),
            ReportColumn(title="Invoice Date", key="invoice_date", format=ColumnFormat.DATE),
            ReportColumn(title="Due Date", key="due_date", format=ColumnFormat.DATE),
            ReportColumn(title="Customer", key="customer_name"),
            ReportColumn(
                title="Invoice Amount",
                key="invoice_amount",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Paid Amount",
                key="paid_amount",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Outstanding Amount",
                key="outstanding_amount",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(title="Status", key="status"),
        ]
        rows = [
            ReportRow(
                data={
                    "invoice_number": row.invoice_number,
                    "invoice_date": row.invoice_date,
                    "due_date": row.due_date,
                    "customer_name": row.customer_name,
                    "invoice_amount": row.invoice_amount,
                    "paid_amount": row.paid_amount,
                    "outstanding_amount": row.outstanding_amount,
                    "status": row.status.value,
                }
            )
            for row in response.rows
        ]
        summary = [
            ReportSummary(label="Total Sales", value=response.summary.total_sales),
            ReportSummary(label="Total Paid", value=response.summary.total_paid),
            ReportSummary(label="Outstanding", value=response.summary.outstanding),
            ReportSummary(label="Invoice Count", value=response.summary.invoice_count),
            ReportSummary(label="Average Invoice", value=response.summary.average_invoice),
            ReportSummary(label="Largest Invoice", value=response.summary.largest_invoice),
        ]
        return ReportsService._assemble_export_data(
            title="Sales Report",
            columns=columns,
            rows=rows,
            summary=summary,
            generated_by=generated_by,
            tenant_name=tenant_name,
            filters=filters,
        )

    @staticmethod
    def build_purchase_report_export_data(
        response: PurchaseReportResponse,
        *,
        generated_by: str,
        tenant_name: str,
        filters: list[ReportFilterDisplay] | None = None,
    ) -> ReportExportData:
        columns = [
            ReportColumn(title="Bill Number", key="bill_number"),
            ReportColumn(title="Bill Date", key="bill_date", format=ColumnFormat.DATE),
            ReportColumn(title="Due Date", key="due_date", format=ColumnFormat.DATE),
            ReportColumn(title="Supplier", key="supplier_name"),
            ReportColumn(
                title="Bill Amount",
                key="bill_amount",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Paid Amount",
                key="paid_amount",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Outstanding Amount",
                key="outstanding_amount",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(title="Status", key="status"),
        ]
        rows = [
            ReportRow(
                data={
                    "bill_number": row.bill_number,
                    "bill_date": row.bill_date,
                    "due_date": row.due_date,
                    "supplier_name": row.supplier_name,
                    "bill_amount": row.bill_amount,
                    "paid_amount": row.paid_amount,
                    "outstanding_amount": row.outstanding_amount,
                    "status": row.status.value,
                }
            )
            for row in response.rows
        ]
        summary = [
            ReportSummary(label="Total Purchases", value=response.summary.total_purchases),
            ReportSummary(label="Total Paid", value=response.summary.total_paid),
            ReportSummary(label="Outstanding", value=response.summary.outstanding),
            ReportSummary(label="Bill Count", value=response.summary.bill_count),
            ReportSummary(label="Average Bill", value=response.summary.average_bill),
            ReportSummary(label="Largest Bill", value=response.summary.largest_bill),
        ]
        return ReportsService._assemble_export_data(
            title="Purchase Report",
            columns=columns,
            rows=rows,
            summary=summary,
            generated_by=generated_by,
            tenant_name=tenant_name,
            filters=filters,
        )

    @staticmethod
    def build_outstanding_report_export_data(
        response: OutstandingReportResponse,
        *,
        generated_by: str,
        tenant_name: str,
        filters: list[ReportFilterDisplay] | None = None,
    ) -> ReportExportData:
        is_customer = response.entity_type.value == "customer"
        entity_label = "Customer" if is_customer else "Supplier"
        columns = [
            ReportColumn(title=entity_label, key="entity_name"),
            ReportColumn(
                title="Outstanding Amount",
                key="outstanding_amount",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Overdue Amount",
                key="overdue_amount",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Current Amount",
                key="current_amount",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Last Invoice Date" if is_customer else "Last Purchase Date",
                key="last_transaction_date",
                format=ColumnFormat.DATE,
            ),
            ReportColumn(
                title="Last Payment Date", key="last_payment_date", format=ColumnFormat.DATE
            ),
            ReportColumn(
                title="Pending Invoice Count" if is_customer else "Pending Bill Count",
                key="pending_count",
                alignment=ColumnAlignment.RIGHT,
            ),
            ReportColumn(title="Risk Indicator", key="risk_level"),
        ]
        rows = [
            ReportRow(
                data={
                    "entity_name": row.entity_name,
                    "outstanding_amount": row.outstanding_amount,
                    "overdue_amount": row.overdue_amount,
                    "current_amount": row.current_amount,
                    "last_transaction_date": row.last_transaction_date,
                    "last_payment_date": row.last_payment_date,
                    "pending_count": row.pending_count,
                    "risk_level": row.risk_level.value,
                }
            )
            for row in response.rows
        ]
        summary = [
            ReportSummary(label="Accounts Receivable", value=response.summary.accounts_receivable),
            ReportSummary(label="Accounts Payable", value=response.summary.accounts_payable),
            ReportSummary(label="Net Position", value=response.summary.net_position),
            ReportSummary(label="Overdue Receivable", value=response.summary.overdue_receivable),
            ReportSummary(label="Overdue Payable", value=response.summary.overdue_payable),
            ReportSummary(
                label="Customers With Outstanding",
                value=response.summary.customers_with_outstanding,
            ),
            ReportSummary(
                label="Suppliers With Outstanding",
                value=response.summary.suppliers_with_outstanding,
            ),
        ]
        return ReportsService._assemble_export_data(
            title="Outstanding Report",
            subtitle=f"{entity_label} Outstanding",
            columns=columns,
            rows=rows,
            summary=summary,
            generated_by=generated_by,
            tenant_name=tenant_name,
            filters=filters,
        )

    @staticmethod
    def build_aging_report_export_data(
        response: AgingReportResponse,
        *,
        generated_by: str,
        tenant_name: str,
        filters: list[ReportFilterDisplay] | None = None,
    ) -> ReportExportData:
        is_customer = response.entity_type.value == "customer"
        entity_label = "Customer" if is_customer else "Supplier"
        columns = [
            ReportColumn(title=entity_label, key="entity_name"),
            ReportColumn(
                title="Current",
                key="current_amount",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="1-30 Days",
                key="days_1_30",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="31-60 Days",
                key="days_31_60",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="61-90 Days",
                key="days_61_90",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="90+ Days",
                key="days_90_plus",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Total",
                key="total",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
        ]
        rows = [
            ReportRow(
                data={
                    "entity_name": row.entity_name,
                    "current_amount": row.current_amount,
                    "days_1_30": row.days_1_30,
                    "days_31_60": row.days_31_60,
                    "days_61_90": row.days_61_90,
                    "days_90_plus": row.days_90_plus,
                    "total": row.total,
                }
            )
            for row in response.rows
        ]
        summary = [
            ReportSummary(label="Current Total", value=response.summary.current_total),
            ReportSummary(label="1-30 Total", value=response.summary.days_1_30_total),
            ReportSummary(label="31-60 Total", value=response.summary.days_31_60_total),
            ReportSummary(label="61-90 Total", value=response.summary.days_61_90_total),
            ReportSummary(label="90+ Total", value=response.summary.days_90_plus_total),
            ReportSummary(label="Grand Total", value=response.summary.grand_total),
        ]
        return ReportsService._assemble_export_data(
            title="Aging Report",
            subtitle=f"{entity_label} Aging",
            columns=columns,
            rows=rows,
            summary=summary,
            generated_by=generated_by,
            tenant_name=tenant_name,
            filters=filters,
        )

    @staticmethod
    def build_trip_profitability_export_data(
        response: TripProfitabilityResponse,
        *,
        generated_by: str,
        tenant_name: str,
        filters: list[ReportFilterDisplay] | None = None,
    ) -> ReportExportData:
        columns = [
            ReportColumn(title="Trip Number", key="trip_number"),
            ReportColumn(title="Boat", key="boat_name"),
            ReportColumn(title="Departure Date", key="departure_date", format=ColumnFormat.DATE),
            ReportColumn(title="Return Date", key="return_date", format=ColumnFormat.DATE),
            ReportColumn(title="Trip Status", key="status"),
            ReportColumn(
                title="Revenue",
                key="revenue",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Expenses",
                key="expenses",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Profit",
                key="profit",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Profit Margin %",
                key="profit_margin_percent",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.PERCENT,
            ),
        ]
        rows = [
            ReportRow(
                data={
                    "trip_number": row.trip_number,
                    "boat_name": row.boat_name,
                    "departure_date": row.departure_date,
                    "return_date": row.return_date,
                    "status": row.status.value,
                    "revenue": row.revenue,
                    "expenses": row.expenses,
                    "profit": row.profit,
                    "profit_margin_percent": row.profit_margin_percent,
                }
            )
            for row in response.rows
        ]
        summary = [
            ReportSummary(label="Total Revenue", value=response.summary.total_revenue),
            ReportSummary(label="Total Expenses", value=response.summary.total_expenses),
            ReportSummary(label="Total Profit", value=response.summary.total_profit),
            ReportSummary(
                label="Average Profit Per Trip", value=response.summary.average_profit_per_trip
            ),
            ReportSummary(
                label="Average Revenue Per Trip", value=response.summary.average_revenue_per_trip
            ),
            ReportSummary(
                label="Most Profitable Trip", value=response.summary.most_profitable_trip_number
            ),
            ReportSummary(
                label="Most Profitable Trip Profit",
                value=response.summary.most_profitable_trip_profit,
            ),
            ReportSummary(label="Loss Making Trips", value=response.summary.loss_making_trips),
        ]
        return ReportsService._assemble_export_data(
            title="Trip Profitability",
            columns=columns,
            rows=rows,
            summary=summary,
            generated_by=generated_by,
            tenant_name=tenant_name,
            filters=filters,
        )

    @staticmethod
    def build_boat_profitability_export_data(
        response: BoatProfitabilityResponse,
        *,
        generated_by: str,
        tenant_name: str,
        filters: list[ReportFilterDisplay] | None = None,
    ) -> ReportExportData:
        columns = [
            ReportColumn(title="Boat", key="boat_name"),
            ReportColumn(title="Registration Number", key="registration_number"),
            ReportColumn(title="Total Trips", key="total_trips", alignment=ColumnAlignment.RIGHT),
            ReportColumn(
                title="Revenue",
                key="revenue",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Expenses",
                key="expenses",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Profit",
                key="profit",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Profit Margin %",
                key="profit_margin_percent",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.PERCENT,
            ),
            ReportColumn(
                title="Avg Profit / Trip",
                key="average_profit_per_trip",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Avg Revenue / Trip",
                key="average_revenue_per_trip",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Best Trip Profit",
                key="best_trip_profit",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Worst Trip Profit",
                key="worst_trip_profit",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(title="Last Trip Date", key="last_trip_date", format=ColumnFormat.DATE),
        ]
        rows = [
            ReportRow(
                data={
                    "boat_name": row.boat_name,
                    "registration_number": row.registration_number,
                    "total_trips": row.total_trips,
                    "revenue": row.revenue,
                    "expenses": row.expenses,
                    "profit": row.profit,
                    "profit_margin_percent": row.profit_margin_percent,
                    "average_profit_per_trip": row.average_profit_per_trip,
                    "average_revenue_per_trip": row.average_revenue_per_trip,
                    "best_trip_profit": row.best_trip_profit,
                    "worst_trip_profit": row.worst_trip_profit,
                    "last_trip_date": row.last_trip_date,
                }
            )
            for row in response.rows
        ]
        summary = [
            ReportSummary(label="Fleet Revenue", value=response.summary.fleet_revenue),
            ReportSummary(label="Fleet Expenses", value=response.summary.fleet_expenses),
            ReportSummary(label="Fleet Profit", value=response.summary.fleet_profit),
            ReportSummary(label="Fleet Margin %", value=response.summary.fleet_margin_percent),
            ReportSummary(label="Total Boats", value=response.summary.total_boats),
            ReportSummary(label="Active Boats", value=response.summary.active_boats),
            ReportSummary(
                label="Average Profit Per Boat", value=response.summary.average_profit_per_boat
            ),
            ReportSummary(
                label="Most Profitable Boat", value=response.summary.most_profitable_boat_name
            ),
            ReportSummary(
                label="Most Profitable Boat Profit",
                value=response.summary.most_profitable_boat_profit,
            ),
        ]
        return ReportsService._assemble_export_data(
            title="Boat Profitability",
            columns=columns,
            rows=rows,
            summary=summary,
            generated_by=generated_by,
            tenant_name=tenant_name,
            filters=filters,
        )

    @staticmethod
    def build_fish_sales_export_data(
        response: FishSalesResponse,
        *,
        generated_by: str,
        tenant_name: str,
        filters: list[ReportFilterDisplay] | None = None,
    ) -> ReportExportData:
        columns = [
            ReportColumn(title="Fish", key="fish_name"),
            ReportColumn(title="Scientific Name", key="scientific_name"),
            ReportColumn(
                title="Total Quantity Sold",
                key="quantity_sold",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.NUMBER,
            ),
            ReportColumn(title="Unit", key="unit"),
            ReportColumn(
                title="Revenue",
                key="revenue",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Average Selling Price",
                key="average_selling_price",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(
                title="Invoice Count", key="invoice_count", alignment=ColumnAlignment.RIGHT
            ),
            ReportColumn(title="Trip Count", key="trip_count", alignment=ColumnAlignment.RIGHT),
            ReportColumn(
                title="Customer Count", key="customer_count", alignment=ColumnAlignment.RIGHT
            ),
            ReportColumn(title="Last Sold Date", key="last_sold_date", format=ColumnFormat.DATE),
        ]
        rows = [
            ReportRow(
                data={
                    "fish_name": row.fish_name,
                    "scientific_name": row.scientific_name,
                    "quantity_sold": row.quantity_sold,
                    "unit": row.unit.value,
                    "revenue": row.revenue,
                    "average_selling_price": row.average_selling_price,
                    "invoice_count": row.invoice_count,
                    "trip_count": row.trip_count,
                    "customer_count": row.customer_count,
                    "last_sold_date": row.last_sold_date,
                }
            )
            for row in response.rows
        ]
        summary = [
            ReportSummary(label="Total Fish Sold", value=response.summary.total_fish_sold),
            ReportSummary(label="Total Revenue", value=response.summary.total_revenue),
            ReportSummary(
                label="Average Selling Price", value=response.summary.average_selling_price
            ),
            ReportSummary(
                label="Best Selling Fish (Quantity)",
                value=response.summary.best_selling_fish_name,
            ),
            ReportSummary(
                label="Best Selling Fish Quantity",
                value=response.summary.best_selling_fish_quantity,
            ),
            ReportSummary(
                label="Highest Revenue Fish", value=response.summary.highest_revenue_fish_name
            ),
            ReportSummary(
                label="Highest Revenue Fish Revenue",
                value=response.summary.highest_revenue_fish_revenue,
            ),
            ReportSummary(
                label="Total Fish Types Sold", value=response.summary.total_fish_types_sold
            ),
        ]
        return ReportsService._assemble_export_data(
            title="Fish Sales Analytics",
            columns=columns,
            rows=rows,
            summary=summary,
            generated_by=generated_by,
            tenant_name=tenant_name,
            filters=filters,
        )
