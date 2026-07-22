from decimal import Decimal

import pytest

from app.modules.invoices.domain.totals import (
    MAX_MONEY,
    InvoiceTotals,
    LineTotals,
    NegativeTotalError,
    TotalOverflowError,
    calculate_invoice_totals,
    calculate_line_totals,
)


class TestCalculateLineTotals:
    def test_basic_line_with_discount_and_tax(self) -> None:
        totals = calculate_line_totals(
            quantity=Decimal("50.000"),
            rate=Decimal("450.0000"),
            discount_percent=Decimal("0"),
            tax_rate=Decimal("5.00"),
        )
        assert totals == LineTotals(
            discount_amount=Decimal("0.00"),
            taxable_amount=Decimal("22500.00"),
            tax_amount=Decimal("1125.00"),
            line_total=Decimal("23625.00"),
        )

    def test_line_with_discount_percent(self) -> None:
        totals = calculate_line_totals(
            quantity=Decimal("10"),
            rate=Decimal("100"),
            discount_percent=Decimal("10"),
            tax_rate=Decimal("5"),
        )
        # gross = 1000, discount = 100, taxable = 900, tax = 45, line_total = 945
        assert totals.discount_amount == Decimal("100.00")
        assert totals.taxable_amount == Decimal("900.00")
        assert totals.tax_amount == Decimal("45.00")
        assert totals.line_total == Decimal("945.00")

    def test_zero_quantity_and_rate_gives_all_zeros(self) -> None:
        totals = calculate_line_totals(
            quantity=Decimal("0"),
            rate=Decimal("0"),
            discount_percent=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        assert totals == LineTotals(
            discount_amount=Decimal("0.00"),
            taxable_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            line_total=Decimal("0.00"),
        )

    def test_zero_tax_rate_produces_zero_tax(self) -> None:
        totals = calculate_line_totals(
            quantity=Decimal("5"),
            rate=Decimal("20"),
            discount_percent=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        assert totals.tax_amount == Decimal("0.00")
        assert totals.line_total == totals.taxable_amount

    def test_hundred_percent_discount_zeroes_the_line(self) -> None:
        totals = calculate_line_totals(
            quantity=Decimal("5"),
            rate=Decimal("20"),
            discount_percent=Decimal("100"),
            tax_rate=Decimal("5"),
        )
        assert totals.discount_amount == Decimal("100.00")
        assert totals.taxable_amount == Decimal("0.00")
        assert totals.tax_amount == Decimal("0.00")
        assert totals.line_total == Decimal("0.00")

    def test_half_up_rounds_a_boundary_value_up(self) -> None:
        # gross = 2 * 0.625 = 1.25; discount = 1.25 * 50 / 100 = 0.625 exactly
        # -> HALF_UP rounds 0.625 to 0.63, not 0.62 (banker's rounding would).
        totals = calculate_line_totals(
            quantity=Decimal("2"),
            rate=Decimal("0.625"),
            discount_percent=Decimal("50"),
            tax_rate=Decimal("0"),
        )
        assert totals.discount_amount == Decimal("0.63")
        assert totals.taxable_amount == Decimal("0.62")

    def test_decimal_arithmetic_avoids_float_error(self) -> None:
        """0.1 * 0.2 == 0.020000000000000004 in float but exactly 0.02 in
        Decimal - proof this module never touches float."""
        totals = calculate_line_totals(
            quantity=Decimal("0.1"),
            rate=Decimal("0.2"),
            discount_percent=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        assert totals.taxable_amount == Decimal("0.02")

    def test_preserves_full_precision_of_quantity_and_rate(self) -> None:
        # 999.999 * 0.0001 = 0.0999999 -> taxable rounds HALF_UP to 0.10
        totals = calculate_line_totals(
            quantity=Decimal("999.999"),
            rate=Decimal("0.0001"),
            discount_percent=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        assert totals.taxable_amount == Decimal("0.10")

    def test_results_are_two_decimal_places(self) -> None:
        totals = calculate_line_totals(
            quantity=Decimal("3"),
            rate=Decimal("33.3333"),
            discount_percent=Decimal("7.5"),
            tax_rate=Decimal("12.5"),
        )
        for value in (
            totals.discount_amount,
            totals.taxable_amount,
            totals.tax_amount,
            totals.line_total,
        ):
            assert value == value.quantize(Decimal("0.01"))

    def test_negative_rate_raises_negative_total_error(self) -> None:
        """Not reachable through the API (rate>=0 is schema-enforced), but
        the domain function itself must still refuse to produce a negative
        taxable_amount if ever called with an out-of-range value."""
        with pytest.raises(NegativeTotalError):
            calculate_line_totals(
                quantity=Decimal("10"),
                rate=Decimal("-5"),
                discount_percent=Decimal("0"),
                tax_rate=Decimal("0"),
            )

    def test_discount_percent_over_100_raises_negative_total_error(self) -> None:
        """Not reachable through the API (discount_percent<=100 is
        schema-enforced) - a discount larger than the gross amount would
        make taxable_amount negative."""
        with pytest.raises(NegativeTotalError):
            calculate_line_totals(
                quantity=Decimal("10"),
                rate=Decimal("100"),
                discount_percent=Decimal("150"),
                tax_rate=Decimal("0"),
            )

    def test_extreme_quantity_and_rate_raises_overflow_error(self) -> None:
        """quantity (up to 12,3) and rate (up to 12,4) are independently
        bounded by the request schema, but their product is not - this is
        the realistic way TotalOverflowError gets triggered."""
        with pytest.raises(TotalOverflowError):
            calculate_line_totals(
                quantity=Decimal("999999999.999"),
                rate=Decimal("99999999.9999"),
                discount_percent=Decimal("0"),
                tax_rate=Decimal("0"),
            )

    def test_value_just_at_max_money_does_not_raise(self) -> None:
        totals = calculate_line_totals(
            quantity=Decimal("1"),
            rate=MAX_MONEY,
            discount_percent=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        assert totals.taxable_amount == MAX_MONEY

    def test_value_just_over_max_money_raises_overflow_error(self) -> None:
        with pytest.raises(TotalOverflowError):
            calculate_line_totals(
                quantity=Decimal("1"),
                rate=MAX_MONEY + Decimal("0.01"),
                discount_percent=Decimal("0"),
                tax_rate=Decimal("0"),
            )


def _line(
    *,
    discount_amount: str = "0.00",
    taxable_amount: str = "0.00",
    tax_amount: str = "0.00",
    line_total: str = "0.00",
) -> LineTotals:
    return LineTotals(
        discount_amount=Decimal(discount_amount),
        taxable_amount=Decimal(taxable_amount),
        tax_amount=Decimal(tax_amount),
        line_total=Decimal(line_total),
    )


class TestCalculateInvoiceTotals:
    def test_no_items_gives_zero_aggregates(self) -> None:
        totals = calculate_invoice_totals(
            [],
            transport_charge=Decimal("0"),
            other_charge=Decimal("0"),
            round_off=Decimal("0"),
            paid_amount=Decimal("0"),
        )
        assert totals == InvoiceTotals(
            subtotal=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            taxable_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            transport_charge=Decimal("0"),
            other_charge=Decimal("0"),
            round_off=Decimal("0"),
            total_amount=Decimal("0.00"),
            paid_amount=Decimal("0"),
            balance_amount=Decimal("0.00"),
        )

    def test_no_items_but_nonzero_charges_still_totals_correctly(self) -> None:
        """A brand-new invoice (no items yet) with a transport_charge must
        still show it in total_amount/balance_amount."""
        totals = calculate_invoice_totals(
            [],
            transport_charge=Decimal("250.00"),
            other_charge=Decimal("0"),
            round_off=Decimal("0"),
            paid_amount=Decimal("0"),
        )
        assert totals.total_amount == Decimal("250.00")
        assert totals.balance_amount == Decimal("250.00")

    def test_sums_multiple_lines(self) -> None:
        lines = [
            _line(
                discount_amount="0.00",
                taxable_amount="22500.00",
                tax_amount="1125.00",
                line_total="23625.00",
            ),
            _line(
                discount_amount="50.00",
                taxable_amount="450.00",
                tax_amount="22.50",
                line_total="472.50",
            ),
        ]
        totals = calculate_invoice_totals(
            lines,
            transport_charge=Decimal("100.00"),
            other_charge=Decimal("25.00"),
            round_off=Decimal("0"),
            paid_amount=Decimal("0"),
        )
        assert totals.subtotal == Decimal("24097.50")
        assert totals.discount_amount == Decimal("50.00")
        assert totals.taxable_amount == Decimal("22950.00")
        assert totals.tax_amount == Decimal("1147.50")
        assert totals.total_amount == Decimal("24222.50")
        assert totals.balance_amount == Decimal("24222.50")

    def test_total_amount_includes_transport_and_other_charge(self) -> None:
        totals = calculate_invoice_totals(
            [_line(line_total="1000.00")],
            transport_charge=Decimal("50.00"),
            other_charge=Decimal("10.00"),
            round_off=Decimal("0"),
            paid_amount=Decimal("0"),
        )
        assert totals.total_amount == Decimal("1060.00")

    def test_balance_amount_subtracts_paid_amount(self) -> None:
        totals = calculate_invoice_totals(
            [_line(line_total="1000.00")],
            transport_charge=Decimal("0"),
            other_charge=Decimal("0"),
            round_off=Decimal("0"),
            paid_amount=Decimal("400.00"),
        )
        assert totals.total_amount == Decimal("1000.00")
        assert totals.balance_amount == Decimal("600.00")

    def test_paid_amount_exceeding_total_raises_negative_total_error(self) -> None:
        """Not reachable today (paid_amount is always 0 - no Payment module
        yet), but the domain function itself must still refuse to produce a
        negative balance_amount."""
        with pytest.raises(NegativeTotalError):
            calculate_invoice_totals(
                [_line(line_total="100.00")],
                transport_charge=Decimal("0"),
                other_charge=Decimal("0"),
                round_off=Decimal("0"),
                paid_amount=Decimal("200.00"),
            )

    def test_extreme_transport_charge_raises_overflow_error(self) -> None:
        with pytest.raises(TotalOverflowError):
            calculate_invoice_totals(
                [],
                transport_charge=MAX_MONEY,
                other_charge=MAX_MONEY,
                round_off=Decimal("0"),
                paid_amount=Decimal("0"),
            )

    def test_sum_is_rounded_half_up_to_two_decimal_places(self) -> None:
        """Even if a line_total somehow carried more precision than 2
        decimal places, the invoice-level aggregate must still come out
        HALF_UP-rounded to money precision."""
        totals = calculate_invoice_totals(
            [_line(line_total="333.335")],
            transport_charge=Decimal("0"),
            other_charge=Decimal("0"),
            round_off=Decimal("0"),
            paid_amount=Decimal("0"),
        )
        assert totals.subtotal == Decimal("333.34")
