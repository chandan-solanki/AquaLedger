import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, and_, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.boats.models import Boat
from app.modules.companies.models import Company
from app.modules.dashboard.schemas import _RecentActivityRow
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
from app.modules.trips.constants import ACTIVE_TRIP_STATUSES, TripStatus
from app.modules.trips.models import Trip

# Each module keeps its own copy of "which statuses count as open" rather
# than importing the other module's private constant - mirrors
# InvoiceRepository._OPEN_INVOICE_STATUSES / PurchaseRepository.
# _OPEN_PURCHASE_BILL_STATUSES exactly (ARCHITECTURE.md §2: modules never
# reach into another module's internals).
_OPEN_INVOICE_STATUSES = (InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID)
_OPEN_PURCHASE_BILL_STATUSES = (PurchaseStatus.POSTED, PurchaseStatus.PARTIALLY_PAID)
_NON_SALES_INVOICE_STATUSES = (InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED)
# Sprint 10 Session 3's chart queries: same "real sale" definition, applied
# to purchase bills - drafts never happened, cancelled bills don't count as
# spend.
_NON_PURCHASE_BILL_STATUSES = (PurchaseStatus.DRAFT, PurchaseStatus.CANCELLED)


@dataclass(frozen=True)
class InvoiceAggregates:
    todays_sales: Decimal
    monthly_sales: Decimal
    draft_count: int
    issued_this_month_count: int
    overdue_count: int
    overdue_amount: Decimal
    stale_draft_count: int


@dataclass(frozen=True)
class PaymentAggregates:
    customer_payments_today: Decimal
    draft_count: int
    stale_draft_count: int


@dataclass(frozen=True)
class PurchaseBillAggregates:
    posted_this_month_count: int
    overdue_count: int
    overdue_amount: Decimal


@dataclass(frozen=True)
class TripAggregates:
    trips_today: int
    trips_active: int
    trips_completed_today: int
    boats_at_sea: int


@dataclass(frozen=True)
class BoatAggregates:
    active_count: int
    maintenance_count: int
    license_expiring_count: int
    insurance_expiring_count: int


