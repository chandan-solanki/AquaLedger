import pytest

from app.core.document_engine.base_document import BaseDocumentRenderer
from app.core.document_engine.document_models import DocumentData
from app.core.document_engine.document_types import DocumentType
from app.core.document_engine.exceptions import (
    DocumentRendererNotRegisteredError,
    DuplicateDocumentRendererError,
)
from app.core.document_engine.registry import DocumentRegistry


class _FakeRenderer(BaseDocumentRenderer):
    def render(self, data: DocumentData) -> bytes:
        return b"fake-bytes"


class _OtherRenderer(BaseDocumentRenderer):
    def render(self, data: DocumentData) -> bytes:
        return b"other-bytes"


class TestDocumentRegistry:
    def test_fresh_registry_has_no_registered_types(self) -> None:
        fresh = DocumentRegistry()
        assert fresh.registered_types() == []
        assert fresh.is_registered(DocumentType.INVOICE) is False

    def test_register_then_get_returns_the_same_class(self) -> None:
        fresh = DocumentRegistry()
        fresh.register(DocumentType.INVOICE, _FakeRenderer)
        assert fresh.get(DocumentType.INVOICE) is _FakeRenderer
        assert fresh.is_registered(DocumentType.INVOICE) is True

    def test_register_then_registered_types_lists_it(self) -> None:
        fresh = DocumentRegistry()
        fresh.register(DocumentType.PURCHASE_BILL, _FakeRenderer)
        fresh.register(DocumentType.INVOICE, _FakeRenderer)
        assert fresh.registered_types() == [DocumentType.INVOICE, DocumentType.PURCHASE_BILL]

    def test_get_unregistered_type_raises_not_registered(self) -> None:
        fresh = DocumentRegistry()
        with pytest.raises(DocumentRendererNotRegisteredError):
            fresh.get(DocumentType.INVOICE)

    def test_registering_the_same_type_twice_raises_duplicate(self) -> None:
        fresh = DocumentRegistry()
        fresh.register(DocumentType.INVOICE, _FakeRenderer)
        with pytest.raises(DuplicateDocumentRendererError):
            fresh.register(DocumentType.INVOICE, _OtherRenderer)

    def test_duplicate_registration_does_not_replace_the_original(self) -> None:
        fresh = DocumentRegistry()
        fresh.register(DocumentType.INVOICE, _FakeRenderer)
        with pytest.raises(DuplicateDocumentRendererError):
            fresh.register(DocumentType.INVOICE, _OtherRenderer)
        assert fresh.get(DocumentType.INVOICE) is _FakeRenderer

    def test_override_true_allows_replacing_an_existing_registration(self) -> None:
        fresh = DocumentRegistry()
        fresh.register(DocumentType.INVOICE, _FakeRenderer)
        fresh.register(DocumentType.INVOICE, _OtherRenderer, override=True)
        assert fresh.get(DocumentType.INVOICE) is _OtherRenderer
