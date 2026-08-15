import pytest

from app.core.report_export.base_exporter import BaseExporter
from app.core.report_export.exceptions import UnsupportedExportFormatError
from app.core.report_export.export_models import ReportExportData
from app.core.report_export.registry import ExporterRegistry


class _FakeExporter(BaseExporter):
    def export(self, data: ReportExportData) -> bytes:
        return b"fake-bytes"


class TestExporterRegistry:
    def test_fresh_registry_has_no_registered_formats(self) -> None:
        fresh = ExporterRegistry()
        assert fresh.registered_formats() == []
        assert fresh.is_registered("pdf") is False

    def test_register_then_get_returns_the_same_class(self) -> None:
        fresh = ExporterRegistry()
        fresh.register("pdf", _FakeExporter)
        assert fresh.get("pdf") is _FakeExporter
        assert fresh.is_registered("pdf") is True

    def test_register_then_registered_formats_lists_it(self) -> None:
        fresh = ExporterRegistry()
        fresh.register("csv", _FakeExporter)
        fresh.register("excel", _FakeExporter)
        assert fresh.registered_formats() == ["csv", "excel"]

    def test_get_unknown_format_raises_unsupported_export_format(self) -> None:
        fresh = ExporterRegistry()
        with pytest.raises(UnsupportedExportFormatError):
            fresh.get("xyz")

    def test_registering_a_new_class_for_the_same_format_overwrites_it(self) -> None:
        fresh = ExporterRegistry()

        class _OtherExporter(BaseExporter):
            def export(self, data: ReportExportData) -> bytes:
                return b"other-bytes"

        fresh.register("pdf", _FakeExporter)
        fresh.register("pdf", _OtherExporter)
        assert fresh.get("pdf") is _OtherExporter
