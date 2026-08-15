from app.core.report_export.exceptions import UnsupportedReportError
from app.core.report_export.export_models import ReportExportData, ReportType
from app.core.report_export.registry import ExporterRegistry
from app.core.report_export.registry import registry as default_registry


class ExportService:
    """Orchestrates a report export end-to-end (TASKS.md Sprint 11 Session
    5 Phase A) without ever touching the database or a report's own
    calculations: it validates the requested report and format, looks up
    the matching exporter, and hands it an already-built
    `ReportExportData` (assembled by a report module's own
    `build_export_data()`-style method, see
    app/modules/reports/service.py). This phase wires no API endpoint and
    registers no exporters, so `export()` always raises
    `UnsupportedExportFormatError` today - that is the expected, tested
    behavior until a later phase registers the first exporter.
    """

    def __init__(self, exporter_registry: ExporterRegistry | None = None) -> None:
        self._registry = exporter_registry or default_registry

    def export(self, data: ReportExportData, *, report_type: str, export_format: str) -> bytes:
        self._validate_report(report_type)
        exporter_cls = self._registry.get(export_format)
        return exporter_cls().run(data)

    @staticmethod
    def _validate_report(report_type: str) -> ReportType:
        try:
            return ReportType(report_type)
        except ValueError as exc:
            raise UnsupportedReportError(f"Unknown report type: {report_type!r}") from exc
