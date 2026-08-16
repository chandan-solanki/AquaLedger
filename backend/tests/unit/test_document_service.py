from datetime import UTC, date, datetime

import pytest

from app.core.document_engine.base_document import BaseDocumentRenderer
from app.core.document_engine.document_models import DocumentData
from app.core.document_engine.document_service import DocumentService
from app.core.document_engine.document_types import DocumentType
from app.core.document_engine.exceptions import (
    DocumentRendererNotRegisteredError,
    UnsupportedDocumentTypeError,
)
from app.core.document_engine.registry import DocumentRegistry
from app.core.document_engine.registry import registry as _default_registry

_DATA = DocumentData(
    document_type=DocumentType.INVOICE,
    document_number="INV-000001",
    document_date=date(2026, 8, 15),
    title="Tax Invoice",
    tenant_name="Konkan Traders",
    generated_at=datetime(2026, 8, 15, tzinfo=UTC),
    generated_by="admin@fisherp.test",
)


class _FakeRenderer(BaseDocumentRenderer):
    content_type = "application/pdf"
    file_extension = "pdf"

    def render(self, data: DocumentData) -> bytes:
        return b"fake-bytes:" + data.document_number.encode()


class TestDocumentService:
    def test_generate_with_a_registered_renderer_returns_rendered_document(self) -> None:
        fresh_registry = DocumentRegistry()
        fresh_registry.register(DocumentType.INVOICE, _FakeRenderer)
        service = DocumentService(fresh_registry)

        result = service.generate("invoice", _DATA)

        assert result.content == b"fake-bytes:INV-000001"
        assert result.content_type == "application/pdf"
        assert result.file_extension == "pdf"

    def test_generate_with_unregistered_type_raises_not_registered(self) -> None:
        empty_registry = DocumentRegistry()
        service = DocumentService(empty_registry)

        with pytest.raises(DocumentRendererNotRegisteredError):
            service.generate("invoice", _DATA)

    def test_generate_with_unsupported_document_type_raises_unsupported(self) -> None:
        empty_registry = DocumentRegistry()
        service = DocumentService(empty_registry)

        with pytest.raises(UnsupportedDocumentTypeError):
            service.generate("not_a_real_document", _DATA)

    def test_document_type_is_validated_before_renderer_is_looked_up(self) -> None:
        fresh_registry = DocumentRegistry()
        fresh_registry.register(DocumentType.INVOICE, _FakeRenderer)
        service = DocumentService(fresh_registry)

        with pytest.raises(UnsupportedDocumentTypeError):
            service.generate("not_a_real_document", _DATA)

    def test_default_constructor_uses_the_shared_singleton_registry(self) -> None:
        """An identity check, not a raise-for-an-unregistered-type probe -
        a business module (e.g. invoices' InvoiceDocumentRenderer, Sprint
        12 Session 2) permanently registers into this same shared
        singleton at import time, so asserting that any *particular*
        type stays unregistered would break every time a later session
        ships its own renderer (all six DocumentType values are
        eventually registered over the sprint)."""
        service = DocumentService()

        assert service._registry is _default_registry

    def test_all_six_known_document_types_pass_type_validation(self) -> None:
        fresh_registry = DocumentRegistry()
        service = DocumentService(fresh_registry)

        known_types = [
            "invoice",
            "purchase_bill",
            "customer_payment_receipt",
            "supplier_payment_receipt",
            "purchase_order",
            "delivery_challan",
        ]
        for document_type in known_types:
            with pytest.raises(DocumentRendererNotRegisteredError):
                service.generate(document_type, _DATA)
