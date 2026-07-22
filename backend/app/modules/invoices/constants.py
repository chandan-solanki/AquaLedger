from enum import StrEnum


class InvoiceStatus(StrEnum):
    DRAFT = "draft"
    ISSUED = "issued"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    CANCELLED = "cancelled"


# "overdue" is deliberately not a member: ARCHITECTURE.md §13.2 defines it as
# derived (due_date < today AND balance_amount > 0), never stored - a nightly
# job that flips a status column would always be a day stale by month-end.

# Fixed for now - ARCHITECTURE.md §13.1's invoice_sequences schema supports a
# per-tenant configurable prefix, but nothing in TASKS.md's six sessions asks
# for multiple series per tenant, so a single constant prefix is the
# simplest thing that satisfies the spec without inventing an unrequested
# "invoice series" concept.
INVOICE_NUMBER_PREFIX = "INV"
