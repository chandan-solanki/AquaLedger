"""Verifies that importing app.core.report_export.exporters (the package,
not any one exporter module) registers CSV/Excel into the shared
ExporterRegistry singleton, and PDF too whenever WeasyPrint's native
libraries are available (TASKS.md Sprint 11 Session 5 Phase B). Doesn't
assume WeasyPrint availability either way - both outcomes are asserted
against whatever `exporters.PDFExporter` actually resolved to.
"""

from app.core.report_export import exporters
from app.core.report_export.exporters.csv_exporter import CSVExporter
from app.core.report_export.exporters.excel_exporter import ExcelExporter
from app.core.report_export.registry import registry


class TestExportersRegistration:
    def test_csv_is_registered_to_the_csv_exporter_class(self) -> None:
        assert registry.get("csv") is CSVExporter

    def test_excel_is_registered_to_the_excel_exporter_class(self) -> None:
        assert registry.get("excel") is ExcelExporter

    def test_pdf_registration_matches_whether_weasyprint_is_importable(self) -> None:
        if exporters.PDFExporter is None:
            assert not registry.is_registered("pdf")
        else:
            assert registry.get("pdf") is exporters.PDFExporter

    def test_csv_and_excel_are_always_registered_regardless_of_pdf(self) -> None:
        """A WeasyPrint import failure must never take down CSV/Excel
        registration too (see exporters/__init__.py's own docstring)."""
        assert registry.is_registered("csv")
        assert registry.is_registered("excel")
