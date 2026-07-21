import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.trips.constants import TripStatus, TripType


class TripResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c02",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "boat_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
                "trip_number": "TRIP-2026-001",
                "trip_type": "fishing",
                "captain_name": "Suresh Patil",
                "departure_port": "Sassoon Dock",
                "arrival_port": None,
                "departure_datetime": "2026-07-22T04:30:00Z",
                "expected_return_datetime": "2026-07-25T18:00:00Z",
                "actual_return_datetime": None,
                "status": "planned",
                "notes": None,
                "is_active": True,
                "created_at": "2026-07-22T04:00:00Z",
                "updated_at": "2026-07-22T04:00:00Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    boat_id: uuid.UUID
    trip_number: str
    trip_type: TripType
    captain_name: str | None
    departure_port: str | None
    arrival_port: str | None
    departure_datetime: datetime
    expected_return_datetime: datetime | None
    actual_return_datetime: datetime | None
    status: TripStatus
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TripCreateRequest(BaseModel):
    """tenant_id, created_by and updated_by are never client-supplied - the
    router populates them from the authenticated user."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "boat_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
                "trip_number": "TRIP-2026-001",
                "trip_type": "fishing",
                "captain_name": "Suresh Patil",
                "departure_port": "Sassoon Dock",
                "departure_datetime": "2026-07-22T04:30:00Z",
                "expected_return_datetime": "2026-07-25T18:00:00Z",
            }
        }
    )

    boat_id: uuid.UUID = Field(description="Owning boat - must exist for this tenant.")
    trip_number: str = Field(
        min_length=1, max_length=50, examples=["TRIP-2026-001"], description="Unique per tenant."
    )
    trip_type: TripType = Field(examples=[TripType.FISHING])
    captain_name: str | None = Field(default=None, max_length=255)
    departure_port: str | None = Field(default=None, max_length=100)
    arrival_port: str | None = Field(default=None, max_length=100)
    departure_datetime: datetime
    expected_return_datetime: datetime | None = None
    actual_return_datetime: datetime | None = None
    status: TripStatus = TripStatus.PLANNED
    notes: str | None = None
    is_active: bool = True


class TripUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are changed."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "departed",
                "actual_return_datetime": None,
            }
        }
    )

    boat_id: uuid.UUID | None = Field(
        default=None, description="Reassign the owning boat - must exist for this tenant."
    )
    trip_number: str | None = Field(default=None, min_length=1, max_length=50)
    trip_type: TripType | None = None
    captain_name: str | None = Field(default=None, max_length=255)
    departure_port: str | None = Field(default=None, max_length=100)
    arrival_port: str | None = Field(default=None, max_length=100)
    departure_datetime: datetime | None = None
    expected_return_datetime: datetime | None = None
    actual_return_datetime: datetime | None = None
    status: TripStatus | None = None
    notes: str | None = None
    is_active: bool | None = None


_SORTABLE_FIELDS = frozenset({"trip_number", "departure_datetime", "created_at", "updated_at"})


class TripListParams(BaseModel):
    """Query params for GET /trips - bound via FastAPI's Depends() model support."""

    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across trip_number, boat name and captain_name.",
        examples=["TRIP-2026"],
    )
    boat_id: uuid.UUID | None = Field(default=None, description="Filter by boat.")
    status: TripStatus | None = Field(default=None, examples=[TripStatus.PLANNED])
    trip_type: TripType | None = Field(default=None, examples=[TripType.FISHING])
    departure_date_from: date | None = Field(
        default=None, description="Inclusive lower bound on departure_datetime's date."
    )
    departure_date_to: date | None = Field(
        default=None, description="Inclusive upper bound on departure_datetime's date."
    )
    return_date_from: date | None = Field(
        default=None, description="Inclusive lower bound on actual_return_datetime's date."
    )
    return_date_to: date | None = Field(
        default=None, description="Inclusive upper bound on actual_return_datetime's date."
    )
    sort: str = Field(
        default="-created_at",
        description="One of trip_number, departure_datetime, created_at, updated_at; "
        "prefix with '-' for descending.",
        examples=["trip_number", "-departure_datetime"],
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
