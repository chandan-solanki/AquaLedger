from decimal import Decimal

import pytest

from app.modules.payments.domain.allocation import (
    AllocationExceedsInvoiceBalanceError,
    AllocationExceedsUnallocatedError,
    AllocationValidationError,
    PaymentAllocationTotals,
    calculate_payment_allocation_totals,
    validate_allocation_amount,
)


class TestValidateAllocationAmount:
    def test_passes_when_within_both_ceilings(self) -> None:
        validate_allocation_amount(
            allocated_amount=Decimal("500.00"),
            invoice_balance=Decimal("1000.00"),
            payment_unallocated=Decimal("800.00"),
        )  # must not raise

    def test_passes_when_exactly_equal_to_invoice_balance(self) -> None:
        validate_allocation_amount(
            allocated_amount=Decimal("1000.00"),
            invoice_balance=Decimal("1000.00"),
            payment_unallocated=Decimal("2000.00"),
        )  # must not raise

    def test_passes_when_exactly_equal_to_payment_unallocated(self) -> None:
        validate_allocation_amount(
            allocated_amount=Decimal("500.00"),
            invoice_balance=Decimal("2000.00"),
            payment_unallocated=Decimal("500.00"),
        )  # must not raise

    def test_raises_when_exceeding_invoice_balance(self) -> None:
        with pytest.raises(AllocationExceedsInvoiceBalanceError):
            validate_allocation_amount(
                allocated_amount=Decimal("1000.01"),
                invoice_balance=Decimal("1000.00"),
                payment_unallocated=Decimal("5000.00"),
            )

    def test_raises_when_exceeding_payment_unallocated(self) -> None:
        with pytest.raises(AllocationExceedsUnallocatedError):
            validate_allocation_amount(
                allocated_amount=Decimal("500.01"),
                invoice_balance=Decimal("5000.00"),
                payment_unallocated=Decimal("500.00"),
            )

    def test_invoice_balance_is_checked_before_payment_unallocated(self) -> None:
        """When both ceilings would be violated, the invoice balance check
        fires first (see validate_allocation_amount's implementation order)
        - callers that only catch one exception type should still get a
        deterministic result."""
        with pytest.raises(AllocationExceedsInvoiceBalanceError):
            validate_allocation_amount(
                allocated_amount=Decimal("100.00"),
                invoice_balance=Decimal("50.00"),
                payment_unallocated=Decimal("10.00"),
            )

    def test_both_are_allocation_validation_errors(self) -> None:
        assert issubclass(AllocationExceedsInvoiceBalanceError, AllocationValidationError)
        assert issubclass(AllocationExceedsUnallocatedError, AllocationValidationError)
        assert issubclass(AllocationValidationError, ValueError)


class TestCalculatePaymentAllocationTotals:
    def test_returns_total_allocated_and_the_remainder(self) -> None:
        totals = calculate_payment_allocation_totals(
            payment_amount=Decimal("1000.00"), total_allocated=Decimal("600.00")
        )
        assert totals == PaymentAllocationTotals(
            allocated_amount=Decimal("600.00"), unallocated_amount=Decimal("400.00")
        )

    def test_zero_allocated_leaves_everything_unallocated(self) -> None:
        totals = calculate_payment_allocation_totals(
            payment_amount=Decimal("1000.00"), total_allocated=Decimal("0")
        )
        assert totals.allocated_amount == Decimal("0")
        assert totals.unallocated_amount == Decimal("1000.00")

    def test_fully_allocated_leaves_nothing_unallocated(self) -> None:
        totals = calculate_payment_allocation_totals(
            payment_amount=Decimal("1000.00"), total_allocated=Decimal("1000.00")
        )
        assert totals.unallocated_amount == Decimal("0.00")
