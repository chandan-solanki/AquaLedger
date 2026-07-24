import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.supplier_payments.constants import PaymentMethod, SupplierPaymentStatus

_SORTABLE_FIELDS = frozenset({"payment_date", "payment_number", "created_at"})


class SupplierPaymentResponse(BaseModel):
    """Sprint 12 Session 1 response shape (TASKS.md: "schemas.py (Response
    only)"), mirroring `PaymentResponse` on the buy side. Request schemas
    (create/update/list) land in Session 2."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c07",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "supplier_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
                "payment_number": None,
                "payment_date": "2026-07-23",
                "payment_method": "cheque",
                "reference_number": "778821",
                "bank_name": "State Bank",
                "amount": "150000.00",
                "allocated_amount": "0.00",
                "unallocated_amount": "150000.00",
                "remarks": "Against pending purchase bills",
                "status": "draft",
                "posted_at": None,
                "created_at": "2026-07-23T04:00:00Z",
                "updated_at": "2026-07-23T04:00:00Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    supplier_id: uuid.UUID
    payment_number: str | None
    payment_date: date
    payment_method: PaymentMethod
    reference_number: str | None
    bank_name: str | None
    amount: Decimal
    allocated_amount: Decimal
    unallocated_amount: Decimal
    remarks: str | None
    status: SupplierPaymentStatus
    posted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SupplierPaymentAllocationResponse(BaseModel):
    """Sprint 12 Session 1 response shape (TASKS.md: "schemas.py (Response
    only)"), mirroring `PaymentAllocationResponse` on the buy side. Request
    schemas land in Session 3."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c08",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "supplier_payment_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c07",
                "purchase_bill_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c05",
                "allocated_amount": "90000.00",
                "created_at": "2026-07-23T04:05:00Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    supplier_payment_id: uuid.UUID
    purchase_bill_id: uuid.UUID
    allocated_amount: Decimal
    created_at: datetime


class SupplierPaymentAllocationCreateRequest(BaseModel):
    """tenant_id and created_by are never client-supplied - the router
    populates created_by from the authenticated user; there is no
    updated_by, this row is append-only (see SupplierPaymentAllocation's
    docstring). `allocated_amount` is validated against the purchase bill's
    balance_amount and the payment's unallocated_amount by
    SupplierPaymentService.create_allocation
    (app.modules.supplier_payments.domain.allocation) - not further bounded
    here beyond being positive. Mirrors PaymentAllocationCreateRequest."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "purchase_bill_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c05",
                "allocated_amount": "90000.00",
            }
        }
    )

    purchase_bill_id: uuid.UUID = Field(
        description="Target purchase bill - must exist for this tenant and be posted."
    )
    allocated_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class SupplierPaymentAllocationUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are
    changed. The full merged state (purchase_bill_id, allocated_amount) is
    revalidated on every update, regardless of which fields changed - same
    rules as creating an allocation (see
    SupplierPaymentService.update_allocation). Mirrors
    PaymentAllocationUpdateRequest."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "allocated_amount": "120000.00",
            }
        }
    )

    purchase_bill_id: uuid.UUID | None = Field(
        default=None, description="Reassign the target purchase bill."
    )
    allocated_amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)


class SupplierPaymentCreateRequest(BaseModel):
    """tenant_id, created_by and updated_by are never client-supplied - the
    router populates them from the authenticated user. `payment_number`,
    `allocated_amount`, `unallocated_amount`, `status` and `posted_at` are
    not accepted here at all: the server always owns them
    (SupplierPaymentService.create) - number stays NULL until the Session 5
    posting workflow, allocated_amount starts at 0, unallocated_amount
    starts equal to `amount`, and status is always DRAFT. Mirrors
    PaymentCreateRequest on the buy side."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "supplier_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
                "payment_date": "2026-07-23",
                "payment_method": "cheque",
                "reference_number": "778821",
                "bank_name": "State Bank",
                "amount": "150000.00",
                "remarks": "Against pending purchase bills",
            }
        }
    )

    supplier_id: uuid.UUID = Field(
        description="Paying-to supplier - must exist for this tenant and be active."
    )
    payment_date: date
    payment_method: PaymentMethod
    reference_number: str | None = Field(default=None, max_length=100)
    bank_name: str | None = Field(default=None, max_length=255)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    remarks: str | None = None


class SupplierPaymentUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are changed.
    Only DRAFT supplier payments may be updated (see
    SupplierPaymentService.update). `payment_number`/`allocated_amount`/
    `unallocated_amount`/`status`/`posted_at` are not accepted here either,
    for the same reason as SupplierPaymentCreateRequest. If `amount`
    changes, `unallocated_amount` is recomputed from it (always equal to
    `amount` in this session - `allocated_amount` stays 0 until the Session
    3 allocation engine exists). Mirrors PaymentUpdateRequest."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "amount": "175000.00",
                "remarks": "Revised amount",
            }
        }
    )

    supplier_id: uuid.UUID | None = Field(
        default=None,
        description="Reassign the paying-to supplier - must exist for this tenant and be active.",
    )
    payment_date: date | None = None
    payment_method: PaymentMethod | None = None
    reference_number: str | None = Field(default=None, max_length=100)
    bank_name: str | None = Field(default=None, max_length=255)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    remarks: str | None = None


class SupplierPaymentListParams(BaseModel):
    """Query params for GET /supplier-payments - bound via FastAPI's
    Depends() model support. Mirrors PaymentListParams, minus an `amount`
    sort option (not requested for this module - TASKS.md Sprint 12 Session
    2's SORT section lists only payment_date/payment_number/created_at)."""

    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across payment_number, reference_number and "
        "the paying-to supplier's name.",
        examples=["778821"],
    )
    status: SupplierPaymentStatus | None = Field(
        default=None, examples=[SupplierPaymentStatus.DRAFT]
    )
    supplier_id: uuid.UUID | None = Field(default=None, description="Filter by paying-to supplier.")
    payment_method: PaymentMethod | None = Field(default=None, examples=[PaymentMethod.CHEQUE])
    payment_date_from: date | None = Field(
        default=None, description="Inclusive lower bound on payment_date."
    )
    payment_date_to: date | None = Field(
        default=None, description="Inclusive upper bound on payment_date."
    )
    sort: str = Field(
        default="-created_at",
        description="One of payment_date, payment_number, created_at; prefix with '-' for "
        "descending.",
        examples=["payment_date", "-payment_date"],
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
