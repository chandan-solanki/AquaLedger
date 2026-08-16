from enum import StrEnum


class PurchaseOrderStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class PurchaseOrderBillingStatus(StrEnum):
    """Derived (never stored - Sprint 12 Session 12) billing progress of a
    purchase order, computed on every read from live PurchaseBillItem
    quantities via app.modules.purchase_orders.domain.billing. Distinct
    from PurchaseOrderStatus: a CONFIRMED order can be FULLY_BILLED and
    stay CONFIRMED indefinitely - billing never drives the lifecycle
    transition to FULFILLED (that remains an explicit, manual action)."""

    NOT_BILLED = "not_billed"
    PARTIALLY_BILLED = "partially_billed"
    FULLY_BILLED = "fully_billed"


# Numbers are assigned only at confirmation, mirroring PURCHASE_NUMBER_PREFIX's
# reasoning (app.modules.purchase.constants): an abandoned draft must never
# punch a permanent hole in the sequence. Format "PO/2026-27/00001".
PURCHASE_ORDER_NUMBER_PREFIX = "PO"
