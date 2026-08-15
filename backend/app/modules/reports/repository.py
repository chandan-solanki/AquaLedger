import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import Integer, Numeric, and_, case, func, literal, or_, select, union_all
from sqlalchemy import cast as sql_cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from sqlalchemy.sql.selectable import Subquery

from app.modules.boats.models import Boat
from app.modules.companies.models import Company
from app.modules.fish.models import Fish
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.models import Invoice, InvoiceItem
from app.modules.payments.constants import PaymentStatus
from app.modules.payments.models import Payment
from app.modules.purchase.constants import PurchaseStatus
from app.modules.purchase.models import PurchaseBill
from app.modules.reports.constants import (
    EntityType,
    PaidStatus,
    ProfitabilityFilter,
    RiskLevel,
    SupplierTransactionType,
    TransactionType,
)
from app.modules.supplier_payments.constants import SupplierPaymentStatus
from app.modules.supplier_payments.models import SupplierPayment
from app.modules.suppliers.models import Supplier
from app.modules.trip_catches.models import TripCatch
from app.modules.trip_expenses.models import TripExpense
from app.modules.trips.constants import TripStatus
from app.modules.trips.models import Trip

# Mirrors DashboardRepository's `_NON_SALES_INVOICE_STATUSES` - each module
# keeps its own copy of "which statuses count as real" rather than importing
# another module's private constant (ARCHITECTURE.md §2). A ledger entry is
# only ever posted for an invoice that was actually issued (ACCOUNTING
# RULES: "Ignore Draft invoices, Cancelled invoices").
_EXCLUDED_INVOICE_STATUSES = (InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED)

# Same reasoning as _EXCLUDED_INVOICE_STATUSES, on the buy side (ACCOUNTING
# RULES: "Ignore Draft Purchase Bills, Cancelled Purchase Bills").
_EXCLUDED_PURCHASE_STATUSES = (PurchaseStatus.DRAFT, PurchaseStatus.CANCELLED)


def _paid_status_condition(paid_amount: Any, total_amount: Any, paid_status: PaidStatus) -> Any:
    """The Sales/Purchase Report's `paid_status` filter (TASKS.md Sprint 11
    Session 3) - a plain comparison of paid_amount against total_amount,
    independent of the document's own `status` column. Shared by both
    reports since the underlying columns are named identically on Invoice
    and PurchaseBill."""
    if paid_status == PaidStatus.UNPAID:
        return paid_amount == 0
    if paid_status == PaidStatus.PARTIALLY_PAID:
        return and_(paid_amount > 0, paid_amount < total_amount)
    return paid_amount >= total_amount  # PaidStatus.PAID


def _risk_level_case(max_overdue_days: Any) -> Any:
    """The Outstanding/Aging Report's shared risk bucketing (TASKS.md
    Sprint 11 Session 3 Phase B "RISK INDICATOR"): `max_overdue_days` - the
    number of days since the *oldest* still-unpaid invoice/bill's due_date,
    NULL when there is no overdue unpaid row at all - collapses the Aging
    Report's five buckets into three tiers: no overdue balance -> LOW;
    1-60 days overdue (the 1-30 and 31-60 buckets) -> MEDIUM; 61+ days
    overdue (the 61-90 and 90+ buckets) -> HIGH."""
    return case(
        (max_overdue_days.is_(None), literal(RiskLevel.LOW.value)),
        (max_overdue_days <= 60, literal(RiskLevel.MEDIUM.value)),
        else_=literal(RiskLevel.HIGH.value),
    )


@dataclass(frozen=True)
class LedgerAggregates:
    total_debit: Decimal
    total_credit: Decimal
    invoice_count: int
    payment_count: int


@dataclass(frozen=True)
class SupplierLedgerAggregates:
    total_debit: Decimal
    total_credit: Decimal
    purchase_bill_count: int
    supplier_payment_count: int


@dataclass(frozen=True)
class SalesReportAggregates:
    total_sales: Decimal
    total_paid: Decimal
    outstanding: Decimal
    invoice_count: int
    average_invoice: Decimal
    largest_invoice: Decimal


@dataclass(frozen=True)
class SalesReportRowData:
    invoice_id: uuid.UUID
    invoice_number: str
    invoice_date: date
    due_date: date | None
    customer_name: str
    invoice_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    status: InvoiceStatus


@dataclass(frozen=True)
class PurchaseReportAggregates:
    total_purchases: Decimal
    total_paid: Decimal
    outstanding: Decimal
    bill_count: int
    average_bill: Decimal
    largest_bill: Decimal


@dataclass(frozen=True)
class PurchaseReportRowData:
    bill_id: uuid.UUID
    bill_number: str
    bill_date: date
    due_date: date | None
    supplier_name: str
    bill_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    status: PurchaseStatus


@dataclass(frozen=True)
class OutstandingSummaryAggregates:
    """Always the full, unfiltered grand totals - see
    ReportsRepository.get_outstanding_summary's docstring."""

    accounts_receivable: Decimal
    accounts_payable: Decimal
    overdue_receivable: Decimal
    overdue_payable: Decimal
    customers_with_outstanding: int
    suppliers_with_outstanding: int


@dataclass(frozen=True)
class OutstandingReportRowData:
    entity_id: uuid.UUID
    entity_name: str
    entity_code: str
    outstanding_amount: Decimal
    overdue_amount: Decimal
    current_amount: Decimal
    last_transaction_date: date | None
    last_payment_date: date | None
    pending_count: int
    risk_level: RiskLevel


@dataclass(frozen=True)
class AgingReportRowData:
    entity_id: uuid.UUID
    entity_name: str
    entity_code: str
    current_amount: Decimal
    days_1_30: Decimal
    days_31_60: Decimal
    days_61_90: Decimal
    days_90_plus: Decimal
    total: Decimal
    risk_level: RiskLevel


@dataclass(frozen=True)
class AgingSummaryAggregates:
    current_total: Decimal
    days_1_30_total: Decimal
    days_31_60_total: Decimal
    days_61_90_total: Decimal
    days_90_plus_total: Decimal
    grand_total: Decimal


@dataclass(frozen=True)
class TripProfitabilityRowData:
    trip_id: uuid.UUID
    trip_number: str
    boat_id: uuid.UUID
    boat_name: str
    departure_datetime: datetime
    actual_return_datetime: datetime | None
    status: TripStatus
    revenue: Decimal
    expenses: Decimal
    profit: Decimal


@dataclass(frozen=True)
class TripProfitabilityAggregates:
    total_revenue: Decimal
    total_expenses: Decimal
    total_profit: Decimal
    average_profit_per_trip: Decimal
    average_revenue_per_trip: Decimal
    most_profitable_trip_number: str | None
    most_profitable_trip_profit: Decimal | None
    loss_making_trips: int
    trip_count: int


@dataclass(frozen=True)
class BoatProfitabilityRowData:
    boat_id: uuid.UUID
    boat_name: str
    registration_number: str
    total_trips: int
    revenue: Decimal
    expenses: Decimal
    profit: Decimal
    average_profit_per_trip: Decimal
    average_revenue_per_trip: Decimal
    best_trip_profit: Decimal
    worst_trip_profit: Decimal
    last_trip_date: datetime | None


@dataclass(frozen=True)
class BoatProfitabilityAggregates:
    fleet_revenue: Decimal
    fleet_expenses: Decimal
    fleet_profit: Decimal
    total_boats: int
    active_boats: int
    most_profitable_boat_name: str | None
    most_profitable_boat_profit: Decimal | None


@dataclass(frozen=True)
class FishSalesRowData:
    fish_id: uuid.UUID
    fish_name: str
    scientific_name: str | None
    unit: str
    quantity_sold: Decimal
    revenue: Decimal
    invoice_count: int
    trip_count: int
    customer_count: int
    last_sold_date: date | None


@dataclass(frozen=True)
class FishSalesAggregates:
    total_fish_sold: Decimal
    total_revenue: Decimal
    best_selling_fish_name: str | None
    best_selling_fish_quantity: Decimal | None
    highest_revenue_fish_name: str | None
    highest_revenue_fish_revenue: Decimal | None
    total_fish_types_sold: int


@dataclass(frozen=True)
class FishSalesHistoryRowData:
    invoice_id: uuid.UUID
    invoice_number: str
    invoice_date: date
    customer_name: str
    boat_name: str | None
    trip_number: str | None
    quantity: Decimal
    unit_price: Decimal
    revenue: Decimal


@dataclass(frozen=True)
class LedgerRow:
    """One row of a ledger page, before the service adds the opening
    balance offset to `cumulative` to produce the final `running_balance`
    (see ReportsService._to_entry)."""

    transaction_date: date
    created_at: datetime
    reference_number: str
    transaction_type: str
    description: str
    debit: Decimal
    credit: Decimal
    cumulative: Decimal


