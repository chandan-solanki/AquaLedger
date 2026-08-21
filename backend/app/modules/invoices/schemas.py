import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.invoices.constants import InvoiceStatus


class InvoiceItemResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c02",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "invoice_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c03",
                "line_number": 1,
                "fish_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
                "trip_catch_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c04",
                "description": "Pomfret - Grade A",
                "quantity": "50.000",
                "unit": "kg",
                "rate": "450.0000",
                "discount_percent": "0.00",
                "discount_amount": "0.00",
                "taxable_amount": "22500.00",
                "tax_rate": "5.00",
                "tax_amount": "1125.00",
                "line_total": "23625.00",
                "created_at": "2026-07-22T04:00:00Z",
                "updated_at": "2026-07-22T04:00:00Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    invoice_id: uuid.UUID
    line_number: int
    fish_id: uuid.UUID
    trip_catch_id: uuid.UUID | None
    description: str | None
    quantity: Decimal
    unit: str
    rate: Decimal
    discount_percent: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    line_total: Decimal
    created_at: datetime
    updated_at: datetime


class InvoiceItemCreateRequest(BaseModel):
    """tenant_id, created_by and updated_by are never client-supplied - the
    router populates them from the authenticated user. `line_number` is
    assigned server-side (next available for the invoice). Financial fields
    (discount_amount/taxable_amount/tax_amount/line_total) are not accepted
    here at all: the server always owns them, fixed to zero until Session 4
    introduces server-side calculation.

    `trip_catch_id` is required in this session even though the underlying
    column is nullable (ARCHITECTURE.md §16.1's "realized revenue" model,
    for future purchased/untracked stock): InvoiceService.add_item validates
    it exists, belongs to the tenant, matches `fish_id`, and that `quantity`
    does not exceed its available_quantity - all mandatory per TASKS.md
    Session 3."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trip_catch_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c04",
                "fish_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
                "description": "Pomfret - Grade A",
                "quantity": "50.000",
                "unit": "kg",
                "rate": "450.0000",
                "discount_percent": "0.00",
                "tax_rate": "5.00",
            }
        }
    )

    trip_catch_id: uuid.UUID = Field(
        description="Source trip catch - must exist for this tenant, and its fish must "
        "match fish_id."
    )
    fish_id: uuid.UUID = Field(description="Sold fish - must exist for this tenant.")
    description: str | None = None
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit: str = Field(min_length=1, max_length=20, examples=["kg"])
    rate: Decimal = Field(ge=0, max_digits=12, decimal_places=4)
    discount_percent: Decimal = Field(
        default=Decimal("0"), ge=0, le=100, max_digits=5, decimal_places=2
    )
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=5, decimal_places=2)


class InvoiceItemUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are changed.
    Only items on DRAFT invoices may be updated (see InvoiceService.update_item).
    Every update is fully revalidated against the resulting merged state
    (trip catch existence/tenant, fish existence/tenant, fish match, and
    quantity vs. available_quantity) regardless of which fields changed."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "quantity": "40.000",
                "rate": "460.0000",
            }
        }
    )

    trip_catch_id: uuid.UUID | None = Field(
        default=None, description="Reassign the source trip catch."
    )
    fish_id: uuid.UUID | None = Field(default=None, description="Reassign the sold fish.")
    description: str | None = None
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    rate: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=4)
    discount_percent: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=5, decimal_places=2
    )
    tax_rate: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)


class TripCatchDraftDemandResponse(BaseModel):
    """Sprint 15 Session 5: read-only, invoice-specific view of a trip
    catch's competing draft demand - NOT a stock field, and never merged
    into `TripCatchResponse`/`FishStockRow` (those stay Session 2/4's
    Caught/Sold/Available/Waste only). `other_draft_quantity` is the sum of
    `quantity` from every OTHER tenant's DRAFT, non-deleted invoice item
    referencing this trip catch - the invoice passed as `exclude_invoice_id`
    (if any) is never counted, whichever of its own items reference this
    same catch. This number is informational only: it is never used to
    reject a quantity server-side - the issue-time lock-protected check
    against `TripCatch.available_quantity` remains the sole authority."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trip_catch_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c04",
                "other_draft_quantity": "40.000",
            }
        }
    )

    trip_catch_id: uuid.UUID
    other_draft_quantity: Decimal


