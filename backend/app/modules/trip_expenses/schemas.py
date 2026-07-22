import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.trip_expenses.constants import ExpenseType


class TripExpenseResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c02",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "trip_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c02",
                "expense_type": "diesel",
                "amount": "4500.00",
                "expense_date": "2026-07-22",
                "description": "Diesel refill before departure",
                "vendor_name": "Sassoon Dock Fuel Co",
                "receipt_number": "RCPT-1042",
                "created_at": "2026-07-22T04:00:00Z",
                "updated_at": "2026-07-22T04:00:00Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    trip_id: uuid.UUID
    expense_type: ExpenseType
    amount: Decimal
    expense_date: date
    description: str | None
    vendor_name: str | None
    receipt_number: str | None
    created_at: datetime
    updated_at: datetime


class TripExpenseCreateRequest(BaseModel):
    """tenant_id, created_by and updated_by are never client-supplied - the
    router populates them from the authenticated user. trip_id must exist for
    this tenant, must not be CANCELLED, and expense_date must fall within
    [trip.departure_datetime, trip.actual_return_datetime] (no upper bound if
    the trip hasn't returned yet) - see TripExpenseService."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trip_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c02",
                "expense_type": "diesel",
                "amount": "4500.00",
                "expense_date": "2026-07-22",
                "description": "Diesel refill before departure",
                "vendor_name": "Sassoon Dock Fuel Co",
                "receipt_number": "RCPT-1042",
            }
        }
    )

    trip_id: uuid.UUID = Field(
        description="Owning trip - must exist for this tenant and not be cancelled."
    )
    expense_type: ExpenseType
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    expense_date: date
    description: str | None = None
    vendor_name: str | None = Field(default=None, max_length=255)
    receipt_number: str | None = Field(default=None, max_length=100)


class TripExpenseUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are changed.
    If trip_id and/or expense_date are included, the resulting pair (merged
    with the record's current values) is re-validated against the owning
    trip's window/status the same way create() is."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "amount": "4800.00",
                "receipt_number": "RCPT-1042-A",
            }
        }
    )

    trip_id: uuid.UUID | None = Field(
        default=None,
        description="Reassign the owning trip - must exist for this tenant and not be cancelled.",
    )
    expense_type: ExpenseType | None = None
    amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    expense_date: date | None = None
    description: str | None = None
    vendor_name: str | None = Field(default=None, max_length=255)
    receipt_number: str | None = Field(default=None, max_length=100)


_SORTABLE_FIELDS = frozenset({"expense_date", "amount", "created_at"})


class TripExpenseListParams(BaseModel):
    """Query params for GET /trip-expenses - bound via FastAPI's Depends() model support."""

    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across vendor_name and receipt_number.",
        examples=["Sassoon Dock"],
    )
    trip_id: uuid.UUID | None = Field(default=None, description="Filter by trip.")
    expense_type: ExpenseType | None = Field(default=None, examples=[ExpenseType.DIESEL])
    expense_date_from: date | None = Field(
        default=None, description="Inclusive lower bound on expense_date."
    )
    expense_date_to: date | None = Field(
        default=None, description="Inclusive upper bound on expense_date."
    )
    sort: str = Field(
        default="-created_at",
        description="One of expense_date, amount, created_at; prefix with '-' for descending.",
        examples=["expense_date", "-amount"],
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
