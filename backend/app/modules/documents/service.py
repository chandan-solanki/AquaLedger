import math
import uuid
from typing import NamedTuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import PaginatedResponse, PaginationMeta
from app.core.document_engine.document_models import DocumentData
from app.core.document_engine.document_service import DocumentService
from app.core.document_engine.document_types import DocumentType
from app.core.document_engine.exceptions import DocumentNotFoundError as StorageFileNotFoundError
from app.core.document_engine.filename import build_document_filename
from app.core.document_engine.storage import (
    LocalStorageService,
    StorageService,
    build_document_storage_key,
)
from app.modules.documents.constants import PartyType, SourceType
from app.modules.documents.exceptions import DocumentFileMissingError, DocumentRecordNotFoundError
from app.modules.documents.models import DocumentRecord
from app.modules.documents.repository import DocumentRecordRepository
from app.modules.documents.schemas import (
    DocumentListParams,
    DocumentRecordCreate,
    DocumentRecordResponse,
)


class DocumentDownload(NamedTuple):
    """Everything the download endpoint needs to stream a response -
    the record's own content_type/file_name, plus the bytes read through
    StorageService. Named distinctly from RenderedDocument
    (app.core.document_engine) since this comes from storage, not a
    fresh render."""

    content: bytes
    content_type: str
    file_name: str


class GeneratedDocument(NamedTuple):
    """What generate_store_and_record() hands back to a business
    router - the exact bytes just rendered (and stored), ready to build
    an HTTP response from. Structurally identical to DocumentDownload,
    but named distinctly: this is the output of a fresh generation, not
    a read of previously-stored history."""

    content: bytes
    content_type: str
    file_name: str


