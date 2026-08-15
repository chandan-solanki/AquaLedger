from datetime import date, datetime
from decimal import Decimal

from app.core.report_export.export_models import ColumnFormat
from app.core.report_export.formatting import format_value


class TestFormatValue:
    def test_none_renders_as_dash(self) -> None:
        assert format_value(None, ColumnFormat.CURRENCY) == "-"
        assert format_value(None, ColumnFormat.TEXT) == "-"

    def test_currency_adds_thousands_separator_and_two_decimals(self) -> None:
        assert format_value(Decimal("348250"), ColumnFormat.CURRENCY) == "348,250.00"
        assert format_value(Decimal("74.5"), ColumnFormat.CURRENCY) == "74.50"

    def test_percent_appends_a_percent_sign(self) -> None:
        assert format_value(Decimal("74.09"), ColumnFormat.PERCENT) == "74.09%"

    def test_date_renders_as_iso_format(self) -> None:
        assert format_value(date(2026, 7, 1), ColumnFormat.DATE) == "2026-07-01"

    def test_datetime_renders_with_time(self) -> None:
        assert (
            format_value(datetime(2026, 7, 1, 14, 30), ColumnFormat.DATETIME) == "2026-07-01 14:30"
        )

    def test_number_adds_thousands_separator_and_preserves_decimal_places(self) -> None:
        assert format_value(Decimal("1250.500"), ColumnFormat.NUMBER) == "1,250.500"
        assert format_value(6, ColumnFormat.NUMBER) == "6"

    def test_text_renders_via_str(self) -> None:
        assert format_value("Pomfret", ColumnFormat.TEXT) == "Pomfret"
        assert format_value("kg", ColumnFormat.TEXT) == "kg"
