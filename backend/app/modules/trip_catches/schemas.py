import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.trip_catches.constants import CatchGrade


class TripCatchResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c02",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "trip_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c02",
                "fish_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
                "grade": "A",
                "quantity_caught": "120.500",
                "available_quantity": "120.500",
                "sold_quantity": "0.000",
                "waste_quantity": "0.000",
                "landing_date": "2026-07-22",
                "landing_port": "Sassoon Dock",
                "remarks": None,
                "created_at": "2026-07-22T04:00:00Z",
                "updated_at": "2026-07-22T04:00:00Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    trip_id: uuid.UUID
    fish_id: uuid.UUID
    grade: CatchGrade | None
    quantity_caught: Decimal
    available_quantity: Decimal
    sold_quantity: Decimal
    waste_quantity: Decimal
    landing_date: date
    landing_port: str | None
    remarks: str | None
    created_at: datetime
    updated_at: datetime


class TripCatchCreateRequest(BaseModel):
    """tenant_id, created_by and updated_by are never client-supplied - the
    router populates them from the authenticated user. available_quantity/
    sold_quantity/waste_quantity are not accepted here at all - the Session 3
    business rule fixes them to quantity_caught/0/0 at creation time, so
    exposing them as inputs would just let a client silently violate its own
    invariant on the very first write."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trip_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c02",
                "fish_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
                "grade": "A",
                "quantity_caught": "120.500",
                "landing_date": "2026-07-22",
                "landing_port": "Sassoon Dock",
            }
        }
    )

    trip_id: uuid.UUID = Field(
        description="Owning trip - must exist for this tenant and be RETURNED."
    )
    fish_id: uuid.UUID = Field(description="Caught fish - must exist for this tenant.")
    grade: CatchGrade | None = None
    quantity_caught: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    landing_date: date
    landing_port: str | None = Field(default=None, max_length=100)
    remarks: str | None = None


class TripCatchUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are changed.
    If any of quantity_caught/available_quantity/sold_quantity/waste_quantity
    are included, the resulting set (merged with the record's current
    values) must still satisfy available + sold + waste == quantity_caught."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sold_quantity": "40.000",
                "available_quantity": "80.500",
                "remarks": "Partial sale to Company A",
            }
        }
    )

    trip_id: uuid.UUID | None = Field(
        default=None,
        description="Reassign the owning trip - must exist for this tenant and be RETURNED.",
    )
    fish_id: uuid.UUID | None = Field(
        default=None, description="Reassign the fish - must exist for this tenant."
    )
    grade: CatchGrade | None = None
    quantity_caught: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3)
    available_quantity: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=3)
    sold_quantity: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=3)
    waste_quantity: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=3)
    landing_date: date | None = None
    landing_port: str | None = Field(default=None, max_length=100)
    remarks: str | None = None


_SORTABLE_FIELDS = frozenset({"landing_date", "quantity_caught", "created_at"})


class TripCatchListParams(BaseModel):
    """Query params for GET /trip-catches - bound via FastAPI's Depends() model support."""

    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across the trip's trip_number and the fish's name.",
        examples=["TRIP-2026"],
    )
    trip_id: uuid.UUID | None = Field(default=None, description="Filter by trip.")
    fish_id: uuid.UUID | None = Field(default=None, description="Filter by fish.")
    grade: CatchGrade | None = Field(default=None, examples=[CatchGrade.A])
    landing_date_from: date | None = Field(
        default=None, description="Inclusive lower bound on landing_date."
    )
    landing_date_to: date | None = Field(
        default=None, description="Inclusive upper bound on landing_date."
    )
    sort: str = Field(
        default="-created_at",
        description="One of landing_date, quantity_caught, created_at; "
        "prefix with '-' for descending.",
        examples=["landing_date", "-quantity_caught"],
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
