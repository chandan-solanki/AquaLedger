from app.modules.purchase.constants import PURCHASE_NUMBER_PREFIX, PurchaseStatus


def test_purchase_status_values() -> None:
    assert set(PurchaseStatus) == {
        PurchaseStatus.DRAFT,
        PurchaseStatus.POSTED,
        PurchaseStatus.CANCELLED,
    }
    assert PurchaseStatus.DRAFT.value == "draft"
    assert PurchaseStatus.POSTED.value == "posted"
    assert PurchaseStatus.CANCELLED.value == "cancelled"


def test_purchase_number_prefix() -> None:
    assert PURCHASE_NUMBER_PREFIX == "PUR"
