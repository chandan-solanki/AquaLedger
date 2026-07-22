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
