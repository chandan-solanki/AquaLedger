from app.core.errors import ValidationError


class UnsupportedReportError(ValidationError):
    """Raised when ExportService.export() is asked to export a
    `report_type` that isn't one of the known ReportType values - e.g. a
    typo, or a report this engine hasn't been told about yet."""

    code = "UNSUPPORTED_REPORT"


class UnsupportedExportFormatError(ValidationError):
    """Raised when ExportService.export() is asked for an `export_format`
    the registry has no exporter class registered for. Phase A
    (TASKS.md Sprint 11 Session 5) registers zero exporters on purpose -
    PDF/Excel/CSV are added one at a time in a later phase - so today
    every format, known or not, raises this."""

    code = "UNSUPPORTED_EXPORT_FORMAT"
