from enum import StrEnum


class PurchaseStatus(StrEnum):
    DRAFT = "draft"
    POSTED = "posted"
    CANCELLED = "cancelled"


# Numbers are assigned only at posting (TASKS.md Session 5), the same
# reasoning ARCHITECTURE.md §13.1 gives for invoice_number: an abandoned
# draft must never punch a permanent hole in the sequence. The constant is
# defined now (config, not numbering logic) for Session 5 to consume -
# format "PUR/2026-27/00001".
PURCHASE_NUMBER_PREFIX = "PUR"