class ReportsRepository:
    """Read-only ledger queries spanning the invoices and payments modules.

    Like DashboardRepository, this is the documented exception to
    ARCHITECTURE.md §2's "modules talk to each other only through
    service.py" rule: a pure reporting query that only ever SELECTs is
    exactly what §2 itself carves `reporting`/`analytics` out for. This
    repository imports `Invoice`/`Payment` ORM models directly (never their
    repository/service internals) and never executes an INSERT/UPDATE/
    DELETE.

    Every method builds its own UNION ALL of "one row per issued invoice
    (debit) union one row per posted payment (credit)" via `_ledger_union` -
    the Repository's data source per TASKS.md ("Combining both using UNION
    ALL"). Draft/cancelled invoices, draft payments and soft-deleted rows of
    either are excluded uniformly, everywhere, regardless of filters
    (ACCOUNTING RULES).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _invoice_select(self, tenant_id: uuid.UUID, company_id: uuid.UUID) -> Select[Any]:
        return select(
            Invoice.invoice_date.label("transaction_date"),
            Invoice.created_at.label("created_at"),
            Invoice.id.label("source_id"),
            Invoice.invoice_number.label("reference_number"),
            literal(TransactionType.INVOICE.value).label("transaction_type"),
            literal("Sales Invoice").label("description"),
            Invoice.total_amount.label("debit"),
            literal(Decimal("0"), type_=Numeric(14, 2)).label("credit"),
        ).where(
            Invoice.tenant_id == tenant_id,
            Invoice.company_id == company_id,
            Invoice.deleted_at.is_(None),
            Invoice.status.notin_(_EXCLUDED_INVOICE_STATUSES),
        )

    def _payment_select(self, tenant_id: uuid.UUID, company_id: uuid.UUID) -> Select[Any]:
        return select(
            Payment.payment_date.label("transaction_date"),
            Payment.created_at.label("created_at"),
            Payment.id.label("source_id"),
            Payment.payment_number.label("reference_number"),
            literal(TransactionType.PAYMENT.value).label("transaction_type"),
            literal("Payment Received").label("description"),
            literal(Decimal("0"), type_=Numeric(14, 2)).label("debit"),
            Payment.amount.label("credit"),
        ).where(
            Payment.tenant_id == tenant_id,
            Payment.company_id == company_id,
            Payment.deleted_at.is_(None),
            Payment.status == PaymentStatus.POSTED,
        )

    def _ledger_union(self, tenant_id: uuid.UUID, company_id: uuid.UUID) -> Subquery:
        return union_all(
            self._invoice_select(tenant_id, company_id),
            self._payment_select(tenant_id, company_id),
        ).subquery("ledger_transactions")

    async def get_opening_balance(
        self, tenant_id: uuid.UUID, company_id: uuid.UUID, *, before_date: date | None
    ) -> Decimal:
        """Net balance (debit - credit) of every real transaction strictly
        before `before_date` - always over the FULL invoice+payment set,
        never narrowed by transaction_type (a confirmed Session 1 design
        decision: the type filter only narrows which rows *display*, it
        never changes the true account balance). Returns 0 without a query
        when `before_date` is None - there is nothing "before" an unbounded
        range."""
        if before_date is None:
            return Decimal("0")

        union = self._ledger_union(tenant_id, company_id)
        result = await self._session.execute(
            select(
                func.coalesce(func.sum(union.c.debit), 0)
                - func.coalesce(func.sum(union.c.credit), 0)
            ).where(union.c.transaction_date < before_date)
        )
        return cast(Decimal, result.scalar_one())

    async def get_summary_aggregates(
        self,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        *,
        from_date: date | None,
        to_date: date | None,
    ) -> LedgerAggregates:
        """Total debit/credit and invoice/payment counts for the date
        range - one grouped/conditional-aggregate query, mirroring
        DashboardRepository's `case()`/`func.sum`/`func.count` style. Like
        get_opening_balance, always over the full set - never narrowed by
        transaction_type."""
        union = self._ledger_union(tenant_id, company_id)
        conditions = []
        if from_date is not None:
            conditions.append(union.c.transaction_date >= from_date)
        if to_date is not None:
            conditions.append(union.c.transaction_date <= to_date)

        is_invoice = union.c.transaction_type == TransactionType.INVOICE.value
        is_payment = union.c.transaction_type == TransactionType.PAYMENT.value
        row = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(union.c.debit), 0),
                    func.coalesce(func.sum(union.c.credit), 0),
                    func.count(case((is_invoice, 1))),
                    func.count(case((is_payment, 1))),
                ).where(*conditions)
            )
        ).one()
        return LedgerAggregates(
            total_debit=row[0], total_credit=row[1], invoice_count=row[2], payment_count=row[3]
        )

    async def get_ledger_page(
        self,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        *,
        from_date: date | None,
        to_date: date | None,
        transaction_type: TransactionType | None,
        page: int,
        page_size: int,
    ) -> tuple[list[LedgerRow], int]:
        """The paginated, chronologically-ordered Ledger Entries - a single
        windowed query (never one query per row): the cumulative running
        total is computed via `SUM(debit - credit) OVER (ORDER BY
        transaction_date, created_at, source_id ROWS UNBOUNDED PRECEDING)`
        across the *full* date-range-filtered set (unaffected by
        transaction_type, so a displayed invoice row's running balance still
        reflects payments made in between, even when Payment rows are
        hidden by the filter) - only *after* that cumulative sum is computed
        does `transaction_type` narrow which rows are actually counted and
        returned. Two round trips (count + page), the same pattern every
        other repository's `search` uses - not one query per page.

        `source_id` (a uuid7, hence time-ordered) is the tie-break for rows
        sharing a `transaction_date`/`created_at` instant - the same "tie-
        break in the primary sort's own direction" discipline
        InvoiceRepository.search documents, needed here because an invoice
        and a payment could plausibly share a `created_at` timestamp.
        """
        union = self._ledger_union(tenant_id, company_id)
        date_conditions = []
        if from_date is not None:
            date_conditions.append(union.c.transaction_date >= from_date)
        if to_date is not None:
            date_conditions.append(union.c.transaction_date <= to_date)

        order_columns = [union.c.transaction_date, union.c.created_at, union.c.source_id]
        windowed = (
            select(
                union.c.transaction_date,
                union.c.created_at,
                union.c.source_id,
                union.c.reference_number,
                union.c.transaction_type,
                union.c.description,
                union.c.debit,
                union.c.credit,
                func.sum(union.c.debit - union.c.credit)
                .over(order_by=order_columns, rows=(None, 0))
                .label("cumulative"),
            )
            .where(*date_conditions)
            .subquery("ledger_windowed")
        )

        type_conditions = []
        if transaction_type is not None:
            type_conditions.append(windowed.c.transaction_type == transaction_type.value)

        total = (
            await self._session.execute(
                select(func.count()).select_from(windowed).where(*type_conditions)
            )
        ).scalar_one()

        rows = (
            await self._session.execute(
                select(windowed)
                .where(*type_conditions)
                .order_by(
                    windowed.c.transaction_date.asc(),
                    windowed.c.created_at.asc(),
                    windowed.c.source_id.asc(),
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()

        entries = [
            LedgerRow(
                transaction_date=row.transaction_date,
                created_at=row.created_at,
                reference_number=row.reference_number,
                transaction_type=row.transaction_type,
                description=row.description,
                debit=row.debit,
                credit=row.credit,
                cumulative=row.cumulative,
            )
            for row in rows
        ]
        return entries, total

    # -- Supplier Ledger (TASKS.md Sprint 11 Session 2) -----------------
    #
    # Mirrors the Customer Ledger methods above exactly, on the buy side:
    # posted Purchase Bills (debit) unioned with posted Supplier Payments
    # (credit), scoped to one supplier. `LedgerRow` is reused as-is - its
    # fields (transaction_date/reference_number/transaction_type/description/
    # debit/credit/cumulative) are already generic, not invoice-specific.

    def _purchase_bill_select(self, tenant_id: uuid.UUID, supplier_id: uuid.UUID) -> Select[Any]:
        return select(
            PurchaseBill.bill_date.label("transaction_date"),
            PurchaseBill.created_at.label("created_at"),
            PurchaseBill.id.label("source_id"),
            PurchaseBill.bill_number.label("reference_number"),
            literal(SupplierTransactionType.PURCHASE_BILL.value).label("transaction_type"),
            literal("Purchase Bill").label("description"),
            PurchaseBill.total_amount.label("debit"),
            literal(Decimal("0"), type_=Numeric(14, 2)).label("credit"),
        ).where(
            PurchaseBill.tenant_id == tenant_id,
            PurchaseBill.supplier_id == supplier_id,
            PurchaseBill.deleted_at.is_(None),
            PurchaseBill.status.notin_(_EXCLUDED_PURCHASE_STATUSES),
        )

    def _supplier_payment_select(self, tenant_id: uuid.UUID, supplier_id: uuid.UUID) -> Select[Any]:
        return select(
            SupplierPayment.payment_date.label("transaction_date"),
            SupplierPayment.created_at.label("created_at"),
            SupplierPayment.id.label("source_id"),
            SupplierPayment.payment_number.label("reference_number"),
            literal(SupplierTransactionType.SUPPLIER_PAYMENT.value).label("transaction_type"),
            literal("Supplier Payment").label("description"),
            literal(Decimal("0"), type_=Numeric(14, 2)).label("debit"),
            SupplierPayment.amount.label("credit"),
        ).where(
            SupplierPayment.tenant_id == tenant_id,
            SupplierPayment.supplier_id == supplier_id,
            SupplierPayment.deleted_at.is_(None),
            SupplierPayment.status == SupplierPaymentStatus.POSTED,
        )

    def _supplier_ledger_union(self, tenant_id: uuid.UUID, supplier_id: uuid.UUID) -> Subquery:
        return union_all(
            self._purchase_bill_select(tenant_id, supplier_id),
            self._supplier_payment_select(tenant_id, supplier_id),
        ).subquery("supplier_ledger_transactions")

    async def get_supplier_opening_balance(
        self, tenant_id: uuid.UUID, supplier_id: uuid.UUID, *, before_date: date | None
    ) -> Decimal:
        """Net balance (debit - credit) of every real transaction strictly
        before `before_date` - always over the FULL purchase-bill+payment
        set, never narrowed by transaction_type (mirrors
        get_opening_balance's own design decision). Returns 0 without a
        query when `before_date` is None."""
        if before_date is None:
            return Decimal("0")

        union = self._supplier_ledger_union(tenant_id, supplier_id)
        result = await self._session.execute(
            select(
                func.coalesce(func.sum(union.c.debit), 0)
                - func.coalesce(func.sum(union.c.credit), 0)
            ).where(union.c.transaction_date < before_date)
        )
        return cast(Decimal, result.scalar_one())

    async def get_supplier_summary_aggregates(
        self,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        *,
        from_date: date | None,
        to_date: date | None,
    ) -> SupplierLedgerAggregates:
        """Total debit/credit and purchase-bill/supplier-payment counts for
        the date range - mirrors get_summary_aggregates exactly. Always
        over the full set - never narrowed by transaction_type."""
        union = self._supplier_ledger_union(tenant_id, supplier_id)
        conditions = []
        if from_date is not None:
            conditions.append(union.c.transaction_date >= from_date)
        if to_date is not None:
            conditions.append(union.c.transaction_date <= to_date)

        is_purchase_bill = union.c.transaction_type == SupplierTransactionType.PURCHASE_BILL.value
        is_supplier_payment = (
            union.c.transaction_type == SupplierTransactionType.SUPPLIER_PAYMENT.value
        )
        row = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(union.c.debit), 0),
                    func.coalesce(func.sum(union.c.credit), 0),
                    func.count(case((is_purchase_bill, 1))),
                    func.count(case((is_supplier_payment, 1))),
                ).where(*conditions)
            )
        ).one()
        return SupplierLedgerAggregates(
            total_debit=row[0],
            total_credit=row[1],
            purchase_bill_count=row[2],
            supplier_payment_count=row[3],
        )

    async def get_supplier_ledger_page(
        self,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        *,
        from_date: date | None,
        to_date: date | None,
        transaction_type: SupplierTransactionType | None,
        page: int,
        page_size: int,
    ) -> tuple[list[LedgerRow], int]:
        """The paginated, chronologically-ordered Ledger Entries - mirrors
        get_ledger_page exactly: the cumulative running total is computed
        over the full date-range-filtered set before transaction_type
        narrows which rows are actually counted and returned, so a
        displayed purchase bill's running balance still reflects payments
        made in between even when Supplier Payment rows are hidden."""
        union = self._supplier_ledger_union(tenant_id, supplier_id)
        date_conditions = []
        if from_date is not None:
            date_conditions.append(union.c.transaction_date >= from_date)
        if to_date is not None:
            date_conditions.append(union.c.transaction_date <= to_date)

        order_columns = [union.c.transaction_date, union.c.created_at, union.c.source_id]
        windowed = (
            select(
                union.c.transaction_date,
                union.c.created_at,
                union.c.source_id,
                union.c.reference_number,
                union.c.transaction_type,
                union.c.description,
                union.c.debit,
                union.c.credit,
                func.sum(union.c.debit - union.c.credit)
                .over(order_by=order_columns, rows=(None, 0))
                .label("cumulative"),
            )
            .where(*date_conditions)
            .subquery("supplier_ledger_windowed")
        )

        type_conditions = []
        if transaction_type is not None:
            type_conditions.append(windowed.c.transaction_type == transaction_type.value)

        total = (
            await self._session.execute(
                select(func.count()).select_from(windowed).where(*type_conditions)
            )
        ).scalar_one()

        rows = (
            await self._session.execute(
                select(windowed)
                .where(*type_conditions)
                .order_by(
                    windowed.c.transaction_date.asc(),
                    windowed.c.created_at.asc(),
                    windowed.c.source_id.asc(),
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()

        entries = [
            LedgerRow(
                transaction_date=row.transaction_date,
                created_at=row.created_at,
                reference_number=row.reference_number,
                transaction_type=row.transaction_type,
                description=row.description,
                debit=row.debit,
                credit=row.credit,
                cumulative=row.cumulative,
            )
            for row in rows
        ]
        return entries, total

    # -- Sales Report / Purchase Report (TASKS.md Sprint 11 Session 3) --
    #
    # Unlike the Ledgers above, these are plain filtered lists - one row per
    # invoice/purchase bill, no UNION, no running balance. Each report is
    # two round trips: one aggregate query (which also produces the true
    # COUNT(*) over the filtered set, reused directly as
    # `pagination.total_records` - no separate COUNT query needed) and one
    # paginated rows query. Ordering is always fixed (`invoice_date DESC,
    # invoice_number DESC` / `bill_date DESC, bill_number DESC`, each with a
    # final `id DESC` tie-break for full determinism) - TASKS.md's SORTING
    # section for both reports, not a user-selectable option.

    def _sales_report_conditions(
        self,
        tenant_id: uuid.UUID,
        *,
        customer_id: uuid.UUID | None,
        status: InvoiceStatus | None,
        paid_status: PaidStatus | None,
        from_date: date | None,
        to_date: date | None,
        q: str | None,
    ) -> list[Any]:
        conditions: list[Any] = [
            Invoice.tenant_id == tenant_id,
            Invoice.deleted_at.is_(None),
            # "Purpose: show every issued invoice" - a hard invariant, not a
            # toggle: a draft was never a sale, regardless of `status`.
            Invoice.status != InvoiceStatus.DRAFT,
        ]
        if customer_id is not None:
            conditions.append(Invoice.company_id == customer_id)
        if status is not None:
            conditions.append(Invoice.status == status)
        if paid_status is not None:
            conditions.append(
                _paid_status_condition(Invoice.paid_amount, Invoice.total_amount, paid_status)
            )
        if from_date is not None:
            conditions.append(Invoice.invoice_date >= from_date)
        if to_date is not None:
            conditions.append(Invoice.invoice_date <= to_date)
        if q:
            pattern = f"%{q.strip()}%"
            conditions.append(
                or_(Invoice.invoice_number.ilike(pattern), Company.name.ilike(pattern))
            )
        return conditions

    async def get_sales_report(
        self,
        tenant_id: uuid.UUID,
        *,
        customer_id: uuid.UUID | None,
        status: InvoiceStatus | None,
        paid_status: PaidStatus | None,
        from_date: date | None,
        to_date: date | None,
        q: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[SalesReportRowData], SalesReportAggregates, int]:
        conditions = self._sales_report_conditions(
            tenant_id,
            customer_id=customer_id,
            status=status,
            paid_status=paid_status,
            from_date=from_date,
            to_date=to_date,
            q=q,
        )

        agg_row = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(Invoice.total_amount), 0),
                    func.coalesce(func.sum(Invoice.paid_amount), 0),
                    func.coalesce(func.sum(Invoice.balance_amount), 0),
                    func.count(),
                    func.coalesce(func.avg(Invoice.total_amount), 0),
                    func.coalesce(func.max(Invoice.total_amount), 0),
                )
                .select_from(Invoice)
                .join(Company, Company.id == Invoice.company_id)
                .where(*conditions)
            )
        ).one()
        aggregates = SalesReportAggregates(
            total_sales=agg_row[0],
            total_paid=agg_row[1],
            outstanding=agg_row[2],
            invoice_count=agg_row[3],
            average_invoice=agg_row[4],
            largest_invoice=agg_row[5],
        )

        rows_result = (
            await self._session.execute(
                select(
                    Invoice.id,
                    Invoice.invoice_number,
                    Invoice.invoice_date,
                    Invoice.due_date,
                    Company.name,
                    Invoice.total_amount,
                    Invoice.paid_amount,
                    Invoice.balance_amount,
                    Invoice.status,
                )
                .select_from(Invoice)
                .join(Company, Company.id == Invoice.company_id)
                .where(*conditions)
                .order_by(
                    Invoice.invoice_date.desc(), Invoice.invoice_number.desc(), Invoice.id.desc()
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()

        rows = [
            SalesReportRowData(
                invoice_id=row[0],
                invoice_number=row[1],
                invoice_date=row[2],
                due_date=row[3],
                customer_name=row[4],
                invoice_amount=row[5],
                paid_amount=row[6],
                outstanding_amount=row[7],
                status=row[8],
            )
            for row in rows_result
        ]
        return rows, aggregates, aggregates.invoice_count

    def _purchase_report_conditions(
        self,
        tenant_id: uuid.UUID,
        *,
        supplier_id: uuid.UUID | None,
        status: PurchaseStatus | None,
        paid_status: PaidStatus | None,
        from_date: date | None,
        to_date: date | None,
        q: str | None,
    ) -> list[Any]:
        conditions: list[Any] = [
            PurchaseBill.tenant_id == tenant_id,
            PurchaseBill.deleted_at.is_(None),
            # "Purpose: show every posted purchase bill" - a hard invariant,
            # not a toggle: a draft was never a purchase, regardless of
            # `status`.
            PurchaseBill.status != PurchaseStatus.DRAFT,
        ]
        if supplier_id is not None:
            conditions.append(PurchaseBill.supplier_id == supplier_id)
        if status is not None:
            conditions.append(PurchaseBill.status == status)
        if paid_status is not None:
            conditions.append(
                _paid_status_condition(
                    PurchaseBill.paid_amount, PurchaseBill.total_amount, paid_status
                )
            )
        if from_date is not None:
            conditions.append(PurchaseBill.bill_date >= from_date)
        if to_date is not None:
            conditions.append(PurchaseBill.bill_date <= to_date)
        if q:
            pattern = f"%{q.strip()}%"
            conditions.append(
                or_(PurchaseBill.bill_number.ilike(pattern), Supplier.name.ilike(pattern))
            )
        return conditions

    async def get_purchase_report(
        self,
        tenant_id: uuid.UUID,
        *,
        supplier_id: uuid.UUID | None,
        status: PurchaseStatus | None,
        paid_status: PaidStatus | None,
        from_date: date | None,
        to_date: date | None,
        q: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[PurchaseReportRowData], PurchaseReportAggregates, int]:
        conditions = self._purchase_report_conditions(
            tenant_id,
            supplier_id=supplier_id,
            status=status,
            paid_status=paid_status,
            from_date=from_date,
            to_date=to_date,
            q=q,
        )

        agg_row = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(PurchaseBill.total_amount), 0),
                    func.coalesce(func.sum(PurchaseBill.paid_amount), 0),
                    func.coalesce(func.sum(PurchaseBill.balance_amount), 0),
                    func.count(),
                    func.coalesce(func.avg(PurchaseBill.total_amount), 0),
                    func.coalesce(func.max(PurchaseBill.total_amount), 0),
                )
                .select_from(PurchaseBill)
                .join(Supplier, Supplier.id == PurchaseBill.supplier_id)
                .where(*conditions)
            )
        ).one()
        aggregates = PurchaseReportAggregates(
            total_purchases=agg_row[0],
            total_paid=agg_row[1],
            outstanding=agg_row[2],
            bill_count=agg_row[3],
            average_bill=agg_row[4],
            largest_bill=agg_row[5],
        )

        rows_result = (
            await self._session.execute(
                select(
                    PurchaseBill.id,
                    PurchaseBill.bill_number,
                    PurchaseBill.bill_date,
                    PurchaseBill.due_date,
                    Supplier.name,
                    PurchaseBill.total_amount,
                    PurchaseBill.paid_amount,
                    PurchaseBill.balance_amount,
                    PurchaseBill.status,
                )
                .select_from(PurchaseBill)
                .join(Supplier, Supplier.id == PurchaseBill.supplier_id)
                .where(*conditions)
                .order_by(
                    PurchaseBill.bill_date.desc(),
                    PurchaseBill.bill_number.desc(),
                    PurchaseBill.id.desc(),
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()

        rows = [
            PurchaseReportRowData(
                bill_id=row[0],
                bill_number=row[1],
                bill_date=row[2],
                due_date=row[3],
                supplier_name=row[4],
                bill_amount=row[5],
                paid_amount=row[6],
                outstanding_amount=row[7],
                status=row[8],
            )
            for row in rows_result
        ]
        return rows, aggregates, aggregates.bill_count

    # -- Outstanding Report / Aging Report (TASKS.md Sprint 11 Session 3
    # Phase B) -----------------------------------------------------------
    #
    # Unlike every report above, one row here is one customer or one
    # supplier - never one transaction. Both reports share the same
    # customer/supplier "base" aggregate query shape (one GROUP BY over
    # Invoice+Company or PurchaseBill+Supplier) and the same risk-level
    # bucketing (_risk_level_case). `today` is always passed in by the
    # service (mirrors DashboardRepository's own today/month_start
    # parameters) rather than read here, so every day-relative comparison
    # stays deterministic and testable.

    async def get_outstanding_summary(
        self, tenant_id: uuid.UUID, *, today: date
    ) -> OutstandingSummaryAggregates:
        """Always the full, unfiltered grand totals across every customer/
        supplier with invoice/purchase-bill history - never narrowed by
        `entity_type` or any row-level filter, since these are fixed
        accounting KPIs (Accounts Receivable/Payable), not a view of the
        filtered table below them. Two queries (one per side) - each is a
        single grouped/conditional-aggregate query, mirroring
        DashboardRepository's own style."""
        is_invoice_overdue = and_(
            Invoice.due_date.isnot(None), Invoice.due_date < today, Invoice.balance_amount > 0
        )
        ar_row = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(Invoice.balance_amount), 0),
                    func.coalesce(
                        func.sum(case((is_invoice_overdue, Invoice.balance_amount), else_=0)), 0
                    ),
                    func.count(
                        func.distinct(case((Invoice.balance_amount > 0, Invoice.company_id)))
                    ),
                ).where(
                    Invoice.tenant_id == tenant_id,
                    Invoice.deleted_at.is_(None),
                    Invoice.status.notin_(_EXCLUDED_INVOICE_STATUSES),
                )
            )
        ).one()

        is_bill_overdue = and_(
            PurchaseBill.due_date.isnot(None),
            PurchaseBill.due_date < today,
            PurchaseBill.balance_amount > 0,
        )
        ap_row = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(PurchaseBill.balance_amount), 0),
                    func.coalesce(
                        func.sum(case((is_bill_overdue, PurchaseBill.balance_amount), else_=0)), 0
                    ),
                    func.count(
                        func.distinct(
                            case((PurchaseBill.balance_amount > 0, PurchaseBill.supplier_id))
                        )
                    ),
                ).where(
                    PurchaseBill.tenant_id == tenant_id,
                    PurchaseBill.deleted_at.is_(None),
                    PurchaseBill.status.notin_(_EXCLUDED_PURCHASE_STATUSES),
                )
            )
        ).one()

        return OutstandingSummaryAggregates(
            accounts_receivable=ar_row[0],
            accounts_payable=ap_row[0],
            overdue_receivable=ar_row[1],
            overdue_payable=ap_row[1],
            customers_with_outstanding=ar_row[2],
            suppliers_with_outstanding=ap_row[2],
        )

    def _customer_outstanding_base(
        self,
        tenant_id: uuid.UUID,
        *,
        today: date,
        from_date: date | None,
        to_date: date | None,
    ) -> Select[Any]:
        conditions: list[Any] = [
            Invoice.tenant_id == tenant_id,
            Invoice.deleted_at.is_(None),
            Invoice.status.notin_(_EXCLUDED_INVOICE_STATUSES),
        ]
        if from_date is not None:
            conditions.append(Invoice.invoice_date >= from_date)
        if to_date is not None:
            conditions.append(Invoice.invoice_date <= to_date)

        is_overdue = and_(
            Invoice.due_date.isnot(None), Invoice.due_date < today, Invoice.balance_amount > 0
        )
        overdue_days = sql_cast(literal(today) - Invoice.due_date, Integer)
        return (
            select(
                Company.id.label("entity_id"),
                Company.name.label("entity_name"),
                Company.code.label("entity_code"),
                func.coalesce(func.sum(Invoice.balance_amount), 0).label("outstanding_amount"),
                func.coalesce(
                    func.sum(case((is_overdue, Invoice.balance_amount), else_=0)), 0
                ).label("overdue_amount"),
                func.max(Invoice.invoice_date).label("last_transaction_date"),
                func.count(case((Invoice.balance_amount > 0, 1))).label("pending_count"),
                func.max(case((is_overdue, overdue_days))).label("max_overdue_days"),
            )
            .select_from(Invoice)
            .join(Company, Company.id == Invoice.company_id)
            .where(*conditions)
            .group_by(Company.id, Company.name, Company.code)
        )

    def _supplier_outstanding_base(
        self,
        tenant_id: uuid.UUID,
        *,
        today: date,
        from_date: date | None,
        to_date: date | None,
    ) -> Select[Any]:
        """Mirrors _customer_outstanding_base exactly, on the buy side."""
        conditions: list[Any] = [
            PurchaseBill.tenant_id == tenant_id,
            PurchaseBill.deleted_at.is_(None),
            PurchaseBill.status.notin_(_EXCLUDED_PURCHASE_STATUSES),
        ]
        if from_date is not None:
            conditions.append(PurchaseBill.bill_date >= from_date)
        if to_date is not None:
            conditions.append(PurchaseBill.bill_date <= to_date)

        is_overdue = and_(
            PurchaseBill.due_date.isnot(None),
            PurchaseBill.due_date < today,
            PurchaseBill.balance_amount > 0,
        )
        overdue_days = sql_cast(literal(today) - PurchaseBill.due_date, Integer)
        return (
            select(
                Supplier.id.label("entity_id"),
                Supplier.name.label("entity_name"),
                Supplier.code.label("entity_code"),
                func.coalesce(func.sum(PurchaseBill.balance_amount), 0).label("outstanding_amount"),
                func.coalesce(
                    func.sum(case((is_overdue, PurchaseBill.balance_amount), else_=0)), 0
                ).label("overdue_amount"),
                func.max(PurchaseBill.bill_date).label("last_transaction_date"),
                func.count(case((PurchaseBill.balance_amount > 0, 1))).label("pending_count"),
                func.max(case((is_overdue, overdue_days))).label("max_overdue_days"),
            )
            .select_from(PurchaseBill)
            .join(Supplier, Supplier.id == PurchaseBill.supplier_id)
            .where(*conditions)
            .group_by(Supplier.id, Supplier.name, Supplier.code)
        )

    def _customer_last_payment_subquery(self, tenant_id: uuid.UUID) -> Subquery:
        return (
            select(
                Payment.company_id.label("entity_id"),
                func.max(Payment.payment_date).label("last_payment_date"),
            )
            .where(
                Payment.tenant_id == tenant_id,
                Payment.deleted_at.is_(None),
                Payment.status == PaymentStatus.POSTED,
            )
            .group_by(Payment.company_id)
            .subquery("customer_last_payment")
        )

    def _supplier_last_payment_subquery(self, tenant_id: uuid.UUID) -> Subquery:
        return (
            select(
                SupplierPayment.supplier_id.label("entity_id"),
                func.max(SupplierPayment.payment_date).label("last_payment_date"),
            )
            .where(
                SupplierPayment.tenant_id == tenant_id,
                SupplierPayment.deleted_at.is_(None),
                SupplierPayment.status == SupplierPaymentStatus.POSTED,
            )
            .group_by(SupplierPayment.supplier_id)
            .subquery("supplier_last_payment")
        )

    async def _finalize_outstanding_rows(
        self,
        base_query: Select[Any],
        payment_subquery: Subquery,
        *,
        outstanding_only: bool,
        overdue_only: bool,
        risk_level: RiskLevel | None,
        q: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[OutstandingReportRowData], int]:
        """Shared by both the customer and supplier branches of
        get_outstanding_rows - outer-joins the entity-aggregated `base_query`
        to its `payment_subquery` (never a plain join into the same GROUP BY
        as Invoice/PurchaseBill, which would fan out and corrupt every SUM/
        COUNT), computes `risk_level` via `_risk_level_case`, then applies
        every row-level filter before a two-query count+page (mirrors every
        other paginated report in this module)."""
        base = base_query.subquery("outstanding_base")
        combined_select = select(
            base.c.entity_id,
            base.c.entity_name,
            base.c.entity_code,
            base.c.outstanding_amount,
            base.c.overdue_amount,
            (base.c.outstanding_amount - base.c.overdue_amount).label("current_amount"),
            base.c.last_transaction_date,
            payment_subquery.c.last_payment_date,
            base.c.pending_count,
            _risk_level_case(base.c.max_overdue_days).label("risk_level"),
        ).select_from(
            base.outerjoin(payment_subquery, payment_subquery.c.entity_id == base.c.entity_id)
        )
        combined = combined_select.subquery("outstanding_combined")

        conditions: list[Any] = []
        if outstanding_only:
            conditions.append(combined.c.outstanding_amount > 0)
        if overdue_only:
            conditions.append(combined.c.overdue_amount > 0)
        if risk_level is not None:
            conditions.append(combined.c.risk_level == risk_level.value)
        if q:
            pattern = f"%{q.strip()}%"
            conditions.append(
                or_(combined.c.entity_name.ilike(pattern), combined.c.entity_code.ilike(pattern))
            )

        total = (
            await self._session.execute(
                select(func.count()).select_from(combined).where(*conditions)
            )
        ).scalar_one()

        rows_result = (
            await self._session.execute(
                select(combined)
                .where(*conditions)
                .order_by(combined.c.outstanding_amount.desc(), combined.c.entity_name.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()

        rows = [
            OutstandingReportRowData(
                entity_id=row.entity_id,
                entity_name=row.entity_name,
                entity_code=row.entity_code,
                outstanding_amount=row.outstanding_amount,
                overdue_amount=row.overdue_amount,
                current_amount=row.current_amount,
                last_transaction_date=row.last_transaction_date,
                last_payment_date=row.last_payment_date,
                pending_count=row.pending_count,
                risk_level=RiskLevel(row.risk_level),
            )
            for row in rows_result
        ]
        return rows, total

    async def get_outstanding_rows(
        self,
        tenant_id: uuid.UUID,
        *,
        entity_type: EntityType,
        today: date,
        from_date: date | None,
        to_date: date | None,
        outstanding_only: bool,
        overdue_only: bool,
        risk_level: RiskLevel | None,
        q: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[OutstandingReportRowData], int]:
        if entity_type == EntityType.SUPPLIER:
            base = self._supplier_outstanding_base(
                tenant_id, today=today, from_date=from_date, to_date=to_date
            )
            payment_sub = self._supplier_last_payment_subquery(tenant_id)
        else:
            base = self._customer_outstanding_base(
                tenant_id, today=today, from_date=from_date, to_date=to_date
            )
            payment_sub = self._customer_last_payment_subquery(tenant_id)
        return await self._finalize_outstanding_rows(
            base,
            payment_sub,
            outstanding_only=outstanding_only,
            overdue_only=overdue_only,
            risk_level=risk_level,
            q=q,
            page=page,
            page_size=page_size,
        )

    def _customer_aging_base(self, tenant_id: uuid.UUID, *, today: date) -> Select[Any]:
        conditions: list[Any] = [
            Invoice.tenant_id == tenant_id,
            Invoice.deleted_at.is_(None),
            Invoice.status.notin_(_EXCLUDED_INVOICE_STATUSES),
        ]
        overdue_days = sql_cast(literal(today) - Invoice.due_date, Integer)
        is_current = or_(Invoice.due_date.is_(None), Invoice.due_date >= today)
        is_overdue = and_(Invoice.due_date.isnot(None), Invoice.due_date < today)
        bucket_1_30 = and_(is_overdue, overdue_days <= 30)
        bucket_31_60 = and_(is_overdue, overdue_days > 30, overdue_days <= 60)
        bucket_61_90 = and_(is_overdue, overdue_days > 60, overdue_days <= 90)
        bucket_90_plus = and_(is_overdue, overdue_days > 90)
        max_overdue_days = func.max(
            case((and_(is_overdue, Invoice.balance_amount > 0), overdue_days))
        )
        return (
            select(
                Company.id.label("entity_id"),
                Company.name.label("entity_name"),
                Company.code.label("entity_code"),
                func.coalesce(
                    func.sum(case((is_current, Invoice.balance_amount), else_=0)), 0
                ).label("current_amount"),
                func.coalesce(
                    func.sum(case((bucket_1_30, Invoice.balance_amount), else_=0)), 0
                ).label("days_1_30"),
                func.coalesce(
                    func.sum(case((bucket_31_60, Invoice.balance_amount), else_=0)), 0
                ).label("days_31_60"),
                func.coalesce(
                    func.sum(case((bucket_61_90, Invoice.balance_amount), else_=0)), 0
                ).label("days_61_90"),
                func.coalesce(
                    func.sum(case((bucket_90_plus, Invoice.balance_amount), else_=0)), 0
                ).label("days_90_plus"),
                func.coalesce(func.sum(Invoice.balance_amount), 0).label("total"),
                max_overdue_days.label("max_overdue_days"),
            )
            .select_from(Invoice)
            .join(Company, Company.id == Invoice.company_id)
            .where(*conditions)
            .group_by(Company.id, Company.name, Company.code)
        )

    def _supplier_aging_base(self, tenant_id: uuid.UUID, *, today: date) -> Select[Any]:
        """Mirrors _customer_aging_base exactly, on the buy side."""
        conditions: list[Any] = [
            PurchaseBill.tenant_id == tenant_id,
            PurchaseBill.deleted_at.is_(None),
            PurchaseBill.status.notin_(_EXCLUDED_PURCHASE_STATUSES),
        ]
        overdue_days = sql_cast(literal(today) - PurchaseBill.due_date, Integer)
        is_current = or_(PurchaseBill.due_date.is_(None), PurchaseBill.due_date >= today)
        is_overdue = and_(PurchaseBill.due_date.isnot(None), PurchaseBill.due_date < today)
        bucket_1_30 = and_(is_overdue, overdue_days <= 30)
        bucket_31_60 = and_(is_overdue, overdue_days > 30, overdue_days <= 60)
        bucket_61_90 = and_(is_overdue, overdue_days > 60, overdue_days <= 90)
        bucket_90_plus = and_(is_overdue, overdue_days > 90)
        max_overdue_days = func.max(
            case((and_(is_overdue, PurchaseBill.balance_amount > 0), overdue_days))
        )
        return (
            select(
                Supplier.id.label("entity_id"),
                Supplier.name.label("entity_name"),
                Supplier.code.label("entity_code"),
                func.coalesce(
                    func.sum(case((is_current, PurchaseBill.balance_amount), else_=0)), 0
                ).label("current_amount"),
                func.coalesce(
                    func.sum(case((bucket_1_30, PurchaseBill.balance_amount), else_=0)), 0
                ).label("days_1_30"),
                func.coalesce(
                    func.sum(case((bucket_31_60, PurchaseBill.balance_amount), else_=0)), 0
                ).label("days_31_60"),
                func.coalesce(
                    func.sum(case((bucket_61_90, PurchaseBill.balance_amount), else_=0)), 0
                ).label("days_61_90"),
                func.coalesce(
                    func.sum(case((bucket_90_plus, PurchaseBill.balance_amount), else_=0)), 0
                ).label("days_90_plus"),
                func.coalesce(func.sum(PurchaseBill.balance_amount), 0).label("total"),
                max_overdue_days.label("max_overdue_days"),
            )
            .select_from(PurchaseBill)
            .join(Supplier, Supplier.id == PurchaseBill.supplier_id)
            .where(*conditions)
            .group_by(Supplier.id, Supplier.name, Supplier.code)
        )

    async def _finalize_aging_rows(
        self,
        base_query: Select[Any],
        *,
        outstanding_only: bool,
        risk_level: RiskLevel | None,
        q: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[AgingReportRowData], AgingSummaryAggregates, int]:
        """Shared by both branches of get_aging_report. Unlike Outstanding's
        finalize step, there is no payment-date join here - Aging has no
        such column - so this reuses the Sales/Purchase Report trick of a
        single aggregate query whose COUNT(*) doubles as
        `pagination.total_records`, on top of the already-aggregated
        `base_query` (i.e. an aggregate-of-an-aggregate: the entity-level
        GROUP BY happened in `base_query`, this just sums those per-entity
        totals into report-wide bucket totals over the filtered set)."""
        base = base_query.subquery("aging_base")
        combined_select = select(
            base.c.entity_id,
            base.c.entity_name,
            base.c.entity_code,
            base.c.current_amount,
            base.c.days_1_30,
            base.c.days_31_60,
            base.c.days_61_90,
            base.c.days_90_plus,
            base.c.total,
            _risk_level_case(base.c.max_overdue_days).label("risk_level"),
        )
        combined = combined_select.subquery("aging_combined")

        conditions: list[Any] = []
        if outstanding_only:
            conditions.append(combined.c.total > 0)
        if risk_level is not None:
            conditions.append(combined.c.risk_level == risk_level.value)
        if q:
            pattern = f"%{q.strip()}%"
            conditions.append(
                or_(combined.c.entity_name.ilike(pattern), combined.c.entity_code.ilike(pattern))
            )

        agg_row = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(combined.c.current_amount), 0),
                    func.coalesce(func.sum(combined.c.days_1_30), 0),
                    func.coalesce(func.sum(combined.c.days_31_60), 0),
                    func.coalesce(func.sum(combined.c.days_61_90), 0),
                    func.coalesce(func.sum(combined.c.days_90_plus), 0),
                    func.coalesce(func.sum(combined.c.total), 0),
                    func.count(),
                )
                .select_from(combined)
                .where(*conditions)
            )
        ).one()
        summary = AgingSummaryAggregates(
            current_total=agg_row[0],
            days_1_30_total=agg_row[1],
            days_31_60_total=agg_row[2],
            days_61_90_total=agg_row[3],
            days_90_plus_total=agg_row[4],
            grand_total=agg_row[5],
        )
        total_records = agg_row[6]

        rows_result = (
            await self._session.execute(
                select(combined)
                .where(*conditions)
                .order_by(combined.c.total.desc(), combined.c.entity_name.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        rows = [
            AgingReportRowData(
                entity_id=row.entity_id,
                entity_name=row.entity_name,
                entity_code=row.entity_code,
                current_amount=row.current_amount,
                days_1_30=row.days_1_30,
                days_31_60=row.days_31_60,
                days_61_90=row.days_61_90,
                days_90_plus=row.days_90_plus,
                total=row.total,
                risk_level=RiskLevel(row.risk_level),
            )
            for row in rows_result
        ]
        return rows, summary, total_records

    async def get_aging_report(
        self,
        tenant_id: uuid.UUID,
        *,
        entity_type: EntityType,
        today: date,
        outstanding_only: bool,
        risk_level: RiskLevel | None,
        q: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[AgingReportRowData], AgingSummaryAggregates, int]:
        if entity_type == EntityType.SUPPLIER:
            base = self._supplier_aging_base(tenant_id, today=today)
        else:
            base = self._customer_aging_base(tenant_id, today=today)
        return await self._finalize_aging_rows(
            base,
            outstanding_only=outstanding_only,
            risk_level=risk_level,
            q=q,
            page=page,
            page_size=page_size,
        )

    # -- Trip Profitability / Boat Profitability (TASKS.md Sprint 11
    # Session 4 Phase A) --------------------------------------------------
    #
    # `_trip_profitability_base` is the one shared building block: a single
    # row per completed (RETURNED) trip with its revenue/expenses/profit
    # already computed. Trip Profitability paginates it directly; Boat
    # Profitability wraps it in a further GROUP BY boat_id - "Trip
    # Profitability should be reusable by Boat Profitability. Do NOT
    # duplicate calculations" (TASKS.md). Revenue and expenses are each
    # computed by their own separately GROUP-BY'd subquery, keyed by
    # trip_id, then LEFT OUTER JOINed onto Trip - never joined directly
    # into the same query (InvoiceItem rows and TripExpense rows would fan
    # out against each other and corrupt both SUMs), the same join-fan-out
    # avoidance _customer_last_payment_subquery uses for Outstanding
    # Report.

    def _trip_revenue_subquery(self, tenant_id: uuid.UUID) -> Subquery:
        """Trip Revenue = Sum of Invoice Items linked to Trip Catches
        (TASKS.md "PROFIT CALCULATION"), excluding draft/cancelled invoices
        - a cancelled sale was never real revenue, the same posture
        _EXCLUDED_INVOICE_STATUSES enforces everywhere else in this
        module."""
        return (
            select(
                TripCatch.trip_id.label("trip_id"),
                func.coalesce(func.sum(InvoiceItem.line_total), 0).label("revenue"),
            )
            .select_from(TripCatch)
            .join(InvoiceItem, InvoiceItem.trip_catch_id == TripCatch.id)
            .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
            .where(
                TripCatch.tenant_id == tenant_id,
                TripCatch.deleted_at.is_(None),
                InvoiceItem.deleted_at.is_(None),
                Invoice.deleted_at.is_(None),
                Invoice.status.notin_(_EXCLUDED_INVOICE_STATUSES),
            )
            .group_by(TripCatch.trip_id)
            .subquery("trip_revenue")
        )

    def _trip_expense_subquery(self, tenant_id: uuid.UUID) -> Subquery:
        """Trip Expenses = Sum of Trip Expense records (TASKS.md "PROFIT
        CALCULATION")."""
        return (
            select(
                TripExpense.trip_id.label("trip_id"),
                func.coalesce(func.sum(TripExpense.amount), 0).label("expenses"),
            )
            .where(TripExpense.tenant_id == tenant_id, TripExpense.deleted_at.is_(None))
            .group_by(TripExpense.trip_id)
            .subquery("trip_expenses_agg")
        )

    def _trip_profitability_base(
        self,
        tenant_id: uuid.UUID,
        *,
        boat_id: uuid.UUID | None,
        from_date: date | None,
        to_date: date | None,
    ) -> Select[Any]:
        """One row per completed trip - `status == RETURNED` is a hard
        invariant (TASKS.md "Purpose: One row = One completed trip",
        confirmed design decision: planned/departed trips haven't finished,
        cancelled trips never did), not a user-selectable filter. Date
        range filters on the trip's actual return date - the report's own
        primary sort key - never the departure date."""
        revenue_sub = self._trip_revenue_subquery(tenant_id)
        expense_sub = self._trip_expense_subquery(tenant_id)

        conditions: list[Any] = [
            Trip.tenant_id == tenant_id,
            Trip.deleted_at.is_(None),
            Trip.status == TripStatus.RETURNED,
        ]
        if boat_id is not None:
            conditions.append(Trip.boat_id == boat_id)
        if from_date is not None:
            conditions.append(func.date(Trip.actual_return_datetime) >= from_date)
        if to_date is not None:
            conditions.append(func.date(Trip.actual_return_datetime) <= to_date)

        revenue = func.coalesce(revenue_sub.c.revenue, 0)
        expenses = func.coalesce(expense_sub.c.expenses, 0)
        return (
            select(
                Trip.id.label("trip_id"),
                Trip.trip_number.label("trip_number"),
                Trip.boat_id.label("boat_id"),
                Boat.name.label("boat_name"),
                Boat.registration_number.label("registration_number"),
                Boat.is_active.label("boat_is_active"),
                Trip.departure_datetime.label("departure_datetime"),
                Trip.actual_return_datetime.label("actual_return_datetime"),
                Trip.status.label("status"),
                revenue.label("revenue"),
                expenses.label("expenses"),
                (revenue - expenses).label("profit"),
            )
            .select_from(Trip)
            .join(Boat, Boat.id == Trip.boat_id)
            .outerjoin(revenue_sub, revenue_sub.c.trip_id == Trip.id)
            .outerjoin(expense_sub, expense_sub.c.trip_id == Trip.id)
            .where(*conditions)
        )

    def _trip_profitability_conditions(
        self, base: Any, *, profitability: ProfitabilityFilter | None, q: str | None
    ) -> list[Any]:
        conditions: list[Any] = []
        if profitability == ProfitabilityFilter.PROFITABLE:
            conditions.append(base.c.profit > 0)
        elif profitability == ProfitabilityFilter.LOSS:
            conditions.append(base.c.profit < 0)
        if q:
            pattern = f"%{q.strip()}%"
            conditions.append(
                or_(base.c.trip_number.ilike(pattern), base.c.boat_name.ilike(pattern))
            )
        return conditions

    async def get_trip_profitability(
        self,
        tenant_id: uuid.UUID,
        *,
        boat_id: uuid.UUID | None,
        from_date: date | None,
        to_date: date | None,
        profitability: ProfitabilityFilter | None,
        q: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[TripProfitabilityRowData], TripProfitabilityAggregates, int]:
        """Two round trips (aggregate + page), the same discipline every
        other paginated report in this module follows. `most_profitable_*`
        is resolved via a correlated scalar subquery ordered by profit
        DESC LIMIT 1 over the same filtered set, folded into the single
        aggregate query - not a third round trip."""
        base = self._trip_profitability_base(
            tenant_id, boat_id=boat_id, from_date=from_date, to_date=to_date
        ).subquery("trip_profitability_base")
        conditions = self._trip_profitability_conditions(base, profitability=profitability, q=q)

        most_profitable_trip_number = (
            select(base.c.trip_number)
            .where(*conditions)
            .order_by(base.c.profit.desc(), base.c.trip_id.desc())
            .limit(1)
            .scalar_subquery()
        )
        is_loss = base.c.profit < 0
        agg_row = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(base.c.revenue), 0),
                    func.coalesce(func.sum(base.c.expenses), 0),
                    func.coalesce(func.sum(base.c.profit), 0),
                    func.coalesce(func.avg(base.c.profit), 0),
                    func.coalesce(func.avg(base.c.revenue), 0),
                    func.max(base.c.profit),
                    most_profitable_trip_number,
                    func.count(case((is_loss, 1))),
                    func.count(),
                )
                .select_from(base)
                .where(*conditions)
            )
        ).one()
        aggregates = TripProfitabilityAggregates(
            total_revenue=agg_row[0],
            total_expenses=agg_row[1],
            total_profit=agg_row[2],
            average_profit_per_trip=agg_row[3],
            average_revenue_per_trip=agg_row[4],
            most_profitable_trip_profit=agg_row[5],
            most_profitable_trip_number=agg_row[6],
            loss_making_trips=agg_row[7],
            trip_count=agg_row[8],
        )

        rows_result = (
            await self._session.execute(
                select(base)
                .where(*conditions)
                .order_by(
                    base.c.actual_return_datetime.desc(),
                    base.c.trip_number.desc(),
                    base.c.trip_id.desc(),
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        rows = [
            TripProfitabilityRowData(
                trip_id=row.trip_id,
                trip_number=row.trip_number,
                boat_id=row.boat_id,
                boat_name=row.boat_name,
                departure_datetime=row.departure_datetime,
                actual_return_datetime=row.actual_return_datetime,
                status=TripStatus(row.status),
                revenue=row.revenue,
                expenses=row.expenses,
                profit=row.profit,
            )
            for row in rows_result
        ]
        return rows, aggregates, aggregates.trip_count

    def _boat_profitability_base(
        self,
        tenant_id: uuid.UUID,
        *,
        boat_id: uuid.UUID | None,
        from_date: date | None,
        to_date: date | None,
    ) -> Select[Any]:
        """Boat Profitability must aggregate every completed trip belonging
        to the boat (TASKS.md) - built directly on top of
        `_trip_profitability_base`'s own per-trip revenue/expenses/profit,
        never recomputed. A boat with zero completed trips in range never
        appears - INNER JOIN, mirroring Outstanding Report's own "show only
        entities with real history" default."""
        trip_base = self._trip_profitability_base(
            tenant_id, boat_id=boat_id, from_date=from_date, to_date=to_date
        ).subquery("boat_trip_base")
        return (
            select(
                trip_base.c.boat_id,
                trip_base.c.boat_name,
                trip_base.c.registration_number,
                trip_base.c.boat_is_active,
                func.count().label("total_trips"),
                func.coalesce(func.sum(trip_base.c.revenue), 0).label("revenue"),
                func.coalesce(func.sum(trip_base.c.expenses), 0).label("expenses"),
                func.coalesce(func.sum(trip_base.c.profit), 0).label("profit"),
                func.coalesce(func.avg(trip_base.c.profit), 0).label("average_profit_per_trip"),
                func.coalesce(func.avg(trip_base.c.revenue), 0).label("average_revenue_per_trip"),
                func.max(trip_base.c.profit).label("best_trip_profit"),
                func.min(trip_base.c.profit).label("worst_trip_profit"),
                func.max(trip_base.c.actual_return_datetime).label("last_trip_date"),
            )
            .select_from(trip_base)
            .group_by(
                trip_base.c.boat_id,
                trip_base.c.boat_name,
                trip_base.c.registration_number,
                trip_base.c.boat_is_active,
            )
        )

    async def get_boat_profitability(
        self,
        tenant_id: uuid.UUID,
        *,
        boat_id: uuid.UUID | None,
        from_date: date | None,
        to_date: date | None,
        min_trips: int | None,
        profitability: ProfitabilityFilter | None,
        q: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[BoatProfitabilityRowData], BoatProfitabilityAggregates, int]:
        """Two round trips (aggregate + page). `total_boats`/`active_boats`
        and `most_profitable_boat_*` are all resolved from the same
        filtered, boat-grouped set - no separate fleet-wide query, since
        (unlike Outstanding Report's AR/AP) there is no fixed-KPI reason for
        this summary to ignore the request's own filters."""
        grouped = self._boat_profitability_base(
            tenant_id, boat_id=boat_id, from_date=from_date, to_date=to_date
        ).subquery("boat_profitability_grouped")

        conditions: list[Any] = []
        if min_trips is not None:
            conditions.append(grouped.c.total_trips >= min_trips)
        if profitability == ProfitabilityFilter.PROFITABLE:
            conditions.append(grouped.c.profit > 0)
        elif profitability == ProfitabilityFilter.LOSS:
            conditions.append(grouped.c.profit < 0)
        if q:
            pattern = f"%{q.strip()}%"
            conditions.append(
                or_(
                    grouped.c.boat_name.ilike(pattern),
                    grouped.c.registration_number.ilike(pattern),
                )
            )

        most_profitable_boat_name = (
            select(grouped.c.boat_name)
            .where(*conditions)
            .order_by(grouped.c.profit.desc(), grouped.c.boat_id.desc())
            .limit(1)
            .scalar_subquery()
        )
        is_active = grouped.c.boat_is_active.is_(True)
        agg_row = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(grouped.c.revenue), 0),
                    func.coalesce(func.sum(grouped.c.expenses), 0),
                    func.coalesce(func.sum(grouped.c.profit), 0),
                    func.count(),
                    func.count(case((is_active, 1))),
                    func.max(grouped.c.profit),
                    most_profitable_boat_name,
                )
                .select_from(grouped)
                .where(*conditions)
            )
        ).one()
        aggregates = BoatProfitabilityAggregates(
            fleet_revenue=agg_row[0],
            fleet_expenses=agg_row[1],
            fleet_profit=agg_row[2],
            total_boats=agg_row[3],
            active_boats=agg_row[4],
            most_profitable_boat_profit=agg_row[5],
            most_profitable_boat_name=agg_row[6],
        )

        rows_result = (
            await self._session.execute(
                select(grouped)
                .where(*conditions)
                .order_by(grouped.c.profit.desc(), grouped.c.boat_name.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        rows = [
            BoatProfitabilityRowData(
                boat_id=row.boat_id,
                boat_name=row.boat_name,
                registration_number=row.registration_number,
                total_trips=row.total_trips,
                revenue=row.revenue,
                expenses=row.expenses,
                profit=row.profit,
                average_profit_per_trip=row.average_profit_per_trip,
                average_revenue_per_trip=row.average_revenue_per_trip,
                best_trip_profit=row.best_trip_profit,
                worst_trip_profit=row.worst_trip_profit,
                last_trip_date=row.last_trip_date,
            )
            for row in rows_result
        ]
        return rows, aggregates, aggregates.total_boats

    # -- Fish Sales Analytics (TASKS.md Sprint 11 Session 4 Phase B) ------
    #
    # One row per fish, aggregated entirely from invoice_items joined to
    # invoices (for the non-draft/cancelled filter) and fish - "Revenue
    # comes ONLY from Invoice Items. Never use Catch Quantity directly."
    # (TASKS.md). trip_catches/trips are only ever LEFT OUTER JOINed in for
    # trip_count/the boat_id/trip_id filters - an invoice line with no
    # trip_catch_id (purchased/untracked stock) still counts toward
    # revenue/quantity, it simply contributes NULL to the trip aggregation
    # (mirrors DashboardRepository.get_top_fish_by_sales's own join shape,
    # extended with the trip/boat side).

    def _fish_sales_base(
        self,
        tenant_id: uuid.UUID,
        *,
        fish_id: uuid.UUID | None,
        customer_id: uuid.UUID | None,
        boat_id: uuid.UUID | None,
        trip_id: uuid.UUID | None,
        from_date: date | None,
        to_date: date | None,
        q: str | None,
    ) -> Select[Any]:
        conditions: list[Any] = [
            InvoiceItem.tenant_id == tenant_id,
            InvoiceItem.deleted_at.is_(None),
            Invoice.deleted_at.is_(None),
            Invoice.status.notin_(_EXCLUDED_INVOICE_STATUSES),
        ]
        if fish_id is not None:
            conditions.append(InvoiceItem.fish_id == fish_id)
        if customer_id is not None:
            conditions.append(Invoice.company_id == customer_id)
        if boat_id is not None:
            conditions.append(Trip.boat_id == boat_id)
        if trip_id is not None:
            conditions.append(TripCatch.trip_id == trip_id)
        if from_date is not None:
            conditions.append(Invoice.invoice_date >= from_date)
        if to_date is not None:
            conditions.append(Invoice.invoice_date <= to_date)
        if q:
            pattern = f"%{q.strip()}%"
            conditions.append(
                or_(
                    Fish.code.ilike(pattern),
                    Fish.name.ilike(pattern),
                    Fish.local_name.ilike(pattern),
                    Fish.scientific_name.ilike(pattern),
                )
            )

        return (
            select(
                Fish.id.label("fish_id"),
                Fish.name.label("fish_name"),
                Fish.scientific_name.label("scientific_name"),
                Fish.unit.label("unit"),
                func.coalesce(func.sum(InvoiceItem.quantity), 0).label("quantity_sold"),
                func.coalesce(func.sum(InvoiceItem.line_total), 0).label("revenue"),
                func.count(func.distinct(InvoiceItem.invoice_id)).label("invoice_count"),
                func.count(func.distinct(Trip.id)).label("trip_count"),
                func.count(func.distinct(Invoice.company_id)).label("customer_count"),
                func.max(Invoice.invoice_date).label("last_sold_date"),
            )
            .select_from(InvoiceItem)
            .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
            .join(Fish, Fish.id == InvoiceItem.fish_id)
            .outerjoin(TripCatch, TripCatch.id == InvoiceItem.trip_catch_id)
            .outerjoin(Trip, Trip.id == TripCatch.trip_id)
            .where(*conditions)
            .group_by(Fish.id, Fish.name, Fish.scientific_name, Fish.unit)
        )

    async def get_fish_sales(
        self,
        tenant_id: uuid.UUID,
        *,
        fish_id: uuid.UUID | None,
        customer_id: uuid.UUID | None,
        boat_id: uuid.UUID | None,
        trip_id: uuid.UUID | None,
        from_date: date | None,
        to_date: date | None,
        min_quantity: Decimal | None,
        min_revenue: Decimal | None,
        q: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[FishSalesRowData], FishSalesAggregates, int]:
        """Two round trips (aggregate + page) - `total_fish_types_sold`'s
        `COUNT(*)` doubles as `pagination.total_records`, and
        `best_selling_fish_*`/`highest_revenue_fish_*` are each resolved via
        a correlated scalar subquery folded into the same aggregate query,
        the same pattern get_trip_profitability's `most_profitable_trip_*`
        uses - no third round trip."""
        base = self._fish_sales_base(
            tenant_id,
            fish_id=fish_id,
            customer_id=customer_id,
            boat_id=boat_id,
            trip_id=trip_id,
            from_date=from_date,
            to_date=to_date,
            q=q,
        ).subquery("fish_sales_base")

        conditions: list[Any] = []
        if min_quantity is not None:
            conditions.append(base.c.quantity_sold >= min_quantity)
        if min_revenue is not None:
            conditions.append(base.c.revenue >= min_revenue)

        best_selling_fish_name = (
            select(base.c.fish_name)
            .where(*conditions)
            .order_by(base.c.quantity_sold.desc(), base.c.fish_id.desc())
            .limit(1)
            .scalar_subquery()
        )
        highest_revenue_fish_name = (
            select(base.c.fish_name)
            .where(*conditions)
            .order_by(base.c.revenue.desc(), base.c.fish_id.desc())
            .limit(1)
            .scalar_subquery()
        )
        agg_row = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(base.c.quantity_sold), 0),
                    func.coalesce(func.sum(base.c.revenue), 0),
                    func.max(base.c.quantity_sold),
                    best_selling_fish_name,
                    func.max(base.c.revenue),
                    highest_revenue_fish_name,
                    func.count(),
                )
                .select_from(base)
                .where(*conditions)
            )
        ).one()
        aggregates = FishSalesAggregates(
            total_fish_sold=agg_row[0],
            total_revenue=agg_row[1],
            best_selling_fish_quantity=agg_row[2],
            best_selling_fish_name=agg_row[3],
            highest_revenue_fish_revenue=agg_row[4],
            highest_revenue_fish_name=agg_row[5],
            total_fish_types_sold=agg_row[6],
        )

        rows_result = (
            await self._session.execute(
                select(base)
                .where(*conditions)
                .order_by(base.c.revenue.desc(), base.c.fish_name.asc(), base.c.fish_id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        rows = [
            FishSalesRowData(
                fish_id=row.fish_id,
                fish_name=row.fish_name,
                scientific_name=row.scientific_name,
                unit=row.unit,
                quantity_sold=row.quantity_sold,
                revenue=row.revenue,
                invoice_count=row.invoice_count,
                trip_count=row.trip_count,
                customer_count=row.customer_count,
                last_sold_date=row.last_sold_date,
            )
            for row in rows_result
        ]
        return rows, aggregates, aggregates.total_fish_types_sold

    async def get_fish_sales_history(
        self, tenant_id: uuid.UUID, *, fish_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[FishSalesHistoryRowData], int]:
        """The Fish Detail page's own Sales History section - one row per
        individual sale (one invoice item), never aggregated - a distinct
        query shape from get_fish_sales's per-fish GROUP BY, not a
        duplicate of it. Two round trips (count + page), mirroring
        get_ledger_page's own chronological-list style."""
        conditions: list[Any] = [
            InvoiceItem.tenant_id == tenant_id,
            InvoiceItem.deleted_at.is_(None),
            InvoiceItem.fish_id == fish_id,
            Invoice.deleted_at.is_(None),
            Invoice.status.notin_(_EXCLUDED_INVOICE_STATUSES),
        ]

        total = (
            await self._session.execute(
                select(func.count())
                .select_from(InvoiceItem)
                .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
                .where(*conditions)
            )
        ).scalar_one()

        rows_result = (
            await self._session.execute(
                select(
                    Invoice.id.label("invoice_id"),
                    Invoice.invoice_number.label("invoice_number"),
                    Invoice.invoice_date.label("invoice_date"),
                    Company.name.label("customer_name"),
                    Boat.name.label("boat_name"),
                    Trip.trip_number.label("trip_number"),
                    InvoiceItem.quantity.label("quantity"),
                    InvoiceItem.rate.label("unit_price"),
                    InvoiceItem.line_total.label("revenue"),
                )
                .select_from(InvoiceItem)
                .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
                .join(Company, Company.id == Invoice.company_id)
                .outerjoin(TripCatch, TripCatch.id == InvoiceItem.trip_catch_id)
                .outerjoin(Trip, Trip.id == TripCatch.trip_id)
                .outerjoin(Boat, Boat.id == Trip.boat_id)
                .where(*conditions)
                .order_by(
                    Invoice.invoice_date.desc(),
                    Invoice.invoice_number.desc(),
                    InvoiceItem.id.desc(),
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()

        rows = [
            FishSalesHistoryRowData(
                invoice_id=row.invoice_id,
                invoice_number=row.invoice_number,
                invoice_date=row.invoice_date,
                customer_name=row.customer_name,
                boat_name=row.boat_name,
                trip_number=row.trip_number,
                quantity=row.quantity,
                unit_price=row.unit_price,
                revenue=row.revenue,
            )
            for row in rows_result
        ]
        return rows, total
