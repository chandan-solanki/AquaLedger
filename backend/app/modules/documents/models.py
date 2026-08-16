import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.auth.models import User


class DocumentRecord(Base):
    """One generation event of a business document (Sprint 12 Session 6:
    Document Center foundation) - e.g. "this Invoice PDF was rendered at
    this moment, by this user, stored at this key". Deliberately a log of
    *events*, not a deduplicated catalog of "the" document: downloading
    the same invoice's PDF three times creates three rows, all sharing
    the same document_number but distinct generated_at/generated_by -
    there is no uniqueness constraint on document_number here.

    Append-only, like `AuditLog`/`SupplierPaymentAllocation`/the numbering
    sequence tables (all of which omit soft-delete) - a row here is a
    fact about something that already happened, not a mutable business
    entity a user edits or deletes later, so there is no updated_at,
    deleted_at or deleted_by. `generated_at` is the row's one timestamp;
    a separate created_at would always be identical to it, since a row is
    only ever created at the moment its document was generated.

    `document_type` reuses `app.core.document_engine.document_types.
    DocumentType`'s own values verbatim (stored as plain string, not a DB
    enum, the same convention every *_status column in this codebase
    uses) - no second document-type enum is introduced. Report exports
    (Sales Report, Customer/Supplier Statement, etc. - `app.core.
    report_export`'s own disjoint `ReportType`) are deliberately outside
    this table: they have no RenderedDocument/StorageService pipeline of
    their own today, so persisting their metadata here would require
    inventing a parallel mechanism, not reusing this one - see the
    Session 6 deliverable's "Architecture Decision" for the full
    reasoning.

    `party_type`/`party_id`/`party_name` describe the document's business
    counterparty generically rather than via per-entity foreign keys
    (`customer_id`, `supplier_id`, ...) - `party_id` can point at
    `companies.id` or `suppliers.id` depending on `party_type`, so no
    single FK constraint could span both possible targets anyway.
    `party_name` is captured at generation time (denormalized) rather
    than resolved via a live join: unlike `generated_by` (always exactly
    one table, `users`), the party's target table is polymorphic, and a
    conditional dual-join purely to render a history list would add real
    complexity for a cosmetic field on a table whose whole purpose is
    recording what was true at the moment of generation.

    `storage_key` is never exposed through the API (see
    `DocumentRecordResponse`) - only `DocumentRecordService.download`
    reads it, handing it straight to `StorageService.load()`.

    `source_type`/`source_id` (Sprint 12 Session 8) identify the exact
    business record a document was generated from - e.g. `source_type=
    "invoice", source_id=<that invoice's id>` - so the frontend can link
    "Document Number" straight to its source record's own detail page.
    Both are nullable and were added by a later migration than the
    table's own creation: every DocumentRecord created in Sessions 6-7
    (before this column existed) has NULL here and must remain fully
    listable/filterable/downloadable regardless - Document Number simply
    renders as plain, non-clickable text for those rows. Like
    `party_type`/`party_id`, no FK constraint is possible: `source_id`
    is polymorphic across four different tables depending on
    `source_type`.
    """

    __tablename__ = "document_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )

    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    document_number: Mapped[str] = mapped_column(String(50), nullable=False)

    party_type: Mapped[str | None] = mapped_column(String(20))
    party_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    party_name: Mapped[str | None] = mapped_column(String(255))

    source_type: Mapped[str | None] = mapped_column(String(30))
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(10), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    generated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    generated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    generated_by_user: Mapped["User"] = relationship()

    __table_args__ = (
        Index("ix_document_records_tenant", "tenant_id"),
        Index("ix_document_records_tenant_type", "tenant_id", "document_type"),
        Index("ix_document_records_tenant_generated_at", "tenant_id", "generated_at"),
        Index("ix_document_records_tenant_document_number", "tenant_id", "document_number"),
        Index("ix_document_records_tenant_party", "tenant_id", "party_type", "party_id"),
        Index("ix_document_records_tenant_source", "tenant_id", "source_type", "source_id"),
    )
