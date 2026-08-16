from app.core.document_engine.document_models import DocumentData, RenderedDocument
from app.core.document_engine.document_types import DocumentType
from app.core.document_engine.exceptions import UnsupportedDocumentTypeError
from app.core.document_engine.registry import DocumentRegistry
from app.core.document_engine.registry import registry as default_registry


class DocumentService:
    """Orchestrates a document render end-to-end without ever touching
    the database or a business service's own calculations: it validates
    the requested document type and hands an already-built `DocumentData`
    (assembled by a business service, e.g. invoicing/payments/purchasing
    in a later session) to the matching renderer. This session wires no
    API endpoint and registers no renderers, so `generate()` always
    raises `DocumentRendererNotRegisteredError` for a known-but-unbuilt
    type - that is the expected, tested behavior until a later session
    registers the first renderer.
    """

    def __init__(self, document_registry: DocumentRegistry | None = None) -> None:
        self._registry = document_registry or default_registry

    def generate(self, document_type: str, data: DocumentData) -> RenderedDocument:
        resolved_type = self._validate_document_type(document_type)
        renderer_cls = self._registry.get(resolved_type)
        return renderer_cls().run(data)

    @staticmethod
    def _validate_document_type(document_type: str) -> DocumentType:
        try:
            return DocumentType(document_type)
        except ValueError as exc:
            raise UnsupportedDocumentTypeError(f"Unknown document type: {document_type!r}") from exc
