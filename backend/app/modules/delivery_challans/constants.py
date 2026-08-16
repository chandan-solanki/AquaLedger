from enum import StrEnum


class DeliveryChallanStatus(StrEnum):
    """Mirrors PurchaseOrderStatus's shape exactly (Sprint 12 Session 14):
    DRAFT -> DISPATCHED -> DELIVERED (terminal), with CANCELLED reachable
    from DRAFT or DISPATCHED - never from DELIVERED. DISPATCHED is this
    module's counterpart of PurchaseOrderStatus.CONFIRMED ("the goods have
    left / the event is real, not just a draft") and DELIVERED is the
    counterpart of FULFILLED."""

    DRAFT = "draft"
    DISPATCHED = "dispatched"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# Numbers are assigned only at dispatch - the transition where this document
# stops being a mutable draft and becomes a real, physical event - mirroring
# PURCHASE_ORDER_NUMBER_PREFIX's reasoning (app.modules.purchase_orders.constants):
# an abandoned draft must never punch a permanent hole in the sequence.
# Format "DC/2026-27/00001".
DELIVERY_CHALLAN_NUMBER_PREFIX = "DC"
