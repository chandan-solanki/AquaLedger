from enum import StrEnum


class TransactionType(StrEnum):
    """The two ledger transaction kinds a Customer Ledger entry can be
    (TASKS.md Sprint 11 Session 1) - also the accepted values for the
    `transaction_type` filter on GET /reports/customer-ledger. Deliberately
    excludes "opening_balance"/"closing_balance": those are summary-only
    concepts (CustomerLedgerSummary), never rows in `entries`.
    """

    INVOICE = "invoice"
    PAYMENT = "payment"


class SupplierTransactionType(StrEnum):
    """The two ledger transaction kinds a Supplier Ledger entry can be
    (TASKS.md Sprint 11 Session 2) - also the accepted values for the
    `transaction_type` filter on GET /reports/supplier-ledger. A separate
    enum from `TransactionType` rather than reused values: "invoice"/
    "payment" would be the wrong words for a buy-side bill/payment, and
    each ledger's filter should only ever accept its own vocabulary.
    """

    PURCHASE_BILL = "purchase_bill"
    SUPPLIER_PAYMENT = "supplier_payment"


class PaidStatus(StrEnum):
    """Derived payment-progress filter for the Sales/Purchase Report
    (TASKS.md Sprint 11 Session 3) - computed from paid_amount vs
    total_amount at query time, independent of the document's own `status`
    column. Shared by both reports: the concept ("how much of this
    document has been paid") is identical for an invoice and a purchase
    bill."""

    UNPAID = "unpaid"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"


class EntityType(StrEnum):
    """Which side of the ledger the Outstanding/Aging Report's `entity_type`
    tab shows (TASKS.md Sprint 11 Session 3 Phase B) - one row per customer
    (company) or per supplier, never one row per transaction."""

    CUSTOMER = "customer"
    SUPPLIER = "supplier"


class RiskLevel(StrEnum):
    """The Outstanding/Aging Report's dynamic risk indicator - never stored,
    always derived from the single oldest unpaid invoice/bill's days-overdue
    at query time (TASKS.md Sprint 11 Session 3 Phase B "RISK INDICATOR"):
    no overdue balance at all -> LOW; the oldest overdue amount sits in the
    1-30 or 31-60 day bucket -> MEDIUM; the oldest overdue amount sits in
    the 61-90 or 90+ day bucket -> HIGH. See
    ReportsRepository._risk_level_case's docstring for exactly how the two
    aging buckets collapse into each of these three tiers.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProfitabilityFilter(StrEnum):
    """The Trip/Boat Profitability reports' single "Profitability" filter
    (TASKS.md Sprint 11 Session 4 Phase A) - `Profitable Only`/`Loss Only`
    are presented as one mutually-exclusive choice, not two independent
    toggles, unlike Outstanding Report's `outstanding_only`/`overdue_only`
    (which are genuinely orthogonal). A trip/boat with exactly zero profit
    matches neither value."""

    PROFITABLE = "profitable"
    LOSS = "loss"
