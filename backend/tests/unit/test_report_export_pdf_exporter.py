"""PDFExporter tests (TASKS.md Sprint 11 Session 5 Phase B). WeasyPrint
depends on native GTK libraries (Pango, GDK-Pixbuf, libgobject) that are
not installed on every machine this suite runs on - if they're missing,
the whole module skips cleanly rather than failing, since that reflects
an environment gap, not a code defect. Where WeasyPrint IS available
(e.g. a properly provisioned Linux CI/production image), every test here
runs for real and produces an actual PDF.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

try:
    import weasyprint  # noqa: F401
except (ImportError, OSError) as exc:
    # WeasyPrint's native GTK libraries (Pango, GDK-Pixbuf, libgobject) can
    # fail to load as either an ImportError or, on some platforms (e.g.
    # this cffi dlopen path on Windows), a plain OSError - pytest.importorskip
    # only catches the former, so this module skips itself explicitly for
    # both.
    pytest.skip(f"WeasyPrint unavailable: {exc}", allow_module_level=True)

from app.core.report_export.export_models import (  # noqa: E402
    ColumnAlignment,
    ColumnFormat,
    ReportColumn,
    ReportExportData,
    ReportFilterDisplay,
    ReportRow,
    ReportSummary,
)
from app.core.report_export.exporters.pdf_exporter import PDFExporter  # noqa: E402

_GENERATED_AT = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


def _make_data(**overrides: object) -> ReportExportData:
    defaults: dict[str, object] = {
        "title": "Fish Sales Analytics",
        "subtitle": "All Boats",
        "filters": [ReportFilterDisplay(label="From Date", value="2026-07-01")],
        "columns": [
            ReportColumn(title="Fish", key="fish_name"),
            ReportColumn(
                title="Revenue",
                key="revenue",
                alignment=ColumnAlignment.RIGHT,
                format=ColumnFormat.CURRENCY,
            ),
            ReportColumn(title="Last Sold", key="last_sold_date", format=ColumnFormat.DATE),
        ],
        "rows": [
            ReportRow(
                data={
                    "fish_name": "Pomfret",
                    "revenue": Decimal("1000.00"),
                    "last_sold_date": date(2026, 7, 1),
                }
            ),
        ],
        "summary": [ReportSummary(label="Total Revenue", value=Decimal("1000.00"))],
        "generated_at": _GENERATED_AT,
        "generated_by": "admin@fisherp.test",
        "tenant_name": "Konkan Traders",
    }
    defaults.update(overrides)
    return ReportExportData(**defaults)


class TestPDFExporterHTMLRendering:
    """Exercises the Jinja2 rendering step in isolation from WeasyPrint's
    own PDF byte-generation - this catches template errors even faster
    than a full run() would."""

    def test_renders_title_subtitle_and_tenant(self) -> None:
        html = PDFExporter._render_html(_make_data())
        assert "Fish Sales Analytics" in html
        assert "All Boats" in html
        assert "Konkan Traders" in html

    def test_renders_filters_and_summary_sections(self) -> None:
        html = PDFExporter._render_html(_make_data())
        assert "From Date" in html
        assert "2026-07-01" in html
        assert "Total Revenue" in html

    def test_renders_formatted_currency_and_date_values(self) -> None:
        html = PDFExporter._render_html(_make_data())
        assert "1,000.00" in html
        assert "2026-07-01" in html

    def test_empty_state_message_when_no_rows(self) -> None:
        html = PDFExporter._render_html(_make_data(rows=[]))
        assert "No data for the selected filters." in html

    def test_narrow_report_is_portrait(self) -> None:
        html = PDFExporter._render_html(_make_data())
        assert 'class="portrait"' in html

    def test_wide_report_is_landscape(self) -> None:
        columns = [ReportColumn(title=f"Col {i}", key=f"col_{i}") for i in range(9)]
        rows = [ReportRow(data={f"col_{i}": "x" for i in range(9)})]
        html = PDFExporter._render_html(_make_data(columns=columns, rows=rows))
        assert 'class="landscape"' in html

    def test_no_javascript_anywhere_in_the_rendered_document(self) -> None:
        html = PDFExporter._render_html(_make_data())
        assert "<script" not in html.lower()


class TestPDFExporterEndToEnd:
    def test_run_produces_pdf_bytes(self) -> None:
        output = PDFExporter().run(_make_data())
        assert output.startswith(b"%PDF")

    def test_content_type_and_extension(self) -> None:
        exporter = PDFExporter()
        assert exporter.file_extension == "pdf"
        assert exporter.content_type == "application/pdf"

    def test_zero_rows_still_produces_a_valid_pdf(self) -> None:
        output = PDFExporter().run(_make_data(rows=[]))
        assert output.startswith(b"%PDF")
