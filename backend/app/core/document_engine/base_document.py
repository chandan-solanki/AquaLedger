from abc import ABC, abstractmethod
from typing import ClassVar

from app.core.document_engine.document_models import DocumentData, RenderedDocument


class BaseDocumentRenderer(ABC):
    """Every document renderer (invoice PDF, purchase bill PDF, receipt,
    ... - built in later sessions) inherits this and implements only
    `render()` - `validate()`/`prepare()` already have sensible no-op
    defaults a subclass can override if it needs one. No subclass may
    query the database - `data` arrives fully assembled by a business
    service's own `DocumentData`.

    `content_type`/`file_extension` are HTTP-response/storage metadata
    only, mirroring `BaseExporter`'s own class-level declaration.
    """

    content_type: ClassVar[str] = "application/octet-stream"
    file_extension: ClassVar[str] = "bin"

    def validate(self, data: DocumentData) -> None:
        """Renderer-specific validation beyond what DocumentData's own
        pydantic validators already enforce. No-op by default."""
        return None

    def prepare(self, data: DocumentData) -> DocumentData:
        """Renderer-specific pre-processing. Returns `data` unchanged by
        default."""
        return data

    @abstractmethod
    def render(self, data: DocumentData) -> bytes:
        """Produce the rendered document's raw bytes."""
        raise NotImplementedError

    def run(self, data: DocumentData) -> RenderedDocument:
        """The fixed `validate -> prepare -> render` pipeline every
        caller (DocumentService) uses instead of calling `render()`
        directly."""
        self.validate(data)
        prepared = self.prepare(data)
        content = self.render(prepared)
        return RenderedDocument(
            content=content,
            content_type=self.content_type,
            file_extension=self.file_extension,
        )
