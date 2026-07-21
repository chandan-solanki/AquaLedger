import re
import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Same structural check as companies/schemas.py's _PHONE_RE, duplicated here
# rather than shared - the two modules' phone fields have no reason to stay
# in lockstep.
_PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")


def _validate_phone(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not _PHONE_RE.match(value):
        raise ValueError("Phone number must contain 7-15 digits, optionally prefixed with +")
    return value


class BoatResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "company_id": "019f7af3-9c1e-73aa-9c2e-2a6a6e6a6a6a",
                "code": "BOAT-001",
                "name": "Sea Falcon",
                "registration_number": "MH-01-AB-1234",
                "license_number": "LIC-9988",
                "boat_type": "trawler",
                "capacity_kg": "12000.000",
                "engine_number": "ENG-4521",
                "engine_hp": 180,
                "captain_name": "Suresh Patil",
                "captain_phone": "9876543210",
                "insurance_expiry": "2027-03-31",
                "license_expiry": "2027-01-15",
                "notes": None,
                "is_active": True,
                "created_at": "2026-07-21T09:48:08.714017Z",
                "updated_at": "2026-07-21T09:48:08.714017Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    company_id: uuid.UUID
    code: str
    name: str
    registration_number: str
    license_number: str | None
    boat_type: str | None
    capacity_kg: Decimal | None
    engine_number: str | None
    engine_hp: int | None
    captain_name: str | None
    captain_phone: str | None
    insurance_expiry: date | None
    license_expiry: date | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BoatCreateRequest(BaseModel):
    """tenant_id, created_by and updated_by are never client-supplied - the
    router populates them from the authenticated user."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "company_id": "019f7af3-9c1e-73aa-9c2e-2a6a6e6a6a6a",
                "code": "BOAT-001",
                "name": "Sea Falcon",
                "registration_number": "MH-01-AB-1234",
                "license_number": "LIC-9988",
                "boat_type": "trawler",
                "capacity_kg": "12000.000",
                "engine_number": "ENG-4521",
                "engine_hp": 180,
                "captain_name": "Suresh Patil",
                "captain_phone": "9876543210",
                "insurance_expiry": "2027-03-31",
                "license_expiry": "2027-01-15",
            }
        }
    )

    company_id: uuid.UUID = Field(description="Owning company - must exist for this tenant.")
    code: str = Field(
        min_length=1, max_length=50, examples=["BOAT-001"], description="Unique per tenant."
    )
    name: str = Field(min_length=1, max_length=255, examples=["Sea Falcon"])
    registration_number: str = Field(
        min_length=1,
        max_length=50,
        examples=["MH-01-AB-1234"],
        description="Unique per tenant.",
    )
    license_number: str | None = Field(default=None, max_length=50)
    boat_type: str | None = Field(default=None, max_length=50, examples=["trawler"])
    capacity_kg: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=3, examples=["12000.000"]
    )
    engine_number: str | None = Field(default=None, max_length=50)
    engine_hp: int | None = Field(default=None, ge=0)
    captain_name: str | None = Field(default=None, max_length=255)
    captain_phone: str | None = Field(default=None, max_length=20, examples=["9876543210"])
    insurance_expiry: date | None = None
    license_expiry: date | None = None
    notes: str | None = None
    is_active: bool = True

    _check_captain_phone = field_validator("captain_phone")(_validate_phone)


class BoatUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are changed."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "captain_name": "Ramesh Yadav",
                "captain_phone": "9876500011",
            }
        }
    )

    company_id: uuid.UUID | None = Field(
        default=None, description="Reassign the owning company - must exist for this tenant."
    )
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    registration_number: str | None = Field(default=None, min_length=1, max_length=50)
    license_number: str | None = Field(default=None, max_length=50)
    boat_type: str | None = Field(default=None, max_length=50)
    capacity_kg: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=3)
    engine_number: str | None = Field(default=None, max_length=50)
    engine_hp: int | None = Field(default=None, ge=0)
    captain_name: str | None = Field(default=None, max_length=255)
    captain_phone: str | None = Field(default=None, max_length=20)
    insurance_expiry: date | None = None
    license_expiry: date | None = None
    notes: str | None = None
    is_active: bool | None = None

    _check_captain_phone = field_validator("captain_phone")(_validate_phone)


_SORTABLE_FIELDS = frozenset({"name", "code", "created_at", "updated_at"})


class BoatListParams(BaseModel):
    """Query params for GET /boats - bound via FastAPI's Depends() model support."""

    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across name, code, registration_number "
        "and captain_name.",
        examples=["falcon"],
    )
    boat_type: str | None = Field(default=None, max_length=50, examples=["trawler"])
    company_id: uuid.UUID | None = Field(default=None, description="Filter by owning company.")
    is_active: bool | None = Field(default=None, examples=[True])
    insurance_expired: bool | None = Field(
        default=None,
        description="True: insurance_expiry is set and in the past. False: not set or "
        "not yet expired.",
    )
    license_expired: bool | None = Field(
        default=None,
        description="True: license_expiry is set and in the past. False: not set or "
        "not yet expired.",
    )
    sort: str = Field(
        default="-created_at",
        description="One of name, code, created_at, updated_at; prefix with '-' for descending.",
        examples=["name", "-created_at"],
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
