from app.core.report_export.base_exporter import BaseExporter
from app.core.report_export.exceptions import UnsupportedExportFormatError


class ExporterRegistry:
    """Maps an export format string (e.g. "pdf") to the `BaseExporter`
    subclass that handles it. Phase A (TASKS.md Sprint 11 Session 5)
    registers nothing - PDF/Excel/CSV exporters are implemented and
    registered one at a time in a later phase; until then, `get()` raises
    `UnsupportedExportFormatError` for every format, which is the expected
    behavior this phase's tests exercise.

    A module-level `registry` singleton (below) is what a future phase's
    exporters will register themselves into at import time; tests should
    instantiate their own `ExporterRegistry()` rather than mutate the
    shared singleton, to stay isolated from each other.
    """

    def __init__(self) -> None:
        self._exporters: dict[str, type[BaseExporter]] = {}

    def register(self, export_format: str, exporter_cls: type[BaseExporter]) -> None:
        self._exporters[export_format] = exporter_cls

    def get(self, export_format: str) -> type[BaseExporter]:
        exporter_cls = self._exporters.get(export_format)
        if exporter_cls is None:
            raise UnsupportedExportFormatError(
                f"No exporter registered for format: {export_format!r}"
            )
        return exporter_cls

    def is_registered(self, export_format: str) -> bool:
        return export_format in self._exporters

    def registered_formats(self) -> list[str]:
        return sorted(self._exporters)


registry = ExporterRegistry()
