from enum import StrEnum


class ActivityType(StrEnum):
    """Sources fanned into the Section 4 "recent activity" feed."""

    INVOICE = "invoice"
    PAYMENT = "payment"
    TRIP = "trip"
    PURCHASE_BILL = "purchase_bill"
    SUPPLIER_PAYMENT = "supplier_payment"


class AlertType(StrEnum):
    """The six backend-supported alert kinds (TASKS.md Sprint 10 Session 1,
    "SECTION 5 Alerts") - deliberately closed. Do not add a member here
    without a corresponding real aggregate query in repository.py; the spec
    is explicit that alerts must never be invented."""

    BOAT_LICENSE_EXPIRING = "boat_license_expiring"
    BOAT_INSURANCE_EXPIRING = "boat_insurance_expiring"
    INVOICE_OVERDUE = "invoice_overdue"
    PURCHASE_BILL_OVERDUE = "purchase_bill_overdue"
    DRAFT_INVOICE_STALE = "draft_invoice_stale"
    DRAFT_PAYMENT_STALE = "draft_payment_stale"


# Section 4: "Limit 10."
RECENT_ACTIVITY_LIMIT = 10

# Section 5's "configurable threshold" for stale drafts - a plain module
# constant (like INVOICE_NUMBER_PREFIX elsewhere), not a per-tenant settings
# row: nothing in this session's spec asks for tenant-level configurability,
# only that the number itself not be hardcoded inline at every call site.
DRAFT_STALE_THRESHOLD_DAYS = 3

# How far ahead to look for boat license/insurance expiries. Same
# module-constant rationale as DRAFT_STALE_THRESHOLD_DAYS.
EXPIRY_WARNING_WINDOW_DAYS = 30

# TASKS.md Sprint 10 Session 3, "CHART 1"/"CHART 2": "Last 12 months."
CHART_MONTHS = 12

# TASKS.md Sprint 10 Session 3, "CHART 3": "Return Top 10 fish."
TOP_FISH_LIMIT = 10

# TASKS.md Sprint 10 Session 4 widgets: "Return Top 5" for customers,
# suppliers and fish - deliberately smaller than the chart's top 10, since
# these are compact table widgets, not a chart axis.
TOP_CUSTOMERS_LIMIT = 5
TOP_SUPPLIERS_LIMIT = 5
TOP_FISH_WIDGET_LIMIT = 5
