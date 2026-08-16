"""Storage abstraction for generated business documents (Sprint 12
Session 1). `StorageService` is a plain interface any backend can
implement; `LocalStorageService` is the only implementation this session
ships (a filesystem root, configurable via `Settings.document_storage_root`).
S3/R2, Azure Blob and MinIO backends are future work - `StorageService`'s
shape is kept deliberately provider-agnostic so adding one later is a new
subclass, not a redesign.

Security: every storage key is validated before it ever touches the
filesystem. Keys must be relative, POSIX-style, and free of `..`
segments or control characters - a key such as `../../secret.txt` is
rejected outright, and `_resolve_within_root` re-checks the fully
resolved path still lives under the configured root as defense in
depth. `build_document_storage_key()` is how a caller should construct
a key in the first place: `{tenant_id}/documents/{document_type}/{filename}`,
so one tenant's documents can never collide with another's.
"""

import re
from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.core.config import get_settings
from app.core.document_engine.document_types import DocumentType
from app.core.document_engine.exceptions import DocumentNotFoundError, InvalidStorageKeyError

_UNSAFE_SEGMENT_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')


class DocumentFile(BaseModel):
    """Metadata describing a document that has been saved to storage -
    never the file's full content, so this stays cheap to pass around
    (e.g. in a future API response) without reloading bytes from disk."""

    model_config = ConfigDict(frozen=True)

    filename: str
    content_type: str
    size: int
    storage_key: str
    url: str | None = None


def _validate_path_segment(value: str, *, field_name: str) -> str:
    """Validates a single path segment (a tenant id, a filename) rather
    than silently sanitizing it - for an identifier like `tenant_id`,
    quietly rewriting an unsafe value risks mixing one tenant's documents
    into another's storage key, so this rejects instead."""
    if not value or not value.strip():
        raise InvalidStorageKeyError(f"{field_name} must not be empty")
    if value in (".", ".."):
        raise InvalidStorageKeyError(f"{field_name} must not be {value!r}")
    if "/" in value or "\\" in value:
        raise InvalidStorageKeyError(f"{field_name} must not contain a path separator: {value!r}")
    if _UNSAFE_SEGMENT_CHARS.search(value):
        raise InvalidStorageKeyError(f"{field_name} contains unsafe characters: {value!r}")
    return value


def build_document_storage_key(tenant_id: str, document_type: DocumentType, filename: str) -> str:
    """Builds a deterministic, tenant-scoped storage key:
    `{tenant_id}/documents/{document_type}/{filename}`. Use this to build
    the `storage_key` passed to `StorageService.save()`/`load()` rather
    than concatenating a key by hand."""
    safe_tenant_id = _validate_path_segment(tenant_id, field_name="tenant_id")
    safe_filename = _validate_path_segment(filename, field_name="filename")
    return f"{safe_tenant_id}/documents/{document_type.value}/{safe_filename}"


def _normalize_storage_key(storage_key: str) -> str:
    if not storage_key or not storage_key.strip():
        raise InvalidStorageKeyError("storage_key must not be empty")
    normalized = storage_key.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        raise InvalidStorageKeyError(f"storage_key must be a relative path: {storage_key!r}")
    segments = [segment for segment in normalized.split("/") if segment != ""]
    if any(segment == ".." for segment in segments):
        raise InvalidStorageKeyError(
            f"storage_key must not escape the storage root: {storage_key!r}"
        )
    if not segments:
        raise InvalidStorageKeyError(f"storage_key must not be empty: {storage_key!r}")
    return "/".join(segments)


def _resolve_within_root(root: Path, storage_key: str) -> Path:
    normalized = _normalize_storage_key(storage_key)
    root_resolved = root.resolve()
    candidate = (root_resolved / normalized).resolve()
    if not candidate.is_relative_to(root_resolved):
        raise InvalidStorageKeyError(f"storage_key escapes the storage root: {storage_key!r}")
    return candidate


class StorageService(ABC):
    """Provider-agnostic document storage interface. `storage_key` is
    always the caller's responsibility to build (see
    `build_document_storage_key`) - implementations only need to persist
    and retrieve bytes at that key."""

    @abstractmethod
    def save(self, storage_key: str, content: bytes, *, content_type: str) -> DocumentFile:
        raise NotImplementedError

    @abstractmethod
    def load(self, storage_key: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def url(self, storage_key: str) -> str | None:
        raise NotImplementedError


class LocalStorageService(StorageService):
    """Filesystem-backed `StorageService`, rooted at `root` (defaults to
    `Settings.document_storage_root`). Intended for local/dev and
    single-node deployments; S3/R2 (ARCHITECTURE.md §11) is future work
    behind the same interface.
    """

    def __init__(self, root: str | Path | None = None) -> None:
        self._root = Path(root if root is not None else get_settings().document_storage_root)

    def save(self, storage_key: str, content: bytes, *, content_type: str) -> DocumentFile:
        path = _resolve_within_root(self._root, storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return DocumentFile(
            filename=path.name,
            content_type=content_type,
            size=len(content),
            storage_key=storage_key,
            url=self.url(storage_key),
        )

    def load(self, storage_key: str) -> bytes:
        path = _resolve_within_root(self._root, storage_key)
        if not path.is_file():
            raise DocumentNotFoundError(f"No document stored at key: {storage_key!r}")
        return path.read_bytes()

    def delete(self, storage_key: str) -> None:
        path = _resolve_within_root(self._root, storage_key)
        path.unlink(missing_ok=True)

    def exists(self, storage_key: str) -> bool:
        path = _resolve_within_root(self._root, storage_key)
        return path.is_file()

    def url(self, storage_key: str) -> str | None:
        # Local storage has no publicly reachable URL of its own - a
        # presigned URL is an S3/R2-only concept (ARCHITECTURE.md §11),
        # added when that backend is implemented.
        return None
