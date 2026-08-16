from decimal import Decimal

from app.modules.delivery_challans.domain.quantity import remaining_quantity


def test_no_delivery_yet_leaves_the_full_quantity_remaining() -> None:
    assert remaining_quantity(Decimal("100.000"), Decimal("0")) == Decimal("100.000")


def test_partial_delivery_reduces_remaining() -> None:
    assert remaining_quantity(Decimal("100.000"), Decimal("40.000")) == Decimal("60.000")


def test_fully_delivered_leaves_zero_remaining() -> None:
    assert remaining_quantity(Decimal("100.000"), Decimal("100.000")) == Decimal("0.000")


def test_over_delivered_reports_negative_remaining() -> None:
    """The write-time guard should always prevent this in practice, but the
    pure function itself must not assume non-negativity - mirrors
    purchase_orders.domain.billing's own over-billed item behavior."""
    assert remaining_quantity(Decimal("100.000"), Decimal("110.000")) == Decimal("-10.000")
