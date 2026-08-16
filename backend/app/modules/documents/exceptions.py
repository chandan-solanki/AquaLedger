from app.core.errors import NotFoundError


class DocumentRecordNotFoundError(NotFoundError):
    """Raised when a document_id doesn't reference an existing
    DocumentRecord for the caller's tenant - also covers a record
    belonging to another tenant, which is indistinguishable from "does
    not exist" by design (mirrors every other module's *NotFoundError)."""

    code = "DOCUMENT_RECORD_NOT_FOUND"


class DocumentFileMissingError(NotFoundError):
    """Raised when a DocumentRecord's metadata exists but the underlying
    file is no longer present at its storage_key (StorageService.load
    raises DocumentNotFoundError). A distinct code from
    DocumentRecordNotFoundError: the history entry is real, only the
    physical file backing it is gone - a data-integrity anomaly rather
    than "never existed", so the client should be able to tell the two
    apart."""

    code = "DOCUMENT_FILE_MISSING"
