import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.payments.constants import PaymentMethod, PaymentStatus


class PaymentResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c05",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "company_id": "019f7af3-83ae-783a-b139-40a239786b30",
                "payment_number": None,
                "payment_date": "2026-07-23",
                "payment_method": "cheque",
                "reference_number": "445512",
                "bank_name": "State Bank",
                "amount": "200000.00",
                "allocated_amount": "0.00",
                "unallocated_amount": "200000.00",
                "remarks": "Against pending invoices",
                "status": "draft",
                "created_at": "2026-07-23T04:00:00Z",
                "updated_at": "2026-07-23T04:00:00Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    company_id: uuid.UUID
    payment_number: str | None
    payment_date: date
    payment_method: PaymentMethod
    reference_number: str | None
    bank_name: str | None
    amount: Decimal
    allocated_amount: Decimal
    unallocated_amount: Decimal
    remarks: str | None
    status: PaymentStatus
    created_at: datetime
    updated_at: datetime


class PaymentAllocationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c06",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "payment_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c05",
                "invoice_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c03",
                "allocated_amount": "120000.00",
                "created_at": "2026-07-23T04:05:00Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    payment_id: uuid.UUID
    invoice_id: uuid.UUID
    allocated_amount: Decimal
    created_at: datetime


class PaymentAllocationCreateRequest(BaseModel):
    """tenant_id and created_by are never client-supplied - the router
    populates created_by from the authenticated user; there is no
    updated_by, this row is append-only (see PaymentAllocation's
    docstring). `allocated_amount` is validated against the invoice's
    balance_amount and the payment's unallocated_amount by
    PaymentService.create_allocation
    (app.modules.payments.domain.allocation) - not further bounded here
    beyond being positive."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "invoice_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c03",
                "allocated_amount": "120000.00",
            }
        }
    )

    invoice_id: uuid.UUID = Field(
        description="Target invoice - must exist for this tenant and be ISSUED or PARTIALLY_PAID."
    )
    allocated_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class PaymentAllocationUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are
    changed. The full merged state (invoice_id, allocated_amount) is
    revalidated on every update, regardless of which fields changed - same
    rules as creating an allocation (see
    PaymentService.update_allocation)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "allocated_amount": "150000.00",
            }
        }
    )

    invoice_id: uuid.UUID | None = Field(default=None, description="Reassign the target invoice.")
    allocated_amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)


class PaymentCreateRequest(BaseModel):
    """tenant_id, created_by and updated_by are never client-supplied - the
    router populates them from the authenticated user. `payment_number`,
    `allocated_amount`, `unallocated_amount` and `status` are not accepted
    here at all: the server always owns them (PaymentService.create) -
    number stays NULL until the Session 5 posting workflow, allocated_amount
    starts at 0, unallocated_amount starts equal to `amount`, and status is
    always DRAFT. Same split InvoiceCreateRequest uses for invoices."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "company_id": "019f7af3-83ae-783a-b139-40a239786b30",
                "payment_date": "2026-07-23",
                "payment_method": "cheque",
                "reference_number": "445512",
                "bank_name": "State Bank",
                "amount": "200000.00",
                "remarks": "Against pending invoices",
            }
        }
    )

    company_id: uuid.UUID = Field(
        description="Paying company - must exist for this tenant and be active."
    )
    payment_date: date
    payment_method: PaymentMethod
    reference_number: str | None = Field(default=None, max_length=100)
    bank_name: str | None = Field(default=None, max_length=255)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    remarks: str | None = None


class PaymentUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are changed.
    Only DRAFT payments may be updated (see PaymentService.update).
    `payment_number`/`allocated_amount`/`unallocated_amount`/`status` are
    not accepted here either, for the same reason as PaymentCreateRequest.
    If `amount` changes, `unallocated_amount` is recomputed from it (always
    equal to `amount` in this session - `allocated_amount` stays 0 until the
    Session 3 allocation engine exists)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "amount": "250000.00",
                "remarks": "Revised amount",
            }
        }
    )

    company_id: uuid.UUID | None = Field(
        default=None,
        description="Reassign the paying company - must exist for this tenant and be active.",
    )
    payment_date: date | None = None
    payment_method: PaymentMethod | None = None
    reference_number: str | None = Field(default=None, max_length=100)
    bank_name: str | None = Field(default=None, max_length=255)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    remarks: str | None = None


_SORTABLE_FIELDS = frozenset({"payment_date", "payment_number", "amount", "created_at"})


class PaymentListParams(BaseModel):
    """Query params for GET /payments - bound via FastAPI's Depends() model support."""

    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across payment_number, reference_number and "
        "the paying company's name.",
        examples=["445512"],
    )
    status: PaymentStatus | None = Field(default=None, examples=[PaymentStatus.DRAFT])
    company_id: uuid.UUID | None = Field(default=None, description="Filter by paying company.")
    payment_method: PaymentMethod | None = Field(default=None, examples=[PaymentMethod.CHEQUE])
    payment_date_from: date | None = Field(
        default=None, description="Inclusive lower bound on payment_date."
    )
    payment_date_to: date | None = Field(
        default=None, description="Inclusive upper bound on payment_date."
    )
    sort: str = Field(
        default="-created_at",
        description="One of payment_date, payment_number, amount, created_at; prefix with "
        "'-' for descending.",
        examples=["payment_date", "-amount"],
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
