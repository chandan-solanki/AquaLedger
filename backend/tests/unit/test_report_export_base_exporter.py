from datetime import UTC, datetime

import pytest

from app.core.report_export.base_exporter import BaseExporter
from app.core.report_export.export_models import ReportColumn, ReportExportData, ReportRow

_DATA = ReportExportData(
    title="Sales Report",
    columns=[ReportColumn(title="Invoice Number", key="invoice_number")],
    rows=[ReportRow(data={"invoice_number": "INV-1"})],
    summary=[],
    generated_at=datetime(2026, 7, 30, tzinfo=UTC),
    generated_by="admin@fisherp.test",
    tenant_name="Konkan Traders",
)


class _RecordingExporter(BaseExporter):
    """Tracks call order and lets a test observe exactly what each hook
    received, without needing a real PDF/Excel/CSV implementation
    (Phase A ships none - see TASKS.md Sprint 11 Session 5)."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def validate(self, data: ReportExportData) -> None:
        self.calls.append("validate")

    def prepare(self, data: ReportExportData) -> ReportExportData:
        self.calls.append("prepare")
        return data.model_copy(update={"footer": "prepared"})

    def export(self, data: ReportExportData) -> bytes:
        self.calls.append("export")
        assert data.footer == "prepared"
        return b"exported-bytes"


class _MinimalExporter(BaseExporter):
    """Only implements the abstract method - exercises validate()/
    prepare()'s default no-op behavior."""

    def export(self, data: ReportExportData) -> bytes:
        return b"minimal-bytes"


class TestBaseExporter:
    def test_cannot_be_instantiated_directly(self) -> None:
        with pytest.raises(TypeError):
            BaseExporter()  # type: ignore[abstract]

    def test_default_validate_is_a_noop(self) -> None:
        exporter = _MinimalExporter()
        assert exporter.validate(_DATA) is None

    def test_default_prepare_returns_data_unchanged(self) -> None:
        exporter = _MinimalExporter()
        assert exporter.prepare(_DATA) is _DATA

    def test_run_calls_validate_prepare_export_in_order_and_passes_prepared_data_through(
        self,
    ) -> None:
        exporter = _RecordingExporter()
        result = exporter.run(_DATA)
        assert exporter.calls == ["validate", "prepare", "export"]
        assert result == b"exported-bytes"

    def test_run_on_minimal_exporter_returns_export_bytes(self) -> None:
        exporter = _MinimalExporter()
        assert exporter.run(_DATA) == b"minimal-bytes"
