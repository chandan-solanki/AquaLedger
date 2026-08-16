from app.core.document_engine.base_document import BaseDocumentRenderer
from app.core.document_engine.document_types import DocumentType
from app.core.document_engine.exceptions import (
    DocumentRendererNotRegisteredError,
    DuplicateDocumentRendererError,
)


class DocumentRegistry:
    """Maps a `DocumentType` to the `BaseDocumentRenderer` subclass that
    renders it - the same architectural idea as
    `app.core.report_export.registry.ExporterRegistry`, keyed by the
    closed `DocumentType` enum rather than a free-form format string.

    This session (Sprint 12 Session 1) registers nothing - invoice/
    purchase-bill/receipt renderers are implemented and registered one at
    a time in later sessions; until then, `get()` raises
    `DocumentRendererNotRegisteredError` for every type.

    A module-level `registry` singleton (below) is what later sessions'
    renderers will register themselves into at import time; tests should
    instantiate their own `DocumentRegistry()` rather than mutate the
    shared singleton, to stay isolated from each other.
    """

    def __init__(self) -> None:
        self._renderers: dict[DocumentType, type[BaseDocumentRenderer]] = {}

    def register(
        self,
        document_type: DocumentType,
        renderer_cls: type[BaseDocumentRenderer],
        *,
        override: bool = False,
    ) -> None:
        if not override and document_type in self._renderers:
            raise DuplicateDocumentRendererError(
                f"A renderer is already registered for document type: {document_type!r}"
            )
        self._renderers[document_type] = renderer_cls

    def get(self, document_type: DocumentType) -> type[BaseDocumentRenderer]:
        renderer_cls = self._renderers.get(document_type)
        if renderer_cls is None:
            raise DocumentRendererNotRegisteredError(
                f"No renderer registered for document type: {document_type!r}"
            )
        return renderer_cls

    def is_registered(self, document_type: DocumentType) -> bool:
        return document_type in self._renderers

    def registered_types(self) -> list[DocumentType]:
        return sorted(self._renderers, key=lambda document_type: document_type.value)


registry = DocumentRegistry()
