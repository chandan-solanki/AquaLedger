import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.document_engine.document_types import DocumentType
from app.modules.documents.constants import PartyType, SourceType

_SORTABLE_FIELDS = frozenset({"generated_at", "document_number"})


class DocumentRecordCreate(BaseModel):
    """Internal creation schema for one DocumentRecord row (Sprint 12
    Session 6) - not exposed through any API; this is what a future
    generation-endpoint integration (Session 7+) or a test's setup step
    passes to `DocumentRecordService.record_generated_document()`.
    `party_type`/`party_id` must be supplied together or not at all - a
    party name with no party type (or vice versa) is a caller bug, not a
    valid "no party" document. `source_type`/`source_id` (Sprint 12
    Session 8) follow the identical both-or-neither rule - they identify
    the exact business record (e.g. an Invoice row) a document was
    generated from, for source-document navigation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "document_type": "invoice",
                "document_number": "INV/2026-27/00001",
                "party_type": "customer",
                "party_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
                "party_name": "ABC Sea Food",
                "source_type": "invoice",
                "source_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c01",
                "file_name": "Invoice_INV2026-2700001.pdf",
                "file_extension": "pdf",
                "content_type": "application/pdf",
                "storage_key": "019f7af3.../documents/invoice/Invoice_INV2026-2700001.pdf",
                "file_size": 48213,
                "generated_by": "019f83c8-6489-7bcf-beba-c241b7abbb04",
            }
        }
    )

    tenant_id: uuid.UUID
    document_type: DocumentType
    document_number: str = Field(min_length=1, max_length=50)
    party_type: PartyType | None = None
    party_id: uuid.UUID | None = None
    party_name: str | None = Field(default=None, max_length=255)
    source_type: SourceType | None = None
    source_id: uuid.UUID | None = None
    file_name: str = Field(min_length=1, max_length=255)
    file_extension: str = Field(min_length=1, max_length=10)
    content_type: str = Field(min_length=1, max_length=100)
    storage_key: str = Field(min_length=1, max_length=500)
    file_size: int = Field(gt=0)
    generated_by: uuid.UUID

    @model_validator(mode="after")
    def _check_party_fields_travel_together(self) -> "DocumentRecordCreate":
        if (self.party_type is None) != (self.party_id is None):
            raise ValueError("party_type and party_id must both be set, or both be omitted")
        return self

    @model_validator(mode="after")
    def _check_source_fields_travel_together(self) -> "DocumentRecordCreate":
        if (self.source_type is None) != (self.source_id is None):
            raise ValueError("source_type and source_id must both be set, or both be omitted")
        return self


class DocumentRecordResponse(BaseModel):
    """One row of Document Center history. `storage_key` is deliberately
    never included - the download endpoint resolves it internally
    (DocumentRecordService.download), the client only ever supplies the
    record's own `id`. `source_type`/`source_id` (Sprint 12 Session 8)
    are both `None` for any DocumentRecord created before this field
    existed (Sessions 6-7) - the frontend must treat that as "no source
    navigation available", never an error."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c07",
                "document_type": "invoice",
                "document_number": "INV/2026-27/00001",
                "party_type": "customer",
                "party_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
                "party_name": "ABC Sea Food",
                "source_type": "invoice",
                "source_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c01",
                "generated_at": "2026-08-15T04:00:00Z",
                "generated_by": "019f83c8-6489-7bcf-beba-c241b7abbb04",
                "generated_by_name": "Admin",
                "file_name": "Invoice_INV2026-2700001.pdf",
                "file_extension": "pdf",
                "content_type": "application/pdf",
                "file_size": 48213,
            }
        }
    )

    id: uuid.UUID
    document_type: DocumentType
    document_number: str
    party_type: PartyType | None
    party_id: uuid.UUID | None
    party_name: str | None
    source_type: SourceType | None
    source_id: uuid.UUID | None
    generated_at: datetime
    generated_by: uuid.UUID
    generated_by_name: str
    file_name: str
    file_extension: str
    content_type: str
    file_size: int


class DocumentListParams(BaseModel):
    """Query params for GET /documents. `q` searches document_number,
    party_name and file_name (case-insensitive substring) - the human-
    readable fields a user would actually recognize, not an arbitrary
    full-text index. `from_date`/`to_date` bound `generated_at` (the date
    a document was generated), inclusive on both ends."""

    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across document_number, party_name and file_name.",
        examples=["INV/2026-27/00001"],
    )
    document_type: DocumentType | None = Field(default=None, examples=[DocumentType.INVOICE])
    party_type: PartyType | None = Field(default=None, examples=[PartyType.CUSTOMER])
    party_id: uuid.UUID | None = Field(default=None, description="Filter by a specific party.")
    from_date: date | None = Field(
        default=None, description="Inclusive lower bound on generated_at's date."
    )
    to_date: date | None = Field(
        default=None, description="Inclusive upper bound on generated_at's date."
    )
    sort: str = Field(
        default="-generated_at",
        description="One of generated_at, document_number; prefix with '-' for descending.",
        examples=["generated_at", "-generated_at"],
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("sort")
    @classmethod
    def _check_sort(cls, value: str) -> str:
        field = value[1:] if value.startswith("-") else value
        if field not in _SORTABLE_FIELDS:
            raise ValueError(
                f"Invalid sort field '{field}'. Allowed: {', '.join(sorted(_SORTABLE_FIELDS))}"
            )
        return value

    @model_validator(mode="after")
    def _check_date_range(self) -> "DocumentListParams":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must not be after to_date")
        return self
