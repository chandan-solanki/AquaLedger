from app.core.errors import ConflictError, NotFoundError, ValidationError


class UnsupportedDocumentTypeError(ValidationError):
    """Raised when DocumentService.generate() is asked to render a
    `document_type` that isn't one of the known DocumentType values."""

    code = "UNSUPPORTED_DOCUMENT_TYPE"


class DocumentRendererNotRegisteredError(ValidationError):
    """Raised when DocumentRegistry.get() is asked for a document type
    that is a valid DocumentType but has no renderer registered for it
    yet - this session registers none on purpose (invoice/purchase-bill/
    receipt renderers are built in later sessions)."""

    code = "DOCUMENT_RENDERER_NOT_REGISTERED"


class DuplicateDocumentRendererError(ConflictError):
    """Raised when DocumentRegistry.register() is called twice for the
    same document type without `override=True`. Unlike the format-keyed
    ExporterRegistry (which is reasonably re-registered as PDF/Excel/CSV
    variants evolve), each DocumentType is meant to have exactly one
    canonical renderer - a silent second registration is far more likely
    to be a bug than an intentional swap, so this fails loudly by
    default."""

    code = "DUPLICATE_DOCUMENT_RENDERER"


class InvalidStorageKeyError(ValidationError):
    """Raised when a storage key is empty, absolute, contains illegal
    characters, or attempts to traverse outside the configured storage
    root (e.g. `../../secret.txt`)."""

    code = "INVALID_STORAGE_KEY"


class DocumentNotFoundError(NotFoundError):
    """Raised when StorageService.load() is asked for a storage key that
    does not exist."""

    code = "DOCUMENT_NOT_FOUND"
