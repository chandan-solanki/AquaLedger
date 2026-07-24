from decimal import Decimal

import pytest

from app.modules.purchase.constants import PurchaseStatus
from app.modules.supplier_payments.domain.reconciliation import (
    NegativeOutstandingError,
    PaidAmountExceedsTotalError,
    PurchaseBillNotReconcilableError,
    PurchaseBillPaymentTotals,
    ReconciliationError,
    calculate_purchase_bill_payment,
    calculate_supplier_outstanding,
    determine_purchase_bill_status,
)


class TestDeterminePurchaseBillStatus:
    def test_balance_equal_to_total_is_posted(self) -> None:
        assert (
            determine_purchase_bill_status(
                total_amount=Decimal("1000.00"), balance_amount=Decimal("1000.00")
            )
            == PurchaseStatus.POSTED
        )

    def test_zero_balance_is_paid(self) -> None:
        assert (
            determine_purchase_bill_status(
                total_amount=Decimal("1000.00"), balance_amount=Decimal("0.00")
            )
            == PurchaseStatus.PAID
        )

    def test_partial_balance_is_partially_paid(self) -> None:
        assert (
            determine_purchase_bill_status(
                total_amount=Decimal("1000.00"), balance_amount=Decimal("400.00")
            )
            == PurchaseStatus.PARTIALLY_PAID
        )

    def test_zero_total_and_zero_balance_is_posted_not_paid(self) -> None:
        """ "Nothing owed" (balance == total) takes precedence over "nothing
        outstanding" (balance == 0) when both are true at once - a purchase
        bill with no items has total_amount == balance_amount == 0."""
        assert (
            determine_purchase_bill_status(
                total_amount=Decimal("0.00"), balance_amount=Decimal("0.00")
            )
            == PurchaseStatus.POSTED
        )


class TestCalculatePurchaseBillPayment:
    def test_zero_allocated_leaves_the_bill_posted(self) -> None:
        totals = calculate_purchase_bill_payment(
            total_amount=Decimal("1000.00"),
            total_allocated=Decimal("0"),
            current_status=PurchaseStatus.POSTED,
        )
        assert totals == PurchaseBillPaymentTotals(
            paid_amount=Decimal("0.00"),
            balance_amount=Decimal("1000.00"),
            status=PurchaseStatus.POSTED,
        )

    def test_partial_allocation_gives_partially_paid(self) -> None:
        totals = calculate_purchase_bill_payment(
            total_amount=Decimal("1000.00"),
            total_allocated=Decimal("400.00"),
            current_status=PurchaseStatus.POSTED,
        )
        assert totals.paid_amount == Decimal("400.00")
        assert totals.balance_amount == Decimal("600.00")
        assert totals.status == PurchaseStatus.PARTIALLY_PAID

    def test_full_allocation_gives_paid(self) -> None:
        totals = calculate_purchase_bill_payment(
            total_amount=Decimal("1000.00"),
            total_allocated=Decimal("1000.00"),
            current_status=PurchaseStatus.PARTIALLY_PAID,
        )
        assert totals.paid_amount == Decimal("1000.00")
        assert totals.balance_amount == Decimal("0.00")
        assert totals.status == PurchaseStatus.PAID

    def test_reducing_allocation_moves_a_paid_bill_back_to_partially_paid(self) -> None:
        """current_status may legitimately be PAID here - editing/removing
        an allocation that had fully paid a purchase bill must be able to
        move it back down
        (supplier_payments/service.py's _ALLOCATION_EDITABLE_PURCHASE_BILL_STATUSES)."""
        totals = calculate_purchase_bill_payment(
            total_amount=Decimal("1000.00"),
            total_allocated=Decimal("400.00"),
            current_status=PurchaseStatus.PAID,
        )
        assert totals.status == PurchaseStatus.PARTIALLY_PAID

    def test_draft_bill_raises_not_reconcilable(self) -> None:
        with pytest.raises(PurchaseBillNotReconcilableError):
            calculate_purchase_bill_payment(
                total_amount=Decimal("1000.00"),
                total_allocated=Decimal("0"),
                current_status=PurchaseStatus.DRAFT,
            )

    def test_cancelled_bill_raises_not_reconcilable(self) -> None:
        with pytest.raises(PurchaseBillNotReconcilableError):
            calculate_purchase_bill_payment(
                total_amount=Decimal("1000.00"),
                total_allocated=Decimal("0"),
                current_status=PurchaseStatus.CANCELLED,
            )

    def test_status_check_runs_before_any_arithmetic(self) -> None:
        """A wildly invalid total_allocated on a non-reconcilable bill still
        reports PurchaseBillNotReconcilableError, not an amount error - proof
        the status guard is checked first."""
        with pytest.raises(PurchaseBillNotReconcilableError):
            calculate_purchase_bill_payment(
                total_amount=Decimal("1000.00"),
                total_allocated=Decimal("999999.00"),
                current_status=PurchaseStatus.DRAFT,
            )

    def test_paid_amount_exceeding_total_raises(self) -> None:
        """Not reachable through the API - SupplierPaymentService's
        allocation ceilings already keep total_allocated <= total_amount -
        but the domain function itself must still refuse to produce
        paid_amount > total_amount."""
        with pytest.raises(PaidAmountExceedsTotalError):
            calculate_purchase_bill_payment(
                total_amount=Decimal("1000.00"),
                total_allocated=Decimal("1000.01"),
                current_status=PurchaseStatus.POSTED,
            )

    def test_negative_total_allocated_raises(self) -> None:
        with pytest.raises(ReconciliationError):
            calculate_purchase_bill_payment(
                total_amount=Decimal("1000.00"),
                total_allocated=Decimal("-1.00"),
                current_status=PurchaseStatus.POSTED,
            )

    def test_rounds_paid_and_balance_half_up(self) -> None:
        totals = calculate_purchase_bill_payment(
            total_amount=Decimal("1000.005"),
            total_allocated=Decimal("400.005"),
            current_status=PurchaseStatus.POSTED,
        )
        assert totals.paid_amount == Decimal("400.01")
        assert totals.balance_amount == Decimal("600.00")


class TestCalculateSupplierOutstanding:
    def test_rounds_and_returns_the_sum(self) -> None:
        assert calculate_supplier_outstanding(total_open_balance=Decimal("1234.505")) == Decimal(
            "1234.51"
        )

    def test_zero_balance_is_zero(self) -> None:
        assert calculate_supplier_outstanding(total_open_balance=Decimal("0")) == Decimal("0.00")

    def test_negative_total_raises(self) -> None:
        """Not reachable in practice - it is a SUM of balance_amount, which
        PurchaseService's own reconciliation guard never lets go negative -
        but SupplierService must not trust an input it did not itself
        validate."""
        with pytest.raises(NegativeOutstandingError):
            calculate_supplier_outstanding(total_open_balance=Decimal("-0.01"))