class DocumentRecordService:
    """Document Center (Sprint 12 Session 6): metadata persistence,
    search/discovery and secure download for documents already generated
    by the Document Engine (app.core.document_engine) - never generation
    itself. Reuses the existing StorageService abstraction
    (LocalStorageService by default, matching every other storage-facing
    call in this codebase) rather than a second storage mechanism.

    `record_generated_document()` is the low-level write path -
    deliberately generic (a plain DTO in, a response out; it never
    queries Invoice/PurchaseBill/Payment/Supplier/Company). Session 7
    adds `generate_store_and_record()` on top of it - the single call
    every business document-download endpoint now makes, orchestrating
    render -> store -> record -> return in one place so that logic is
    never duplicated across the four business routers.
    """

    def __init__(self, session: AsyncSession, storage: StorageService | None = None) -> None:
        self._session = session
        self._repo = DocumentRecordRepository(session)
        self._storage = storage or LocalStorageService()

    async def generate_store_and_record(
        self,
        data: DocumentData,
        *,
        tenant_id: uuid.UUID,
        party_type: PartyType | None,
        party_id: uuid.UUID | None,
        party_name: str | None,
        generated_by: uuid.UUID,
        source_type: SourceType | None = None,
        source_id: uuid.UUID | None = None,
    ) -> GeneratedDocument:
        """The one call every business document-download endpoint makes
        (Sprint 12 Session 7) - renders `data` exactly once through the
        shared Document Engine, saves those exact bytes via
        StorageService, records a DocumentRecord referencing them, and
        hands the same bytes back for the caller's own HTTP response.
        `data.document_type`/`data.document_number` drive the render,
        filename and storage key - there is no separate document_type
        parameter to (mis)match against them.

        Deliberately business-agnostic: this knows DocumentType/
        DocumentData/RenderedDocument/StorageService and its own
        DocumentRecord machinery, never Invoice/PurchaseBill/Payment/
        Supplier/Customer - the caller (each business router) supplies
        party_type/party_id/party_name/generated_by, resolved from its
        own already-fetched document context (ARCHITECTURE.md §2: no
        repeat business-module lookups happen here). `source_type`/
        `source_id` (Sprint 12 Session 8) are optional and passed the
        same way - each router already has its own path parameter (the
        very id it just rendered a document for) in hand, so no extra
        lookup is needed to supply them.

        Failure semantics: if storage.save() raises, nothing is
        recorded - there is nothing yet to compensate. If
        record_generated_document() raises after a successful save, the
        just-saved file is deleted (storage.delete()) before
        re-raising - a DocumentRecord must never reference a storage key
        that doesn't actually exist, and a stored file must never be
        left dangling with no record pointing at it. Either way the
        caller's request fails outright rather than silently returning a
        PDF the Document Center never learns about.
        """
        rendered = DocumentService().generate(data.document_type.value, data)
        filename = build_document_filename(
            data.document_type, data.document_number, extension=rendered.file_extension
        )
        storage_key = build_document_storage_key(str(tenant_id), data.document_type, filename)

        self._storage.save(storage_key, rendered.content, content_type=rendered.content_type)
        try:
            await self.record_generated_document(
                DocumentRecordCreate(
                    tenant_id=tenant_id,
                    document_type=data.document_type,
                    document_number=data.document_number,
                    party_type=party_type,
                    party_id=party_id,
                    party_name=party_name,
                    source_type=source_type,
                    source_id=source_id,
                    file_name=filename,
                    file_extension=rendered.file_extension,
                    content_type=rendered.content_type,
                    storage_key=storage_key,
                    file_size=len(rendered.content),
                    generated_by=generated_by,
                )
            )
        except Exception:
            self._storage.delete(storage_key)
            raise

        return GeneratedDocument(
            content=rendered.content, content_type=rendered.content_type, file_name=filename
        )

    async def record_generated_document(
        self, payload: DocumentRecordCreate
    ) -> DocumentRecordResponse:
        record = DocumentRecord(
            tenant_id=payload.tenant_id,
            document_type=payload.document_type.value,
            document_number=payload.document_number,
            party_type=payload.party_type.value if payload.party_type else None,
            party_id=payload.party_id,
            party_name=payload.party_name,
            source_type=payload.source_type.value if payload.source_type else None,
            source_id=payload.source_id,
            file_name=payload.file_name,
            file_extension=payload.file_extension,
            content_type=payload.content_type,
            storage_key=payload.storage_key,
            file_size=payload.file_size,
            generated_by=payload.generated_by,
        )
        await self._repo.add(record)
        try:
            await self._session.commit()
        except Exception:
            # Leaves the session usable for the caller afterward - in
            # particular, generate_store_and_record's own compensation
            # (storage.delete()) runs on a clean session, and the FastAPI
            # request-scoped session isn't left mid-failed-transaction if
            # anything downstream tries to use it again.
            await self._session.rollback()
            raise
        await self._session.refresh(record, attribute_names=["generated_by_user"])
        return self._to_response(record)

    async def list_documents(
        self, *, tenant_id: uuid.UUID, params: DocumentListParams
    ) -> PaginatedResponse[DocumentRecordResponse]:
        records, total = await self._repo.search(
            tenant_id,
            q=params.q,
            document_type=params.document_type.value if params.document_type else None,
            party_type=params.party_type,
            party_id=params.party_id,
            from_date=params.from_date,
            to_date=params.to_date,
            sort=params.sort,
            page=params.page,
            page_size=params.page_size,
        )
        total_pages = math.ceil(total / params.page_size) if total else 0
        meta = PaginationMeta(
            total_records=total,
            total_pages=total_pages,
            current_page=params.page,
            page_size=params.page_size,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )
        return PaginatedResponse(
            data=[self._to_response(record) for record in records],
            meta=meta,
        )

    async def download(self, document_id: uuid.UUID, *, tenant_id: uuid.UUID) -> DocumentDownload:
        """Resolves a DocumentRecord for the caller's tenant, then reads
        its bytes through StorageService - the client only ever supplies
        `document_id`; storage_key never leaves the server (see
        DocumentRecordResponse's docstring)."""
        record = await self._get_or_raise(document_id, tenant_id)
        try:
            content = self._storage.load(record.storage_key)
        except StorageFileNotFoundError as exc:
            raise DocumentFileMissingError(
                "The file for this document is no longer available"
            ) from exc
        return DocumentDownload(
            content=content, content_type=record.content_type, file_name=record.file_name
        )

    async def _get_or_raise(self, document_id: uuid.UUID, tenant_id: uuid.UUID) -> DocumentRecord:
        record = await self._repo.get_by_id(document_id, tenant_id)
        if record is None:
            raise DocumentRecordNotFoundError("Document not found")
        return record

    @staticmethod
    def _to_response(record: DocumentRecord) -> DocumentRecordResponse:
        return DocumentRecordResponse(
            id=record.id,
            document_type=DocumentType(record.document_type),
            document_number=record.document_number,
            party_type=PartyType(record.party_type) if record.party_type else None,
            party_id=record.party_id,
            party_name=record.party_name,
            source_type=SourceType(record.source_type) if record.source_type else None,
            source_id=record.source_id,
            generated_at=record.generated_at,
            generated_by=record.generated_by,
            generated_by_name=record.generated_by_user.full_name,
            file_name=record.file_name,
            file_extension=record.file_extension,
            content_type=record.content_type,
            file_size=record.file_size,
        )
