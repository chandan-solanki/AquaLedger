"""Unit tests for app.modules.purchase_orders.domain.billing (Sprint 12
Session 12) - pure derivation of a purchase order's billing progress from
already-aggregated Purchase Bill data. No database, no HTTP - every
OrderedItem/ItemBillingInfo below is hand-built, mirroring
test_purchase_order_document_builder.py's own style."""

import uuid
from decimal import Decimal

from app.modules.purchase_orders.constants import PurchaseOrderBillingStatus
from app.modules.purchase_orders.domain.billing import (
    ItemBillingInfo,
    OrderedItem,
    derive_billing_summary,
)

_ITEM_A = uuid.uuid4()
_ITEM_B = uuid.uuid4()


class TestDeriveBillingSummary:
    def test_no_items_is_not_billed(self) -> None:
        summary = derive_billing_summary([], {}, total_amount=Decimal("0"))
        assert summary.billing_status == PurchaseOrderBillingStatus.NOT_BILLED
        assert summary.billed_amount == Decimal("0")
        assert summary.remaining_amount == Decimal("0")
        assert summary.items == {}

    def test_items_with_no_billing_at_all_is_not_billed(self) -> None:
        items = [OrderedItem(id=_ITEM_A, quantity=Decimal("100.000"))]
        summary = derive_billing_summary(items, {}, total_amount=Decimal("23625.00"))
        assert summary.billing_status == PurchaseOrderBillingStatus.NOT_BILLED
        assert summary.billed_amount == Decimal("0")
        assert summary.remaining_amount == Decimal("23625.00")
        assert summary.items[_ITEM_A].ordered_quantity == Decimal("100.000")
        assert summary.items[_ITEM_A].billed_quantity == Decimal("0")
        assert summary.items[_ITEM_A].remaining_quantity == Decimal("100.000")

    def test_partially_billed_single_item(self) -> None:
        items = [OrderedItem(id=_ITEM_A, quantity=Decimal("100.000"))]
        billed = {
            _ITEM_A: ItemBillingInfo(
                billed_quantity=Decimal("40.000"), billed_amount=Decimal("9450.00")
            )
        }
        summary = derive_billing_summary(items, billed, total_amount=Decimal("23625.00"))
        assert summary.billing_status == PurchaseOrderBillingStatus.PARTIALLY_BILLED
        assert summary.billed_amount == Decimal("9450.00")
        assert summary.remaining_amount == Decimal("14175.00")
        assert summary.items[_ITEM_A].billed_quantity == Decimal("40.000")
        assert summary.items[_ITEM_A].remaining_quantity == Decimal("60.000")

    def test_fully_billed_single_item(self) -> None:
        items = [OrderedItem(id=_ITEM_A, quantity=Decimal("100.000"))]
        billed = {
            _ITEM_A: ItemBillingInfo(
                billed_quantity=Decimal("100.000"), billed_amount=Decimal("23625.00")
            )
        }
        summary = derive_billing_summary(items, billed, total_amount=Decimal("23625.00"))
        assert summary.billing_status == PurchaseOrderBillingStatus.FULLY_BILLED
        assert summary.remaining_amount == Decimal("0.00")
        assert summary.items[_ITEM_A].remaining_quantity == Decimal("0.000")

    def test_over_billed_item_still_reports_negative_remaining(self) -> None:
        """derive_billing_summary never clamps - PurchaseService's own
        over-billing check is what actually prevents this from happening in
        practice; this function just reports what it's given, faithfully,
        so a real bug elsewhere would surface as a visible negative number
        rather than being silently hidden here."""
        items = [OrderedItem(id=_ITEM_A, quantity=Decimal("100.000"))]
        billed = {
            _ITEM_A: ItemBillingInfo(
                billed_quantity=Decimal("120.000"), billed_amount=Decimal("28350.00")
            )
        }
        summary = derive_billing_summary(items, billed, total_amount=Decimal("23625.00"))
        assert summary.items[_ITEM_A].remaining_quantity == Decimal("-20.000")
        # Still reported FULLY_BILLED (remaining <= 0), not a fourth status.
        assert summary.billing_status == PurchaseOrderBillingStatus.FULLY_BILLED

    def test_multiple_items_do_not_cross_contaminate(self) -> None:
        items = [
            OrderedItem(id=_ITEM_A, quantity=Decimal("100.000")),
            OrderedItem(id=_ITEM_B, quantity=Decimal("50.000")),
        ]
        billed = {
            _ITEM_A: ItemBillingInfo(
                billed_quantity=Decimal("40.000"), billed_amount=Decimal("9450.00")
            ),
            _ITEM_B: ItemBillingInfo(
                billed_quantity=Decimal("50.000"), billed_amount=Decimal("11250.00")
            ),
        }
        summary = derive_billing_summary(items, billed, total_amount=Decimal("34875.00"))
        assert summary.items[_ITEM_A].remaining_quantity == Decimal("60.000")
        assert summary.items[_ITEM_B].remaining_quantity == Decimal("0.000")
        # One item fully billed, the other only partially -> order overall
        # is partially billed, not fully.
        assert summary.billing_status == PurchaseOrderBillingStatus.PARTIALLY_BILLED
        assert summary.billed_amount == Decimal("20700.00")

    def test_all_items_fully_billed_is_fully_billed_order(self) -> None:
        items = [
            OrderedItem(id=_ITEM_A, quantity=Decimal("100.000")),
            OrderedItem(id=_ITEM_B, quantity=Decimal("50.000")),
        ]
        billed = {
            _ITEM_A: ItemBillingInfo(
                billed_quantity=Decimal("100.000"), billed_amount=Decimal("23625.00")
            ),
            _ITEM_B: ItemBillingInfo(
                billed_quantity=Decimal("50.000"), billed_amount=Decimal("11250.00")
            ),
        }
        summary = derive_billing_summary(items, billed, total_amount=Decimal("34875.00"))
        assert summary.billing_status == PurchaseOrderBillingStatus.FULLY_BILLED

    def test_item_missing_from_billed_map_defaults_to_zero(self) -> None:
        """An item with no entry in billed_by_item at all (never billed
        against) must default to zero, not raise a KeyError."""
        items = [
            OrderedItem(id=_ITEM_A, quantity=Decimal("100.000")),
            OrderedItem(id=_ITEM_B, quantity=Decimal("50.000")),
        ]
        billed = {
            _ITEM_A: ItemBillingInfo(
                billed_quantity=Decimal("40.000"), billed_amount=Decimal("9450.00")
            )
        }
        summary = derive_billing_summary(items, billed, total_amount=Decimal("34875.00"))
        assert summary.items[_ITEM_B].billed_quantity == Decimal("0")
        assert summary.items[_ITEM_B].remaining_quantity == Decimal("50.000")

    def test_remaining_amount_can_stay_nonzero_when_fully_billed(self) -> None:
        """Documents the known approximation: total_amount includes
        header-level transport_charge/other_charge/round_off, which aren't
        tied to any billable item, so remaining_amount can be a non-zero
        residual even when billing_status is FULLY_BILLED - this is
        expected, not a bug (see PurchaseOrderBillingSummary's own
        docstring)."""
        items = [OrderedItem(id=_ITEM_A, quantity=Decimal("100.000"))]
        billed = {
            _ITEM_A: ItemBillingInfo(
                billed_quantity=Decimal("100.000"), billed_amount=Decimal("23625.00")
            )
        }
        # total_amount includes a 250.00 transport_charge on top of the
        # item-level subtotal+tax of 23625.00.
        summary = derive_billing_summary(items, billed, total_amount=Decimal("23875.00"))
        assert summary.billing_status == PurchaseOrderBillingStatus.FULLY_BILLED
        assert summary.remaining_amount == Decimal("250.00")
