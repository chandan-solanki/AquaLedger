from enum import StrEnum


class SupplierPaymentStatus(StrEnum):
    DRAFT = "draft"
    POSTED = "posted"
    CANCELLED = "cancelled"


class PaymentMethod(StrEnum):
    """Mirrors app.modules.payments.constants.PaymentMethod on the buy side -
    each module keeps its own copy rather than importing the other's, since
    modules never reach into each other's internals (ARCHITECTURE.md §2)."""

    CASH = "cash"
    UPI = "upi"
    CHEQUE = "cheque"
    BANK_TRANSFER = "bank_transfer"
    CARD = "card"
    ADJUSTMENT = "adjustment"


# Numbers are assigned only at posting (TASKS.md Sprint 12 Session 5), the
# same reasoning ARCHITECTURE.md §13.1 gives for invoice_number: an
# abandoned draft must never punch a permanent hole in the sequence. The
# constant is defined now (config, not numbering logic) for Session 5 to
# consume - format "SPAY/2026-27/00001".
SUPPLIER_PAYMENT_NUMBER_PREFIX = "SPAY"