class ConflictingInvoiceSummary(BaseModel):
    """Sprint 15 Session 6: exactly what the conflict-resolution UI needs
    about one OTHER invoice referencing the same trip catch - never the
    full invoice (no totals, no remarks, no tenant_id)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "invoice_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c03",
                "invoice_number": "INV/2026-27/00025",
                "status": "issued",
                "invoice_date": "2026-07-22",
                "company_name": "ABC Traders",
                "quantity": "60.000",
            }
        }
    )

    invoice_id: uuid.UUID
    invoice_number: str | None
    status: InvoiceStatus
    invoice_date: date
    company_name: str
    quantity: Decimal


class TripCatchConflictResponse(BaseModel):
    """Sprint 15 Session 6: the full "why did issuing this fail" picture for
    one trip catch - `required_quantity`/`shortfall_quantity` are null when
    no specific attempted quantity is known (`required_quantity` wasn't
    passed). This is informational only, resolved fresh at request time -
    it never reserves or mutates stock, and the issue-time lock-protected
    check in InvoiceService.issue remains the sole authority."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trip_catch_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c04",
                "required_quantity": "50.000",
                "available_quantity": "40.000",
                "shortfall_quantity": "10.000",
                "conflicting_invoices": [
                    {
                        "invoice_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c03",
                        "invoice_number": "INV/2026-27/00025",
                        "status": "issued",
                        "invoice_date": "2026-07-22",
                        "company_name": "ABC Traders",
                        "quantity": "60.000",
                    }
                ],
            }
        }
    )

    trip_catch_id: uuid.UUID
    required_quantity: Decimal | None
    available_quantity: Decimal
    shortfall_quantity: Decimal | None
    conflicting_invoices: list[ConflictingInvoiceSummary]


class TripCatchInvoiceUsage(BaseModel):
    """Sprint 15 Session 7: per-trip-catch invoice usage summary for the
    Fish Stock detail page's Contributing Catches table - visibility only,
    never a stock reservation (draft invoices never reduce
    available_quantity; only issue() does that). `invoice_count` counts
    distinct non-cancelled, non-deleted invoices referencing the catch.
    `draft_quantity` is the quantity referenced by DRAFT invoices (demand
    only); `consumed_quantity` is the quantity on ISSUED/PARTIALLY_PAID/PAID
    invoices (already deducted from available_quantity, and should mirror
    TripCatch.sold_quantity in the common case of one fish per catch)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trip_catch_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c04",
                "invoice_count": 2,
                "draft_quantity": "30.000",
                "consumed_quantity": "60.000",
            }
        }
    )

    trip_catch_id: uuid.UUID
    invoice_count: int
    draft_quantity: Decimal
    consumed_quantity: Decimal


class TripCatchOtherInvoiceUsage(BaseModel):
    """Sprint 15 Session 8: for one trip catch THIS invoice's own items
    reference, how much OTHER invoices (any invoice besides the one being
    viewed) reference it - shown proactively on the Invoice Detail page's
    item table, before any issue attempt. Deliberately a distinct schema
    from `TripCatchInvoiceUsage` (Session 7) even though the underlying
    query is shared: that one is an absolute count gated on `fish:view` with
    no exclusion, this one is always relative to "other than the invoice I'm
    looking at" and gated on `invoice:view`. `other_invoice_count`/
    `other_draft_quantity`/`other_consumed_quantity` never include the
    current invoice's own items, regardless of how many of its own items
    reference this same trip catch."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trip_catch_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c04",
                "other_invoice_count": 2,
                "other_draft_quantity": "20.000",
                "other_consumed_quantity": "40.000",
            }
        }
    )

    trip_catch_id: uuid.UUID
    other_invoice_count: int
    other_draft_quantity: Decimal
    other_consumed_quantity: Decimal


