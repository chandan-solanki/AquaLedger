"""Unit tests for app.core.report_export.filenames (TASKS.md Sprint 11
Session 5 Phase D - Export Polish)."""

from datetime import UTC, date, datetime

from app.core.report_export.export_models import ReportColumn, ReportExportData, ReportRow
from app.core.report_export.filenames import build_export_filename

_GENERATED_AT = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


def _make_data(title: str, subtitle: str | None = None) -> ReportExportData:
    return ReportExportData(
        title=title,
        subtitle=subtitle,
        columns=[ReportColumn(title="X", key="x")],
        rows=[ReportRow(data={"x": 1})],
        summary=[],
        generated_at=_GENERATED_AT,
        generated_by="admin@fisherp.test",
        tenant_name="Konkan Traders",
    )


class TestBuildExportFilename:
    def test_aggregate_report_uses_todays_date(self) -> None:
        filename = build_export_filename(_make_data("Sales Report"), extension="pdf")
        assert filename == f"Sales_Report_{date.today().isoformat()}.pdf"

    def test_entity_scoped_report_uses_the_partys_name_not_the_date(self) -> None:
        filename = build_export_filename(
            _make_data("Customer Ledger", "ABC Sea Food (CO-0001)"), extension="xlsx"
        )
        assert filename == "Customer_Ledger_ABC_Sea_Food.xlsx"

    def test_supplier_statement_example_from_the_spec(self) -> None:
        filename = build_export_filename(
            _make_data("Supplier Statement", "ABC Marine (SUP-0002)"), extension="pdf"
        )
        assert filename == "Supplier_Statement_ABC_Marine.pdf"

    def test_multi_word_title_becomes_underscored(self) -> None:
        filename = build_export_filename(_make_data("Fish Sales Analytics"), extension="csv")
        assert filename.startswith("Fish_Sales_Analytics_")

    def test_illegal_filename_characters_are_stripped(self) -> None:
        filename = build_export_filename(
            _make_data("Customer Ledger", "O'Brien / Sons? (CO-0003)"), extension="pdf"
        )
        assert not any(char in filename for char in '<>:"/\\|?*')
        assert filename == "Customer_Ledger_O'Brien_Sons.pdf"

    def test_no_illegal_characters_ever_in_any_output(self) -> None:
        for title, subtitle in [
            ("Boat Profitability", None),
            ("Trip Profitability", None),
            ("Customer Statement", 'Say "Hi" <Ltd> (CO-9)'),
        ]:
            filename = build_export_filename(_make_data(title, subtitle), extension="xlsx")
            assert not any(char in filename for char in '<>:"/\\|?*')

    def test_repeated_whitespace_collapses_to_a_single_underscore(self) -> None:
        filename = build_export_filename(
            _make_data("Customer Ledger", "Big   Fish   Traders (CO-0009)"), extension="pdf"
        )
        assert filename == "Customer_Ledger_Big_Fish_Traders.pdf"

    def test_extension_is_appended_verbatim(self) -> None:
        assert build_export_filename(_make_data("Aging Report"), extension="csv").endswith(".csv")
        assert build_export_filename(_make_data("Aging Report"), extension="xlsx").endswith(".xlsx")
        assert build_export_filename(_make_data("Aging Report"), extension="pdf").endswith(".pdf")
