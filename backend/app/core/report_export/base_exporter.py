from abc import ABC, abstractmethod
from typing import ClassVar

from app.core.report_export.export_models import ReportExportData


class BaseExporter(ABC):
    """Every exporter (PDF/Excel/CSV - app.core.report_export.exporters,
    TASKS.md Sprint 11 Session 5 Phase B) inherits this and implements
    only `export()` - `validate()`/`prepare()` already have sensible
    no-op defaults a subclass can override if it needs one (e.g. a PDF
    exporter enforcing a page-count limit, an Excel exporter normalizing
    column widths). No subclass may query the database - `data` arrives
    fully assembled by a report module's own `build_export_data()`.

    `content_type`/`file_extension` are HTTP-response metadata only (used
    by the export API route to build the download response) - they carry
    no rendering logic, so declaring them here isn't a redesign of the
    validate/prepare/export/run pipeline Phase A shipped.
    """

    content_type: ClassVar[str] = "application/octet-stream"
    file_extension: ClassVar[str] = "bin"

    def validate(self, data: ReportExportData) -> None:
        """Exporter-specific validation beyond what ReportExportData's own
        pydantic validators already enforce. No-op by default."""
        return None

    def prepare(self, data: ReportExportData) -> ReportExportData:
        """Exporter-specific pre-processing. Returns `data` unchanged by
        default."""
        return data

    @abstractmethod
    def export(self, data: ReportExportData) -> bytes:
        """Produce the exported file's raw bytes."""
        raise NotImplementedError

    def run(self, data: ReportExportData) -> bytes:
        """The fixed `validate -> prepare -> export` pipeline every caller
        (ExportService) uses instead of calling `export()` directly."""
        self.validate(data)
        prepared = self.prepare(data)
        return self.export(prepared)
