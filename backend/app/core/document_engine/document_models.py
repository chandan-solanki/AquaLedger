"""Shared DTOs for the Document Engine (Sprint 12 Session 1 - Document
Management Foundation). `DocumentData` is the one shape every future
renderer (invoice PDF, purchase bill PDF, receipt, ... - built in later
sessions) will consume. This engine never queries the database and
never computes a business figure (a total, a tax amount, a balance) -
a business service (invoicing, payments, purchasing, ...) builds a
`DocumentData` from figures it has already computed and hands the
finished object to `DocumentService`.

This is intentionally a separate abstraction from
`app.core.report_export.export_models.ReportExportData` - reports are
tabular analytical data, business documents have parties, line items
and totals with a fixed print layout. See ARCHITECTURE.md §41 for the
Reports side; this package is the Documents side.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.document_engine.document_types import DocumentType


class DocumentParty(BaseModel):
    """One party printed on a document - a customer on an invoice, a
    supplier on a purchase bill, either on a payment receipt. One shape
    covers all three (rather than separate `customer`/`supplier` DTOs)
    since the fields needed are identical regardless of which side of
    the trade the party is on."""

    model_config = ConfigDict(frozen=True)

    id: str | None = None
    name: str
    code: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    tax_id: str | None = None


class DocumentLine(BaseModel):
    """One line item - a fish sold on an invoice, a charge on a bill, or
    a row inside a `DocumentSection`'s own sub-table."""

    model_config = ConfigDict(frozen=True)

    description: str
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    tax_rate: Decimal | None = None
    tax_amount: Decimal | None = None
    line_total: Decimal
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentTotals(BaseModel):
    """The totals block printed at the foot of a document. Values arrive
    pre-computed by the calling business service - this engine never
    derives `total` from `subtotal`/`tax`/`discount` itself."""

    model_config = ConfigDict(frozen=True)

    subtotal: Decimal
    discount: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    rounding: Decimal = Decimal("0")
    total: Decimal
    paid: Decimal | None = None
    balance: Decimal | None = None


class DocumentSection(BaseModel):
    """A generic named block distinct from the document's primary
    `line_items` table - e.g. a Purchase Order's delivery instructions or
    a Delivery Challan's vehicle details. Reuses `DocumentLine` for its
    own optional sub-table rather than inventing a second row shape."""

    model_config = ConfigDict(frozen=True)

    title: str | None = None
    lines: list[DocumentLine] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentData(BaseModel):
    """The one shape every renderer (built in later sessions) receives -
    assembled entirely from data a business service has already fetched
    and computed. `document_type` records what this document *is*, for a
    renderer to pick its own template; `DocumentService.generate()`
    separately validates the *requested* type before resolving a
    renderer, so a caller asking to render "invoice" always gets an
    invoice renderer regardless of what this field says.
    """

    model_config = ConfigDict(frozen=True)

    document_type: DocumentType
    document_number: str
    document_date: date
    title: str
    subtitle: str | None = None
    tenant_name: str
    tenant_details: str | None = None
    party: DocumentParty | None = None
    sections: list[DocumentSection] = Field(default_factory=list)
    line_items: list[DocumentLine] = Field(default_factory=list)
    totals: DocumentTotals | None = None
    notes: str | None = None
    terms: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime
    generated_by: str

    @model_validator(mode="after")
    def _check_required_text_fields(self) -> "DocumentData":
        for field_name in ("document_number", "title", "tenant_name", "generated_by"):
            value: str = getattr(self, field_name)
            if not value.strip():
                raise ValueError(f"{field_name} must not be blank")
        return self


class RenderedDocument(BaseModel):
    """The generic result of running a `BaseDocumentRenderer` end-to-end
    (see base_document.py) - the same shape every future renderer
    returns regardless of what it actually rendered. `content_type`/
    `file_extension` are HTTP-response/storage metadata only; they carry
    no rendering logic of their own."""

    model_config = ConfigDict(frozen=True)

    content: bytes
    content_type: str
    file_extension: str
