import datetime as dt

import pytest

from app.modules.payments.domain.numbering import fiscal_year_for, format_payment_number


class TestFiscalYearFor:
    @pytest.mark.parametrize(
        ("payment_date", "expected"),
        [
            (dt.date(2026, 4, 1), "2026-27"),
            (dt.date(2026, 7, 23), "2026-27"),
            (dt.date(2027, 3, 31), "2026-27"),
            (dt.date(2026, 3, 31), "2025-26"),
            (dt.date(2026, 1, 1), "2025-26"),
        ],
    )
    def test_indian_gst_fiscal_year_boundaries(self, payment_date: dt.date, expected: str) -> None:
        assert fiscal_year_for(payment_date) == expected

    def test_century_rollover_stays_two_digits(self) -> None:
        assert fiscal_year_for(dt.date(2099, 4, 1)) == "2099-00"


class TestFormatPaymentNumber:
    def test_pads_sequence_to_five_digits(self) -> None:
        assert format_payment_number("PAY", "2026-27", 1) == "PAY/2026-27/00001"

    def test_does_not_truncate_a_sequence_wider_than_the_padding(self) -> None:
        assert format_payment_number("PAY", "2026-27", 123456) == "PAY/2026-27/123456"

    def test_uses_the_given_prefix_verbatim(self) -> None:
        assert format_payment_number("XYZ", "2025-26", 42) == "XYZ/2025-26/00042"
