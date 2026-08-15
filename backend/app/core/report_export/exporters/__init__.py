"""Registers the concrete PDF/Excel/CSV exporters into the shared
`ExporterRegistry` singleton (TASKS.md Sprint 11 Session 5 Phase B).
Importing this package is the one place that side-effect happens - the
export API route does `import app.core.report_export.exporters  # noqa`
once, at module load time, to populate the registry before any request
can reach it.

WeasyPrint depends on native GTK libraries (Pango, GDK-Pixbuf, libgobject)
that may not be present on every machine this code runs on (e.g. a bare
Windows dev box without the GTK runtime installed) - if importing it
fails, PDF export is simply not registered (requesting format=pdf then
raises the normal UnsupportedExportFormatError) rather than taking down
Excel/CSV registration too.
"""

import structlog

from app.core.report_export.base_exporter import BaseExporter
from app.core.report_export.exporters.csv_exporter import CSVExporter
from app.core.report_export.exporters.excel_exporter import ExcelExporter
from app.core.report_export.registry import registry

logger = structlog.get_logger("app.report_export")

registry.register("csv", CSVExporter)
registry.register("excel", ExcelExporter)

PDFExporter: type[BaseExporter] | None

try:
    from app.core.report_export.exporters.pdf_exporter import PDFExporter as _PDFExporter
except (ImportError, OSError):
    logger.warning(
        "pdf_exporter_unavailable",
        reason="WeasyPrint failed to import - its native GTK libraries are likely missing "
        "on this machine. PDF export will raise UnsupportedExportFormatError until this "
        "is resolved; Excel and CSV export are unaffected.",
    )
    PDFExporter = None
else:
    PDFExporter = _PDFExporter
    registry.register("pdf", PDFExporter)

__all__ = ["CSVExporter", "ExcelExporter", "PDFExporter"]
