import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.purchase.constants import PurchaseStatus

_SORTABLE_FIELDS = frozenset({"bill_date", "bill_number", "created_at"})
_ITEM_SORTABLE_FIELDS = frozenset({"line_number", "description", "created_at"})


class PurchaseBillItemResponse(BaseModel):
    """Sprint 11 Session 1 response shape (TASKS.md: "schemas.py (Response
    only)"), paired with the Session 3 request schemas below.
    discount_amount/taxable_amount/tax_amount/line_total are computed
    server-side by app.modules.purchase.domain.totals and recalculated on
    every item mutation (Session 4) - never client-supplied."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c06",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "purchase_bill_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c05",
                "line_number": 1,
                "description": "Pomfret - Grade A",
                "quantity": "50.000",
                "unit": "KG",
                "rate": "450.0000",
                "discount_percent": "0.00",
                "discount_amount": "0.00",
                "taxable_amount": "22500.00",
                "tax_rate": "5.00",
                "tax_amount": "1125.00",
                "line_total": "23625.00",
                "created_at": "2026-07-23T04:00:00Z",
                "updated_at": "2026-07-23T04:00:00Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    purchase_bill_id: uuid.UUID
    line_number: int
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


class PurchaseBillItemCreateRequest(BaseModel):
    """Sprint 11 Session 3 (TASKS.md). tenant_id, purchase_bill_id and
    line_number are never client-supplied - line_number is assigned
    server-side (PurchaseRepository.allocate_next_line_number). Financial
    fields (discount_amount/taxable_amount/tax_amount/line_total) are not
    accepted here at all: the server always owns them, computed by
    app.modules.purchase.domain.totals from quantity/rate/discount_percent/
    tax_rate (Session 4). Unlike InvoiceItemCreateRequest, `description` is
    required (TASKS.md's explicit validation list) even though the
    underlying column stays nullable, and there is no fish_id/trip_catch_id
    - a purchase line has no link to a sold-fish master or a trip catch."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Pomfret - Grade A",
                "quantity": "50.000",
                "unit": "KG",
                "rate": "450.0000",
                "discount_percent": "0.00",
                "tax_rate": "5.00",
            }
        }
    )

    description: str = Field(min_length=1, examples=["Pomfret - Grade A"])
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit: str = Field(min_length=1, max_length=20, examples=["KG"])
    rate: Decimal = Field(ge=0, max_digits=12, decimal_places=4)
    discount_percent: Decimal = Field(
        default=Decimal("0"), ge=0, le=100, max_digits=5, decimal_places=2
    )
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=5, decimal_places=2)


class PurchaseBillItemUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are changed.
    Only items on DRAFT purchase bills may be updated (see
    PurchaseService.update_item). Financial fields/line_number are not
    accepted here either, for the same reason as
    PurchaseBillItemCreateRequest."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "quantity": "40.000",
                "rate": "460.0000",
            }
        }
    )

    description: str | None = Field(default=None, min_length=1)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    rate: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=4)
    discount_percent: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=5, decimal_places=2
    )
    tax_rate: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)


class PurchaseBillItemListParams(BaseModel):
    """Query params for GET /purchase/{purchase_bill_id}/items. No
    pagination - a purchase bill's line count is small and bounded, the
    same posture InvoiceItem's own item list takes."""

    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across description.",
        examples=["Pomfret"],
    )
    sort: str = Field(
        default="line_number",
        description="One of line_number, description, created_at; prefix with '-' for descending.",
        examples=["line_number", "-created_at"],
    )

    @field_validator("sort")
    @classmethod
    def _check_sort(cls, value: str) -> str:
        field = value[1:] if value.startswith("-") else value
        if field not in _ITEM_SORTABLE_FIELDS:
            raise ValueError(
                f"Invalid sort field '{field}'. Allowed: {', '.join(sorted(_ITEM_SORTABLE_FIELDS))}"
            )
        return value


class PurchaseBillResponse(BaseModel):
    """Sprint 11 Session 1 response shape (TASKS.md: "schemas.py (Response
    only)"), extended with `taxable_amount` in Session 4. subtotal/
    discount_amount/taxable_amount/tax_amount/total_amount/balance_amount
    are computed server-side by app.modules.purchase.domain.totals and
    recalculated on every item mutation (Session 4); paid_amount stays 0
    until the Session 5 supplier-payment workflow."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c05",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "supplier_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
                "bill_number": None,
                "bill_date": "2026-07-23",
                "due_date": "2026-08-22",
                "status": "draft",
                "subtotal": "23625.00",
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
                "posted_at": None,
                "created_at": "2026-07-23T04:00:00Z",
                "updated_at": "2026-07-23T04:00:00Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    supplier_id: uuid.UUID
    bill_number: str | None
    bill_date: date
    due_date: date | None
    status: PurchaseStatus
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
    posted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PurchaseBillCreateRequest(BaseModel):
    """tenant_id, created_by and updated_by are never client-supplied - the
    router populates them from the authenticated user. Every financial
    field (subtotal/discount_amount/taxable_amount/tax_amount/
    transport_charge/other_charge/round_off/total_amount/paid_amount/
    balance_amount), `bill_number`, `status` and `posted_at` are not
    accepted here at all: the server always owns them (PurchaseService.create)
    - all financial fields start at 0 (no items exist yet), `status` is
    always DRAFT, `bill_number`/`posted_at` always NULL until the Session 5
    posting workflow assigns them. Unlike InvoiceCreateRequest,
    `transport_charge`/`other_charge` are NOT client-settable in this
    session either (TASKS.md Sprint 11 Session 2 lists them under "Server
    owns")."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "supplier_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
                "bill_date": "2026-07-23",
                "due_date": "2026-08-22",
                "remarks": "Weekly settlement",
            }
        }
    )

    supplier_id: uuid.UUID = Field(
        description="Billing supplier - must exist for this tenant and be active."
    )
    bill_date: date
    due_date: date | None = None
    remarks: str | None = None


class PurchaseBillUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are changed.
    Only DRAFT purchase bills may be updated (see PurchaseService.update).
    Financial fields/`bill_number`/`status`/`posted_at` are not accepted
    here either, for the same reason as PurchaseBillCreateRequest."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "due_date": "2026-08-29",
                "remarks": "Revised due date",
            }
        }
    )

    supplier_id: uuid.UUID | None = Field(
        default=None,
        description="Reassign the billing supplier - must exist for this tenant and be active.",
    )
    bill_date: date | None = None
    due_date: date | None = None
    remarks: str | None = None


class PurchaseBillListParams(BaseModel):
    """Query params for GET /purchase - bound via FastAPI's Depends() model
    support."""

    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across bill_number and the billing supplier's name.",
        examples=["PUR-2026"],
    )
    status: PurchaseStatus | None = Field(default=None, examples=[PurchaseStatus.DRAFT])
    supplier_id: uuid.UUID | None = Field(default=None, description="Filter by billing supplier.")
    bill_date_from: date | None = Field(
        default=None, description="Inclusive lower bound on bill_date."
    )
    bill_date_to: date | None = Field(
        default=None, description="Inclusive upper bound on bill_date."
    )
    sort: str = Field(
        default="-created_at",
        description="One of bill_date, bill_number, created_at; prefix with '-' for descending.",
        examples=["bill_date", "-bill_number"],
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