class DashboardRepository:
    """Read-only aggregate queries spanning every module the owner's
    homepage summarizes.

    ARCHITECTURE.md §2's "modules talk to each other only through
    service.py" rule exists to stop *business logic* (writes, invariants)
    from leaking across module boundaries. A pure reporting endpoint that
    only ever SELECTs is the documented exception: ARCHITECTURE.md §29
    carves out a dedicated read-only `app_ro` DB role explicitly for
    "reporting + AI", and §2 itself lists `reporting`/`analytics` as their
    own modules precisely because they read across the whole schema. This
    repository is that shape - it imports other modules' ORM models
    directly (never their repository/service internals) and never
    executes an INSERT/UPDATE/DELETE.

    Each method below computes several related numbers for one source
    table in a single grouped/conditional-aggregate query (COUNT/SUM/CASE/
    COALESCE) instead of one round trip per number - TASKS.md's "single
    service call, minimal queries, avoid N+1", applied per table. The
    service layer issues one such query per table (about a dozen total),
    never loads full rows to sum in Python.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_invoice_aggregates(
        self,
        tenant_id: uuid.UUID,
        *,
        today: date,
        month_start: date,
        stale_draft_cutoff: datetime,
    ) -> InvoiceAggregates:
        not_draft_or_cancelled = Invoice.status.notin_(_NON_SALES_INVOICE_STATUSES)
        todays_sale_amount = case(
            (
                and_(Invoice.invoice_date == today, not_draft_or_cancelled),
                Invoice.total_amount,
            ),
            else_=0,
        )
        monthly_sale_amount = case(
            (
                and_(Invoice.invoice_date >= month_start, not_draft_or_cancelled),
                Invoice.total_amount,
            ),
            else_=0,
        )
        is_overdue = and_(
            Invoice.status.in_(_OPEN_INVOICE_STATUSES),
            Invoice.due_date.isnot(None),
            Invoice.due_date < today,
            Invoice.balance_amount > 0,
        )
        row = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(todays_sale_amount), 0),
                    func.coalesce(func.sum(monthly_sale_amount), 0),
                    func.count(case((Invoice.status == InvoiceStatus.DRAFT, 1))),
                    func.count(
                        case(
                            (
                                and_(
                                    Invoice.issued_at.isnot(None),
                                    Invoice.issued_at >= month_start,
                                ),
                                1,
                            )
                        )
                    ),
                    func.count(case((is_overdue, 1))),
                    func.coalesce(func.sum(case((is_overdue, Invoice.balance_amount), else_=0)), 0),
                    func.count(
                        case(
                            (
                                and_(
                                    Invoice.status == InvoiceStatus.DRAFT,
                                    Invoice.created_at < stale_draft_cutoff,
                                ),
                                1,
                            )
                        )
                    ),
                ).where(Invoice.tenant_id == tenant_id, Invoice.deleted_at.is_(None))
            )
        ).one()
        return InvoiceAggregates(
            todays_sales=row[0],
            monthly_sales=row[1],
            draft_count=row[2],
            issued_this_month_count=row[3],
            overdue_count=row[4],
            overdue_amount=row[5],
            stale_draft_count=row[6],
        )

    async def get_payment_aggregates(
        self,
        tenant_id: uuid.UUID,
        *,
        today: date,
        stale_draft_cutoff: datetime,
    ) -> PaymentAggregates:
        todays_posted_amount = case(
            (
                and_(Payment.payment_date == today, Payment.status == PaymentStatus.POSTED),
                Payment.amount,
            ),
            else_=0,
        )
        row = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(todays_posted_amount), 0),
                    func.count(case((Payment.status == PaymentStatus.DRAFT, 1))),
                    func.count(
                        case(
                            (
                                and_(
                                    Payment.status == PaymentStatus.DRAFT,
                                    Payment.created_at < stale_draft_cutoff,
                                ),
                                1,
                            )
                        )
                    ),
                ).where(Payment.tenant_id == tenant_id, Payment.deleted_at.is_(None))
            )
        ).one()
        return PaymentAggregates(
            customer_payments_today=row[0], draft_count=row[1], stale_draft_count=row[2]
        )

    async def get_supplier_payments_today(self, tenant_id: uuid.UUID, *, today: date) -> Decimal:
        result = await self._session.execute(
            select(func.coalesce(func.sum(SupplierPayment.amount), 0)).where(
                SupplierPayment.tenant_id == tenant_id,
                SupplierPayment.deleted_at.is_(None),
                SupplierPayment.payment_date == today,
                SupplierPayment.status == SupplierPaymentStatus.POSTED,
            )
        )
        return result.scalar_one()

    async def get_purchase_bill_aggregates(
        self, tenant_id: uuid.UUID, *, today: date, month_start: date
    ) -> PurchaseBillAggregates:
        is_overdue = and_(
            PurchaseBill.status.in_(_OPEN_PURCHASE_BILL_STATUSES),
            PurchaseBill.due_date.isnot(None),
            PurchaseBill.due_date < today,
            PurchaseBill.balance_amount > 0,
        )
        row = (
            await self._session.execute(
                select(
                    func.count(
                        case(
                            (
                                and_(
                                    PurchaseBill.posted_at.isnot(None),
                                    PurchaseBill.posted_at >= month_start,
                                ),
                                1,
                            )
                        )
                    ),
                    func.count(case((is_overdue, 1))),
                    func.coalesce(
                        func.sum(case((is_overdue, PurchaseBill.balance_amount), else_=0)), 0
                    ),
                ).where(PurchaseBill.tenant_id == tenant_id, PurchaseBill.deleted_at.is_(None))
            )
        ).one()
        return PurchaseBillAggregates(
            posted_this_month_count=row[0], overdue_count=row[1], overdue_amount=row[2]
        )

    async def get_trip_aggregates(self, tenant_id: uuid.UUID, *, today: date) -> TripAggregates:
        row = (
            await self._session.execute(
                select(
                    func.count(case((func.date(Trip.departure_datetime) == today, 1))),
                    func.count(case((Trip.status.in_(ACTIVE_TRIP_STATUSES), 1))),
                    func.count(
                        case(
                            (
                                and_(
                                    Trip.status == TripStatus.RETURNED,
                                    func.date(Trip.actual_return_datetime) == today,
                                ),
                                1,
                            )
                        )
                    ),
                    func.count(
                        func.distinct(case((Trip.status == TripStatus.DEPARTED, Trip.boat_id)))
                    ),
                ).where(Trip.tenant_id == tenant_id, Trip.deleted_at.is_(None))
            )
        ).one()
        return TripAggregates(
            trips_today=row[0],
            trips_active=row[1],
            trips_completed_today=row[2],
            boats_at_sea=row[3],
        )

    async def get_boat_aggregates(
        self, tenant_id: uuid.UUID, *, today: date, expiry_window_end: date
    ) -> BoatAggregates:
        row = (
            await self._session.execute(
                select(
                    func.count(case((Boat.is_active.is_(True), 1))),
                    func.count(case((Boat.is_active.is_(False), 1))),
                    func.count(
                        case(
                            (
                                and_(
                                    Boat.is_active.is_(True),
                                    Boat.license_expiry.isnot(None),
                                    Boat.license_expiry >= today,
                                    Boat.license_expiry <= expiry_window_end,
                                ),
                                1,
                            )
                        )
                    ),
                    func.count(
                        case(
                            (
                                and_(
                                    Boat.is_active.is_(True),
                                    Boat.insurance_expiry.isnot(None),
                                    Boat.insurance_expiry >= today,
                                    Boat.insurance_expiry <= expiry_window_end,
                                ),
                                1,
                            )
                        )
                    ),
                ).where(Boat.tenant_id == tenant_id, Boat.deleted_at.is_(None))
            )
        ).one()
        return BoatAggregates(
            active_count=row[0],
            maintenance_count=row[1],
            license_expiring_count=row[2],
            insurance_expiring_count=row[3],
        )

    async def get_todays_catch_quantity(self, tenant_id: uuid.UUID, *, today: date) -> Decimal:
        result = await self._session.execute(
            select(func.coalesce(func.sum(TripCatch.quantity_caught), 0)).where(
                TripCatch.tenant_id == tenant_id,
                TripCatch.deleted_at.is_(None),
                TripCatch.landing_date == today,
            )
        )
        return result.scalar_one()

    async def get_customer_outstanding(self, tenant_id: uuid.UUID) -> Decimal:
        """Sums the already-reconciled `companies.outstanding_amount` cache
        (ARCHITECTURE.md §5.3) rather than re-deriving from invoices/
        payments - the invoicing/payments modules already keep it correct
        from source on every transaction, so re-summing invoice balances
        here would just be the same number computed twice."""
        result = await self._session.execute(
            select(func.coalesce(func.sum(Company.outstanding_amount), 0)).where(
                Company.tenant_id == tenant_id, Company.deleted_at.is_(None)
            )
        )
        return result.scalar_one()

    async def get_supplier_outstanding(self, tenant_id: uuid.UUID) -> Decimal:
        """Mirrors get_customer_outstanding on the buy side - sums
        `suppliers.outstanding_amount`, the cache the purchase/
        supplier_payments modules already reconcile from source."""
        result = await self._session.execute(
            select(func.coalesce(func.sum(Supplier.outstanding_amount), 0)).where(
                Supplier.tenant_id == tenant_id, Supplier.deleted_at.is_(None)
            )
        )
        return result.scalar_one()

    async def recent_invoices(
        self, tenant_id: uuid.UUID, *, limit: int
    ) -> list[_RecentActivityRow]:
        rows = (
            await self._session.execute(
                select(Invoice.id, Invoice.invoice_number, Company.name, Invoice.created_at)
                .join(Company, Company.id == Invoice.company_id)
                .where(Invoice.tenant_id == tenant_id, Invoice.deleted_at.is_(None))
                .order_by(Invoice.created_at.desc())
                .limit(limit)
            )
        ).all()
        return [
            _RecentActivityRow(
                id=row.id,
                reference=row.invoice_number or "Draft",
                title=f"Invoice to {row.name}",
                created_at=row.created_at,
            )
            for row in rows
        ]

    async def recent_payments(
        self, tenant_id: uuid.UUID, *, limit: int
    ) -> list[_RecentActivityRow]:
        rows = (
            await self._session.execute(
                select(Payment.id, Payment.payment_number, Company.name, Payment.created_at)
                .join(Company, Company.id == Payment.company_id)
                .where(Payment.tenant_id == tenant_id, Payment.deleted_at.is_(None))
                .order_by(Payment.created_at.desc())
                .limit(limit)
            )
        ).all()
        return [
            _RecentActivityRow(
                id=row.id,
                reference=row.payment_number or "Draft",
                title=f"Payment received from {row.name}",
                created_at=row.created_at,
            )
            for row in rows
        ]

    async def recent_trips(self, tenant_id: uuid.UUID, *, limit: int) -> list[_RecentActivityRow]:
        rows = (
            await self._session.execute(
                select(Trip.id, Trip.trip_number, Boat.name, Trip.created_at)
                .join(Boat, Boat.id == Trip.boat_id)
                .where(Trip.tenant_id == tenant_id, Trip.deleted_at.is_(None))
                .order_by(Trip.created_at.desc())
                .limit(limit)
            )
        ).all()
        return [
            _RecentActivityRow(
                id=row.id,
                reference=row.trip_number,
                title=f"Trip {row.trip_number} ({row.name})",
                created_at=row.created_at,
            )
            for row in rows
        ]

    async def recent_purchase_bills(
        self, tenant_id: uuid.UUID, *, limit: int
    ) -> list[_RecentActivityRow]:
        rows = (
            await self._session.execute(
                select(
                    PurchaseBill.id,
                    PurchaseBill.bill_number,
                    Supplier.name,
                    PurchaseBill.created_at,
                )
                .join(Supplier, Supplier.id == PurchaseBill.supplier_id)
                .where(PurchaseBill.tenant_id == tenant_id, PurchaseBill.deleted_at.is_(None))
                .order_by(PurchaseBill.created_at.desc())
                .limit(limit)
            )
        ).all()
        return [
            _RecentActivityRow(
                id=row.id,
                reference=row.bill_number or "Draft",
                title=f"Purchase bill from {row.name}",
                created_at=row.created_at,
            )
            for row in rows
        ]

    async def recent_supplier_payments(
        self, tenant_id: uuid.UUID, *, limit: int
    ) -> list[_RecentActivityRow]:
        rows = (
            await self._session.execute(
                select(
                    SupplierPayment.id,
                    SupplierPayment.payment_number,
                    Supplier.name,
                    SupplierPayment.created_at,
                )
                .join(Supplier, Supplier.id == SupplierPayment.supplier_id)
                .where(SupplierPayment.tenant_id == tenant_id, SupplierPayment.deleted_at.is_(None))
                .order_by(SupplierPayment.created_at.desc())
                .limit(limit)
            )
        ).all()
        return [
            _RecentActivityRow(
                id=row.id,
                reference=row.payment_number or "Draft",
                title=f"Payment made to {row.name}",
                created_at=row.created_at,
            )
            for row in rows
        ]

    async def get_monthly_sales_by_month(
        self, tenant_id: uuid.UUID, *, earliest_month: date
    ) -> dict[date, tuple[Decimal, int]]:
        """Sprint 10 Session 3 "CHART 1": one grouped query, `DATE_TRUNC`'d
        to the calendar month, for every month from `earliest_month`
        onward - never one query per month. Months with zero sales simply
        don't appear in the returned dict; the service zero-fills the full
        trailing-12-month range from this (a chart must never show a gap
        as if data were missing rather than genuinely zero)."""
        not_draft_or_cancelled = Invoice.status.notin_(_NON_SALES_INVOICE_STATUSES)
        month = cast(func.date_trunc("month", Invoice.invoice_date), Date)
        rows = (
            await self._session.execute(
                select(month, func.coalesce(func.sum(Invoice.total_amount), 0), func.count())
                .where(
                    Invoice.tenant_id == tenant_id,
                    Invoice.deleted_at.is_(None),
                    not_draft_or_cancelled,
                    Invoice.invoice_date >= earliest_month,
                )
                .group_by(month)
            )
        ).all()
        return {row[0]: (row[1], row[2]) for row in rows}

    async def get_monthly_purchases_by_month(
        self, tenant_id: uuid.UUID, *, earliest_month: date
    ) -> dict[date, tuple[Decimal, int]]:
        """Mirrors get_monthly_sales_by_month on the buy side for Sprint 10
        Session 3 "CHART 2", grouped by `bill_date` the same way sales is
        grouped by `invoice_date` (the business transaction date, not
        `posted_at`)."""
        not_draft_or_cancelled = PurchaseBill.status.notin_(_NON_PURCHASE_BILL_STATUSES)
        month = cast(func.date_trunc("month", PurchaseBill.bill_date), Date)
        rows = (
            await self._session.execute(
                select(month, func.coalesce(func.sum(PurchaseBill.total_amount), 0), func.count())
                .where(
                    PurchaseBill.tenant_id == tenant_id,
                    PurchaseBill.deleted_at.is_(None),
                    not_draft_or_cancelled,
                    PurchaseBill.bill_date >= earliest_month,
                )
                .group_by(month)
            )
        ).all()
        return {row[0]: (row[1], row[2]) for row in rows}

    async def get_top_fish_by_sales(
        self, tenant_id: uuid.UUID, *, limit: int
    ) -> list[tuple[str, Decimal, Decimal]]:
        """Sprint 10 Session 3 "CHART 3": one grouped, `ORDER BY ... LIMIT`
        query across `invoice_items` joined to `invoices` (for the non-
        draft/cancelled filter) and `fish` (for the display name) - never
        loads every invoice item to sum in Python."""
        not_draft_or_cancelled = Invoice.status.notin_(_NON_SALES_INVOICE_STATUSES)
        quantity_sold = func.coalesce(func.sum(InvoiceItem.quantity), 0)
        sales_amount = func.coalesce(func.sum(InvoiceItem.line_total), 0)
        rows = (
            await self._session.execute(
                select(Fish.name, quantity_sold, sales_amount)
                .select_from(InvoiceItem)
                .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
                .join(Fish, Fish.id == InvoiceItem.fish_id)
                .where(
                    InvoiceItem.tenant_id == tenant_id,
                    InvoiceItem.deleted_at.is_(None),
                    Invoice.deleted_at.is_(None),
                    not_draft_or_cancelled,
                )
                .group_by(Fish.id, Fish.name)
                .order_by(sales_amount.desc())
                .limit(limit)
            )
        ).all()
        return [(row[0], row[1], row[2]) for row in rows]

    async def get_top_customers(
        self, tenant_id: uuid.UUID, *, limit: int
    ) -> list[tuple[uuid.UUID, str, Decimal, int, Decimal]]:
        """Sprint 10 Session 4 "WIDGET 1 Top Customers": one grouped, `ORDER
        BY total_sales DESC LIMIT` query joining non-draft/cancelled
        invoices to their company - `outstanding_amount` is the same
        reconciled `companies.outstanding_amount` cache
        `get_customer_outstanding` sums, read per-row here rather than
        re-derived from invoice balances."""
        not_draft_or_cancelled = Invoice.status.notin_(_NON_SALES_INVOICE_STATUSES)
        total_sales = func.coalesce(func.sum(Invoice.total_amount), 0)
        rows = (
            await self._session.execute(
                select(
                    Company.id,
                    Company.name,
                    total_sales,
                    func.count(Invoice.id),
                    Company.outstanding_amount,
                )
                .select_from(Invoice)
                .join(Company, Company.id == Invoice.company_id)
                .where(
                    Invoice.tenant_id == tenant_id,
                    Invoice.deleted_at.is_(None),
                    Company.deleted_at.is_(None),
                    not_draft_or_cancelled,
                )
                .group_by(Company.id, Company.name, Company.outstanding_amount)
                .order_by(total_sales.desc())
                .limit(limit)
            )
        ).all()
        return [(row[0], row[1], row[2], row[3], row[4]) for row in rows]

    async def get_top_suppliers(
        self, tenant_id: uuid.UUID, *, limit: int
    ) -> list[tuple[uuid.UUID, str, Decimal, int, Decimal]]:
        """Mirrors get_top_customers on the buy side for "WIDGET 2 Top
        Suppliers" - non-draft/cancelled purchase bills grouped by
        supplier, ordered by `purchase_total` descending."""
        not_draft_or_cancelled = PurchaseBill.status.notin_(_NON_PURCHASE_BILL_STATUSES)
        purchase_total = func.coalesce(func.sum(PurchaseBill.total_amount), 0)
        rows = (
            await self._session.execute(
                select(
                    Supplier.id,
                    Supplier.name,
                    purchase_total,
                    func.count(PurchaseBill.id),
                    Supplier.outstanding_amount,
                )
                .select_from(PurchaseBill)
                .join(Supplier, Supplier.id == PurchaseBill.supplier_id)
                .where(
                    PurchaseBill.tenant_id == tenant_id,
                    PurchaseBill.deleted_at.is_(None),
                    Supplier.deleted_at.is_(None),
                    not_draft_or_cancelled,
                )
                .group_by(Supplier.id, Supplier.name, Supplier.outstanding_amount)
                .order_by(purchase_total.desc())
                .limit(limit)
            )
        ).all()
        return [(row[0], row[1], row[2], row[3], row[4]) for row in rows]

    async def get_top_fish_widget(
        self, tenant_id: uuid.UUID, *, limit: int
    ) -> list[tuple[uuid.UUID, str, Decimal, Decimal]]:
        """"WIDGET 3 Top Fish" - the same non-draft/cancelled, grouped/
        ordered/limited query as get_top_fish_by_sales (Session 3's chart),
        kept as its own method rather than reused because this widget also
        needs `fish_id` for drill-down navigation, which the chart series
        has no use for."""
        not_draft_or_cancelled = Invoice.status.notin_(_NON_SALES_INVOICE_STATUSES)
        quantity_sold = func.coalesce(func.sum(InvoiceItem.quantity), 0)
        sales_amount = func.coalesce(func.sum(InvoiceItem.line_total), 0)
        rows = (
            await self._session.execute(
                select(Fish.id, Fish.name, quantity_sold, sales_amount)
                .select_from(InvoiceItem)
                .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
                .join(Fish, Fish.id == InvoiceItem.fish_id)
                .where(
                    InvoiceItem.tenant_id == tenant_id,
                    InvoiceItem.deleted_at.is_(None),
                    Invoice.deleted_at.is_(None),
                    not_draft_or_cancelled,
                )
                .group_by(Fish.id, Fish.name)
                .order_by(sales_amount.desc())
                .limit(limit)
            )
        ).all()
        return [(row[0], row[1], row[2], row[3]) for row in rows]

    async def get_trip_status_counts(self, tenant_id: uuid.UUID) -> dict[TripStatus, int]:
        """Sprint 10 Session 3 "CHART 4": one `GROUP BY status` query - the
        service zero-fills any of the four statuses absent from this (tiny,
        already-aggregated) result rather than this method returning a
        sparse or padded dict itself."""
        rows = (
            await self._session.execute(
                select(Trip.status, func.count())
                .where(Trip.tenant_id == tenant_id, Trip.deleted_at.is_(None))
                .group_by(Trip.status)
            )
        ).all()
        return {TripStatus(row[0]): row[1] for row in rows}
