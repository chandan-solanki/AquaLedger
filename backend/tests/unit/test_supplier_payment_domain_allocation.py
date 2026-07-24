from decimal import Decimal

import pytest

from app.modules.supplier_payments.domain.allocation import (
    AllocationExceedsPurchaseBillBalanceError,
    AllocationExceedsUnallocatedError,
    SupplierPaymentAllocationTotals,
    calculate_supplier_payment_allocation_totals,
    validate_allocation_amount,
)


class TestValidateAllocationAmount:
    def test_passes_within_both_ceilings(self) -> None:
        validate_allocation_amount(
            allocated_amount=Decimal("500.00"),
            purchase_bill_balance=Decimal("1000.00"),
            payment_unallocated=Decimal("800.00"),
        )  # must not raise

    def test_passes_when_exactly_equal_to_purchase_bill_balance(self) -> None:
        validate_allocation_amount(
            allocated_amount=Decimal("1000.00"),
            purchase_bill_balance=Decimal("1000.00"),
            payment_unallocated=Decimal("5000.00"),
        )  # must not raise - the ceiling is inclusive

    def test_passes_when_exactly_equal_to_payment_unallocated(self) -> None:
        validate_allocation_amount(
            allocated_amount=Decimal("500.00"),
            purchase_bill_balance=Decimal("5000.00"),
            payment_unallocated=Decimal("500.00"),
        )  # must not raise - the ceiling is inclusive

    def test_exceeding_purchase_bill_balance_raises(self) -> None:
        with pytest.raises(AllocationExceedsPurchaseBillBalanceError) as exc_info:
            validate_allocation_amount(
                allocated_amount=Decimal("1000.01"),
                purchase_bill_balance=Decimal("1000.00"),
                payment_unallocated=Decimal("5000.00"),
            )
        assert "exceeds the purchase bill's balance" in str(exc_info.value)

    def test_exceeding_payment_unallocated_raises(self) -> None:
        with pytest.raises(AllocationExceedsUnallocatedError) as exc_info:
            validate_allocation_amount(
                allocated_amount=Decimal("500.01"),
                purchase_bill_balance=Decimal("5000.00"),
                payment_unallocated=Decimal("500.00"),
            )
        assert "exceeds the payment's unallocated amount" in str(exc_info.value)

    def test_purchase_bill_balance_is_checked_before_payment_unallocated(self) -> None:
        """Both ceilings could independently reject the same amount - the
        purchase bill balance check runs first, mirroring
        payments.domain.allocation.validate_allocation_amount's own
        ordering."""
        with pytest.raises(AllocationExceedsPurchaseBillBalanceError):
            validate_allocation_amount(
                allocated_amount=Decimal("1000.00"),
                purchase_bill_balance=Decimal("100.00"),
                payment_unallocated=Decimal("100.00"),
            )


class TestCalculateSupplierPaymentAllocationTotals:
    def test_returns_allocated_and_unallocated_from_scratch(self) -> None:
        totals = calculate_supplier_payment_allocation_totals(
            payment_amount=Decimal("1000.00"), total_allocated=Decimal("600.00")
        )
        assert totals == SupplierPaymentAllocationTotals(
            allocated_amount=Decimal("600.00"), unallocated_amount=Decimal("400.00")
        )

    def test_zero_allocated_leaves_everything_unallocated(self) -> None:
        totals = calculate_supplier_payment_allocation_totals(
            payment_amount=Decimal("1000.00"), total_allocated=Decimal("0")
        )
        assert totals.allocated_amount == Decimal("0")
        assert totals.unallocated_amount == Decimal("1000.00")

    def test_fully_allocated_leaves_nothing_unallocated(self) -> None:
        totals = calculate_supplier_payment_allocation_totals(
            payment_amount=Decimal("1000.00"), total_allocated=Decimal("1000.00")
        )
        assert totals.allocated_amount == Decimal("1000.00")
        assert totals.unallocated_amount == Decimal("0")

    def test_is_a_pure_recomputation_with_no_extra_clamping(self) -> None:
        """Not reachable through the real create/update paths (both are
        ceiling-validated before this runs), but this function performs no
        clamping of its own - it is a pure recomputation, not a second
        validation pass."""
        totals = calculate_supplier_payment_allocation_totals(
            payment_amount=Decimal("1000.00"), total_allocated=Decimal("1200.00")
        )
        assert totals.allocated_amount == Decimal("1200.00")
        assert totals.unallocated_amount == Decimal("-200.00")
