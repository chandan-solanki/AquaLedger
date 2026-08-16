from app.modules.delivery_challans.constants import (
    DELIVERY_CHALLAN_NUMBER_PREFIX,
    DeliveryChallanStatus,
)


def test_delivery_challan_status_values() -> None:
    assert set(DeliveryChallanStatus) == {
        DeliveryChallanStatus.DRAFT,
        DeliveryChallanStatus.DISPATCHED,
        DeliveryChallanStatus.DELIVERED,
        DeliveryChallanStatus.CANCELLED,
    }
    assert DeliveryChallanStatus.DRAFT.value == "draft"
    assert DeliveryChallanStatus.DISPATCHED.value == "dispatched"
    assert DeliveryChallanStatus.DELIVERED.value == "delivered"
    assert DeliveryChallanStatus.CANCELLED.value == "cancelled"


def test_delivery_challan_number_prefix() -> None:
    assert DELIVERY_CHALLAN_NUMBER_PREFIX == "DC"