class InvoiceIssuePreflightConflict(BaseModel):
    """Sprint 15 Session 10: one trip catch this DRAFT invoice references
    that, based on the current database state (read without any lock), no
    longer has enough `available_quantity` to satisfy this invoice's own
    requested quantity. `requested_quantity` is this invoice's own items'
    quantity summed for this trip catch (an invoice with two items against
    the same catch is counted once, aggregated). `other_draft_quantity` is
    the same "other invoice usage" figure Sessions 7/8 already established -
    additional context, not itself the cause of `is_sufficient`. This is
    advisory only: the authoritative, lock-protected check remains
    InvoiceService.issue's own call to
    TripCatchService.deduct_available_quantity, re-read fresh at issue time
    - a clean preflight (no conflicts) is never a guarantee that issuing
    will actually succeed a moment later."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trip_catch_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c04",
                "requested_quantity": "30.000",
                "available_quantity": "25.000",
                "is_sufficient": False,
                "shortfall_quantity": "5.000",
                "other_draft_quantity": "10.000",
            }
        }
    )

    trip_catch_id: uuid.UUID
    requested_quantity: Decimal
    available_quantity: Decimal
    is_sufficient: bool
    shortfall_quantity: Decimal
    other_draft_quantity: Decimal


class InvoiceIssuePreflightResponse(BaseModel):
    """Sprint 15 Session 10: "is this draft invoice likely issuable right
    now" - one bounded read regardless of item count, never a per-item or
    per-trip-catch request. `conflicts` lists only the trip catches that are
    currently NOT sufficient (an empty list means `can_issue_now` is true) -
    a sufficient catch never appears here, since the warning UI only ever
    needs to render actual problems. Read-only and resolved fresh at request
    time; never reserves or deducts stock, and never a substitute for the
    issue-time authoritative validation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "invoice_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c03",
                "can_issue_now": False,
                "conflicts": [
                    {
                        "trip_catch_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c04",
                        "requested_quantity": "30.000",
                        "available_quantity": "25.000",
                        "is_sufficient": False,
                        "shortfall_quantity": "5.000",
                        "other_draft_quantity": "10.000",
                    }
                ],
            }
        }
    )

    invoice_id: uuid.UUID
    can_issue_now: bool
    conflicts: list[InvoiceIssuePreflightConflict]


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c03",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "company_id": "019f7af3-83ae-783a-b139-40a239786b30",
                "invoice_number": None,
                "invoice_date": "2026-07-22",
                "due_date": "2026-08-06",
                "status": "draft",
                "subtotal": "22500.00",
                "discount_amount": "0.00",
                "taxable_amount": "22500.00",
                "tax_amount": "1125.00",
                "transport_charge": "0.00",
                "other_charge": "0.00",
                "round_off": "0.00",
                "total_amount": "23625.00",
                "paid_amount": "0.00",
                "balance_amount": "23625.00",
                "remarks": None,
                "issued_at": None,
                "created_at": "2026-07-22T04:00:00Z",
                "updated_at": "2026-07-22T04:00:00Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    company_id: uuid.UUID
    invoice_number: str | None
    invoice_date: date
    due_date: date | None
    status: InvoiceStatus
    subtotal: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    transport_charge: Decimal
    other_charge: Decimal
    round_off: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    balance_amount: Decimal
    remarks: str | None
    issued_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InvoiceCreateRequest(BaseModel):
    """tenant_id, created_by and updated_by are never client-supplied - the
    router populates them from the authenticated user. `transport_charge`/
    `other_charge` are the only financial inputs the client controls -
    every *calculated* financial field (subtotal/discount_amount/
    taxable_amount/tax_amount/round_off/total_amount/paid_amount/
    balance_amount) is not accepted here at all: the server always owns
    them (app.modules.invoices.domain.totals, Session 4). `status` is
    always DRAFT and `invoice_number` always NULL at creation - numbers are
    assigned only at issue (ARCHITECTURE.md §13.1, Session 5)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "company_id": "019f7af3-83ae-783a-b139-40a239786b30",
                "invoice_date": "2026-07-22",
                "due_date": "2026-08-06",
                "transport_charge": "250.00",
                "other_charge": "0.00",
                "remarks": "Weekly settlement",
            }
        }
    )

    company_id: uuid.UUID = Field(
        description="Billed-to company - must exist for this tenant and be active."
    )
    invoice_date: date
    due_date: date | None = None
    transport_charge: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    other_charge: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    remarks: str | None = None


class InvoiceUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are changed.
    Only DRAFT invoices may be updated (see InvoiceService.update).
    `transport_charge`/`other_charge` changes trigger a full totals
    recalculation, the same as an item add/edit/delete. Calculated
    financial fields are not accepted here either, for the same reason as
    InvoiceCreateRequest."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "due_date": "2026-08-13",
                "remarks": "Revised due date",
            }
        }
    )

    company_id: uuid.UUID | None = Field(
        default=None,
        description="Reassign the billed-to company - must exist for this tenant and be active.",
    )
    invoice_date: date | None = None
    due_date: date | None = None
    transport_charge: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    other_charge: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    remarks: str | None = None


_SORTABLE_FIELDS = frozenset({"invoice_date", "invoice_number", "created_at"})


class InvoiceListParams(BaseModel):
    """Query params for GET /invoices - bound via FastAPI's Depends() model support."""

    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across invoice_number and the billed company's name.",
        examples=["INV-2026"],
    )
    status: InvoiceStatus | None = Field(default=None, examples=[InvoiceStatus.DRAFT])
    company_id: uuid.UUID | None = Field(default=None, description="Filter by billed company.")
    invoice_date_from: date | None = Field(
        default=None, description="Inclusive lower bound on invoice_date."
    )
    invoice_date_to: date | None = Field(
        default=None, description="Inclusive upper bound on invoice_date."
    )
    sort: str = Field(
        default="-created_at",
        description="One of invoice_date, invoice_number, created_at; prefix with '-' "
        "for descending.",
        examples=["invoice_date", "-invoice_number"],
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
