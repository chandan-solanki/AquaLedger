"""Pure derivation of a delivery challan item's remaining deliverable
quantity (Sprint 12 Session 14). No SQLAlchemy, no FastAPI, no I/O - mirrors
app.modules.purchase_orders.domain.billing's "pure domain logic" posture.

Unlike Purchase Order billing, there is no derived header-level "status"
here to compute - a delivery challan carries no financial totals at all, so
the only real invariant worth a pure, independently-testable function is
this one subtraction. `already_delivered_quantity` is expected to already
be aggregated (via DeliveryChallanRepository.sum_delivered_by_invoice_items)
across every non-deleted, non-CANCELLED delivery challan item that
references the same invoice item - the same "DRAFT counts as a live
reservation" discipline PurchaseRepository.sum_billed_quantity_for_po_item
documents for Purchase Bill items.
"""

from decimal import Decimal


def remaining_quantity(invoiced_quantity: Decimal, already_delivered_quantity: Decimal) -> Decimal:
    """Can go negative if something was over-delivered despite the write-time
    guard (e.g. a race, or data seeded directly) - the same posture
    purchase_orders.domain.billing.PurchaseOrderItemBilling's own
    remaining_quantity takes; callers must not assume non-negativity."""
    return invoiced_quantity - already_delivered_quantity
