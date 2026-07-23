from decimal import Decimal

import pytest

from app.modules.invoices.constants import InvoiceStatus
from app.modules.payments.domain.reconciliation import (
    InvoiceNotReconcilableError,
    InvoicePaymentTotals,
    NegativeOutstandingError,
    PaidAmountExceedsTotalError,
    ReconciliationError,
    calculate_company_outstanding,
    calculate_invoice_payment,
    determine_invoice_status,
)


class TestDetermineInvoiceStatus:
    def test_balance_equal_to_total_is_issued(self) -> None:
        assert (
            determine_invoice_status(
                total_amount=Decimal("1000.00"), balance_amount=Decimal("1000.00")
            )
            == InvoiceStatus.ISSUED
        )

    def test_zero_balance_is_paid(self) -> None:
        assert (
            determine_invoice_status(
                total_amount=Decimal("1000.00"), balance_amount=Decimal("0.00")
            )
            == InvoiceStatus.PAID
        )

    def test_partial_balance_is_partially_paid(self) -> None:
        assert (
            determine_invoice_status(
                total_amount=Decimal("1000.00"), balance_amount=Decimal("400.00")
            )
            == InvoiceStatus.PARTIALLY_PAID
        )

    def test_zero_total_and_zero_balance_is_issued_not_paid(self) -> None:
        """ "Nothing owed" (balance == total) takes precedence over "nothing
        outstanding" (balance == 0) when both are true at once - an invoice
        with no items has total_amount == balance_amount == 0."""
        assert (
            determine_invoice_status(total_amount=Decimal("0.00"), balance_amount=Decimal("0.00"))
            == InvoiceStatus.ISSUED
        )


class TestCalculateInvoicePayment:
    def test_zero_allocated_leaves_the_invoice_issued(self) -> None:
        totals = calculate_invoice_payment(
            total_amount=Decimal("1000.00"),
            total_allocated=Decimal("0"),
            current_status=InvoiceStatus.ISSUED,
        )
        assert totals == InvoicePaymentTotals(
            paid_amount=Decimal("0.00"),
            balance_amount=Decimal("1000.00"),
            status=InvoiceStatus.ISSUED,
        )

    def test_partial_allocation_gives_partially_paid(self) -> None:
        totals = calculate_invoice_payment(
            total_amount=Decimal("1000.00"),
            total_allocated=Decimal("400.00"),
            current_status=InvoiceStatus.ISSUED,
        )
        assert totals.paid_amount == Decimal("400.00")
        assert totals.balance_amount == Decimal("600.00")
        assert totals.status == InvoiceStatus.PARTIALLY_PAID

    def test_full_allocation_gives_paid(self) -> None:
        totals = calculate_invoice_payment(
            total_amount=Decimal("1000.00"),
            total_allocated=Decimal("1000.00"),
            current_status=InvoiceStatus.PARTIALLY_PAID,
        )
        assert totals.paid_amount == Decimal("1000.00")
        assert totals.balance_amount == Decimal("0.00")
        assert totals.status == InvoiceStatus.PAID

    def test_reducing_allocation_moves_a_paid_invoice_back_to_partially_paid(self) -> None:
        """current_status may legitimately be PAID here - editing/removing
        an allocation that had fully paid an invoice must be able to move
        it back down (payments/service.py's _ALLOCATION_EDITABLE_INVOICE_STATUSES)."""
        totals = calculate_invoice_payment(
            total_amount=Decimal("1000.00"),
            total_allocated=Decimal("400.00"),
            current_status=InvoiceStatus.PAID,
        )
        assert totals.status == InvoiceStatus.PARTIALLY_PAID

    def test_draft_invoice_raises_not_reconcilable(self) -> None:
        with pytest.raises(InvoiceNotReconcilableError):
            calculate_invoice_payment(
                total_amount=Decimal("1000.00"),
                total_allocated=Decimal("0"),
                current_status=InvoiceStatus.DRAFT,
            )

    def test_cancelled_invoice_raises_not_reconcilable(self) -> None:
        with pytest.raises(InvoiceNotReconcilableError):
            calculate_invoice_payment(
                total_amount=Decimal("1000.00"),
                total_allocated=Decimal("0"),
                current_status=InvoiceStatus.CANCELLED,
            )

    def test_status_check_runs_before_any_arithmetic(self) -> None:
        """A wildly invalid total_allocated on a non-reconcilable invoice
        still reports InvoiceNotReconcilableError, not an amount error -
        proof the status guard is checked first."""
        with pytest.raises(InvoiceNotReconcilableError):
            calculate_invoice_payment(
                total_amount=Decimal("1000.00"),
                total_allocated=Decimal("999999.00"),
                current_status=InvoiceStatus.DRAFT,
            )

    def test_paid_amount_exceeding_total_raises(self) -> None:
        """Not reachable through the API - PaymentService's allocation
        ceilings already keep total_allocated <= total_amount - but the
        domain function itself must still refuse to produce paid_amount >
        total_amount."""
        with pytest.raises(PaidAmountExceedsTotalError):
            calculate_invoice_payment(
                total_amount=Decimal("1000.00"),
                total_allocated=Decimal("1000.01"),
                current_status=InvoiceStatus.ISSUED,
            )

    def test_negative_total_allocated_raises(self) -> None:
        with pytest.raises(ReconciliationError):
            calculate_invoice_payment(
                total_amount=Decimal("1000.00"),
                total_allocated=Decimal("-1.00"),
                current_status=InvoiceStatus.ISSUED,
            )

    def test_rounds_paid_and_balance_half_up(self) -> None:
        totals = calculate_invoice_payment(
            total_amount=Decimal("1000.005"),
            total_allocated=Decimal("400.005"),
            current_status=InvoiceStatus.ISSUED,
        )
        assert totals.paid_amount == Decimal("400.01")
        assert totals.balance_amount == Decimal("600.00")


class TestCalculateCompanyOutstanding:
    def test_rounds_and_returns_the_sum(self) -> None:
        assert calculate_company_outstanding(total_open_balance=Decimal("1234.505")) == Decimal(
            "1234.51"
        )

    def test_zero_balance_is_zero(self) -> None:
        assert calculate_company_outstanding(total_open_balance=Decimal("0")) == Decimal("0.00")

    def test_negative_total_raises(self) -> None:
        """Not reachable in practice - it is a SUM of balance_amount, which
        InvoiceService's own reconciliation guard never lets go negative -
        but CompanyService must not trust an input it did not itself
        validate."""
        with pytest.raises(NegativeOutstandingError):
            calculate_company_outstanding(total_open_balance=Decimal("-0.01"))
