from enum import StrEnum


class PaymentStatus(StrEnum):
    DRAFT = "draft"
    POSTED = "posted"
    CANCELLED = "cancelled"


class PaymentMethod(StrEnum):
    """ARCHITECTURE.md §5.2's `payments.method` set. Stored as a plain
    String column (like `invoices.status`), not a DB-level enum - same
    rationale as InvoiceStatus."""

    CASH = "cash"
    UPI = "upi"
    CHEQUE = "cheque"
    BANK_TRANSFER = "bank_transfer"
    CARD = "card"
    ADJUSTMENT = "adjustment"


# Payment numbers are assigned only at posting (TASKS.md Session 5), the
# same reasoning ARCHITECTURE.md §13.1 gives for invoice_number: an
# abandoned draft must never punch a permanent hole in the sequence.
PAYMENT_NUMBER_PREFIX = "PAY"
