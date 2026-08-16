from app.modules.purchase_orders.constants import PURCHASE_ORDER_NUMBER_PREFIX, PurchaseOrderStatus


def test_purchase_order_status_values() -> None:
    assert set(PurchaseOrderStatus) == {
        PurchaseOrderStatus.DRAFT,
        PurchaseOrderStatus.CONFIRMED,
        PurchaseOrderStatus.FULFILLED,
        PurchaseOrderStatus.CANCELLED,
    }
    assert PurchaseOrderStatus.DRAFT.value == "draft"
    assert PurchaseOrderStatus.CONFIRMED.value == "confirmed"
    assert PurchaseOrderStatus.FULFILLED.value == "fulfilled"
    assert PurchaseOrderStatus.CANCELLED.value == "cancelled"


def test_purchase_order_number_prefix() -> None:
    assert PURCHASE_ORDER_NUMBER_PREFIX == "PO"
