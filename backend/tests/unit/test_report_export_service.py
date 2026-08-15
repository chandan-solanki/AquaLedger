from datetime import UTC, datetime

import pytest

from app.core.report_export.base_exporter import BaseExporter
from app.core.report_export.exceptions import UnsupportedExportFormatError, UnsupportedReportError
from app.core.report_export.export_models import ReportColumn, ReportExportData, ReportRow
from app.core.report_export.export_service import ExportService
from app.core.report_export.registry import ExporterRegistry

_DATA = ReportExportData(
    title="Fish Sales Analytics",
    columns=[ReportColumn(title="Fish", key="fish_name")],
    rows=[ReportRow(data={"fish_name": "Pomfret"})],
    summary=[],
    generated_at=datetime(2026, 7, 30, tzinfo=UTC),
    generated_by="admin@fisherp.test",
    tenant_name="Konkan Traders",
)


class _FakeExporter(BaseExporter):
    def export(self, data: ReportExportData) -> bytes:
        return b"fake-bytes:" + data.title.encode()


class TestExportService:
    def test_export_with_a_registered_exporter_returns_its_bytes(self) -> None:
        fresh_registry = ExporterRegistry()
        fresh_registry.register("pdf", _FakeExporter)
        service = ExportService(fresh_registry)

        result = service.export(_DATA, report_type="fish_sales", export_format="pdf")

        assert result == b"fake-bytes:Fish Sales Analytics"

    def test_export_with_unregistered_format_raises_unsupported_export_format(self) -> None:
        empty_registry = ExporterRegistry()
        service = ExportService(empty_registry)

        with pytest.raises(UnsupportedExportFormatError):
            service.export(_DATA, report_type="fish_sales", export_format="pdf")

    def test_export_with_unknown_format_string_raises_unsupported_export_format(self) -> None:
        empty_registry = ExporterRegistry()
        service = ExportService(empty_registry)

        with pytest.raises(UnsupportedExportFormatError):
            service.export(_DATA, report_type="fish_sales", export_format="xyz")

    def test_export_with_unsupported_report_raises_unsupported_report(self) -> None:
        fresh_registry = ExporterRegistry()
        fresh_registry.register("pdf", _FakeExporter)
        service = ExportService(fresh_registry)

        with pytest.raises(UnsupportedReportError):
            service.export(_DATA, report_type="not_a_real_report", export_format="pdf")

    def test_report_is_validated_before_format_is_looked_up(self) -> None:
        """An invalid report_type must fail as UnsupportedReportError even
        when export_format is *also* invalid - report validation runs
        first."""
        empty_registry = ExporterRegistry()
        service = ExportService(empty_registry)

        with pytest.raises(UnsupportedReportError):
            service.export(_DATA, report_type="not_a_real_report", export_format="also_not_real")

    def test_default_constructor_uses_the_shared_singleton_registry(self) -> None:
        """The default-constructed service must delegate to the shared
        module-level registry, not a private empty one - a format no
        phase ever registers still raises regardless of what real
        exporters (csv/excel/pdf, added in Phase B) happen to be
        registered there."""
        service = ExportService()

        with pytest.raises(UnsupportedExportFormatError):
            service.export(_DATA, report_type="fish_sales", export_format="xyz_never_registered")

    def test_all_nine_known_report_types_pass_report_validation(self) -> None:
        fresh_registry = ExporterRegistry()
        fresh_registry.register("pdf", _FakeExporter)
        service = ExportService(fresh_registry)

        known_reports = [
            "customer_ledger",
            "supplier_ledger",
            "sales_report",
            "purchase_report",
            "outstanding_report",
            "aging_report",
            "trip_profitability",
            "boat_profitability",
            "fish_sales",
        ]
        for report_type in known_reports:
            assert service.export(_DATA, report_type=report_type, export_format="pdf") == (
                b"fake-bytes:Fish Sales Analytics"
            )
