from datetime import UTC, date, datetime

import pytest

from app.core.document_engine.base_document import BaseDocumentRenderer
from app.core.document_engine.document_models import DocumentData

_DATA = DocumentData(
    document_type="invoice",
    document_number="INV-000001",
    document_date=date(2026, 8, 15),
    title="Tax Invoice",
    tenant_name="Konkan Traders",
    generated_at=datetime(2026, 8, 15, tzinfo=UTC),
    generated_by="admin@fisherp.test",
)


class _RecordingRenderer(BaseDocumentRenderer):
    content_type = "application/pdf"
    file_extension = "pdf"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def validate(self, data: DocumentData) -> None:
        self.calls.append("validate")

    def prepare(self, data: DocumentData) -> DocumentData:
        self.calls.append("prepare")
        return data.model_copy(update={"notes": "prepared"})

    def render(self, data: DocumentData) -> bytes:
        self.calls.append("render")
        assert data.notes == "prepared"
        return b"rendered-bytes"


class _MinimalRenderer(BaseDocumentRenderer):
    def render(self, data: DocumentData) -> bytes:
        return b"minimal-bytes"


class TestBaseDocumentRenderer:
    def test_cannot_be_instantiated_directly(self) -> None:
        with pytest.raises(TypeError):
            BaseDocumentRenderer()  # type: ignore[abstract]

    def test_default_validate_is_a_noop(self) -> None:
        renderer = _MinimalRenderer()
        assert renderer.validate(_DATA) is None

    def test_default_prepare_returns_data_unchanged(self) -> None:
        renderer = _MinimalRenderer()
        assert renderer.prepare(_DATA) is _DATA

    def test_default_content_type_and_extension(self) -> None:
        renderer = _MinimalRenderer()
        result = renderer.run(_DATA)
        assert result.content_type == "application/octet-stream"
        assert result.file_extension == "bin"

    def test_run_calls_validate_prepare_render_in_order_and_passes_prepared_data_through(
        self,
    ) -> None:
        renderer = _RecordingRenderer()
        result = renderer.run(_DATA)
        assert renderer.calls == ["validate", "prepare", "render"]
        assert result.content == b"rendered-bytes"
        assert result.content_type == "application/pdf"
        assert result.file_extension == "pdf"

    def test_run_on_minimal_renderer_returns_rendered_document(self) -> None:
        renderer = _MinimalRenderer()
        result = renderer.run(_DATA)
        assert result.content == b"minimal-bytes"
