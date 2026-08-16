"""Pure derivation of a purchase order's billing progress from Purchase
Bill data already aggregated elsewhere (Sprint 12 Session 12). No
SQLAlchemy, no FastAPI, no I/O - mirrors domain/totals.py's own "pure
domain logic" posture exactly. Billing status is never stored (Section 11
of the brief): every call recomputes it from the live ordered/billed
quantities passed in, so there is no risk of a stored flag drifting out of
sync with the actual bills.

This module takes plain dataclasses, not `purchase_orders.schemas`
Pydantic models or `purchase` module ORM rows - the caller (currently
`purchase_orders.router`, composing app.modules.purchase.service.
PurchaseService's aggregation with app.modules.purchase_orders.service.
PurchaseOrderService's own item list) converts to `OrderedItem`/
`ItemBillingInfo` first, keeping this module decoupled from both modules'
app-layer types, the same way `domain/totals.py` takes `LineTotals` rather
than an ORM `PurchaseOrderItem`.

Quantity is the authoritative signal (Section 13): `billing_status` and
each item's `remaining_quantity` are derived purely from quantities, in
the same unit as the item itself, never from money. `billed_amount`/
`remaining_amount` are informational only - see their own docstrings.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.modules.purchase_orders.constants import PurchaseOrderBillingStatus


@dataclass(frozen=True, slots=True)
class OrderedItem:
    """The subset of a PurchaseOrderItem this module needs: its id and its
    own ordered quantity, in its own unit."""

    id: uuid.UUID
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class ItemBillingInfo:
    """One purchase order item's aggregate consumption across every valid
    (non-deleted, non-cancelled-bill) PurchaseBillItem that references it -
    computed by app.modules.purchase.repository's grouped aggregation
    query, never by loading bills into Python."""

    billed_quantity: Decimal
    billed_amount: Decimal


@dataclass(frozen=True, slots=True)
class PurchaseOrderItemBilling:
    """One item's full billing picture, ready for the API response."""

    item_id: uuid.UUID
    ordered_quantity: Decimal
    billed_quantity: Decimal
    remaining_quantity: Decimal


@dataclass(frozen=True, slots=True)
class PurchaseOrderBillingSummary:
    """The header-level billing rollup for GET /purchase-orders/{id}.

    `billed_amount`/`remaining_amount` are informational only, not
    enforced anywhere: `remaining_amount = total_amount - billed_amount`
    can stay a non-zero residual even when `billing_status ==
    FULLY_BILLED`, because `total_amount` includes header-level
    transport_charge/other_charge/round_off, which aren't tied to any
    billable item and therefore never show up in `billed_amount`. It can
    also differ from a strict "ordered minus billed" figure when a bill
    item's rate differs from the originating PO item's own rate (a real,
    legitimate scenario - prices can move between order and bill). The one
    hard-enforced constraint is always `billing_status`/per-item
    `remaining_quantity`, both quantity-based.
    """

    billed_amount: Decimal
    remaining_amount: Decimal
    billing_status: PurchaseOrderBillingStatus
    items: dict[uuid.UUID, PurchaseOrderItemBilling] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PurchaseOrderLinkedBill:
    """One Purchase Bill linked to this purchase order, for the "linked
    Purchase Bills" list on GET /purchase-orders/{id}/purchase-bills. Owned
    here, not by app.modules.purchase, for the same reason ItemBillingInfo
    is - the caller (purchase_orders.router) shapes the final API response
    from this plain value, and app.modules.purchase.service constructs
    instances of it (purchase is the downstream consumer of purchase_orders,
    never the reverse, so this module must not import anything from
    `purchase`). `status` is a plain str (PurchaseStatus's value), not the
    PurchaseStatus enum itself, to keep that one-directional dependency
    clean."""

    id: uuid.UUID
    bill_number: str | None
    bill_date: date
    status: str
    total_amount: Decimal
    balance_amount: Decimal


_ZERO_BILLING = ItemBillingInfo(billed_quantity=Decimal("0"), billed_amount=Decimal("0"))


def derive_billing_summary(
    ordered_items: list[OrderedItem],
    billed_by_item: dict[uuid.UUID, ItemBillingInfo],
    *,
    total_amount: Decimal,
) -> PurchaseOrderBillingSummary:
    """Combines each item's ordered quantity with its already-aggregated
    billed quantity/amount into the full per-item and header billing
    picture. `billed_by_item` need only contain entries for items that
    have at least one linked bill item - any item missing from it is
    treated as fully unbilled (`_ZERO_BILLING`).
    """
    item_billing: dict[uuid.UUID, PurchaseOrderItemBilling] = {}
    for ordered in ordered_items:
        billing = billed_by_item.get(ordered.id, _ZERO_BILLING)
        item_billing[ordered.id] = PurchaseOrderItemBilling(
            item_id=ordered.id,
            ordered_quantity=ordered.quantity,
            billed_quantity=billing.billed_quantity,
            remaining_quantity=ordered.quantity - billing.billed_quantity,
        )

    billed_amount = sum(
        (billing.billed_amount for billing in billed_by_item.values()), Decimal("0")
    )
    remaining_amount = total_amount - billed_amount

    if not item_billing:
        billing_status = PurchaseOrderBillingStatus.NOT_BILLED
    elif all(item.remaining_quantity <= 0 for item in item_billing.values()):
        billing_status = PurchaseOrderBillingStatus.FULLY_BILLED
    elif all(item.billed_quantity <= 0 for item in item_billing.values()):
        billing_status = PurchaseOrderBillingStatus.NOT_BILLED
    else:
        billing_status = PurchaseOrderBillingStatus.PARTIALLY_BILLED

    return PurchaseOrderBillingSummary(
        billed_amount=billed_amount,
        remaining_amount=remaining_amount,
        billing_status=billing_status,
        items=item_billing,
    )


__all__ = [
    "ItemBillingInfo",
    "OrderedItem",
    "PurchaseOrderBillingSummary",
    "PurchaseOrderItemBilling",
    "PurchaseOrderLinkedBill",
    "derive_billing_summary",
]
