import re
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.suppliers.constants import SupplierStatus

# Same structural checks as companies/schemas.py's _EMAIL_RE/_PHONE_RE/
# _GSTIN_RE, duplicated here rather than shared - the two modules' fields
# have no reason to stay in lockstep (boats/schemas.py made the same call
# for its own phone field).
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")
_GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")

_SORTABLE_FIELDS = frozenset({"name", "code", "created_at"})


def _validate_email(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not _EMAIL_RE.match(value):
        raise ValueError("Invalid email address format")
    return value.lower()


def _validate_phone(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not _PHONE_RE.match(value):
        raise ValueError("Phone number must contain 7-15 digits, optionally prefixed with +")
    return value


def _validate_gstin(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().upper()
    if not _GSTIN_RE.match(value):
        raise ValueError("Invalid GSTIN format")
    return value


class SupplierResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "code": "SUP-001",
                "name": "Coastal Fish Suppliers",
                "legal_name": "Coastal Fish Suppliers Pvt Ltd",
                "gstin": "27ABCDE1234F1Z5",
                "phone": "9876543210",
                "email": "contact@coastalfish.example",
                "address": "12 Harbour Road",
                "city": "Mumbai",
                "state": "Maharashtra",
                "country": "India",
                "contact_person": "Ravi Kumar",
                "credit_days": 30,
                "opening_balance": "0.00",
                "outstanding_amount": "0.00",
                "status": "active",
                "created_at": "2026-07-23T04:00:00Z",
                "updated_at": "2026-07-23T04:00:00Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    legal_name: str | None
    gstin: str | None
    phone: str | None
    email: str | None
    address: str | None
    city: str | None
    state: str | None
    country: str | None
    contact_person: str | None
    credit_days: int
    opening_balance: Decimal
    outstanding_amount: Decimal
    status: SupplierStatus
    created_at: datetime
    updated_at: datetime


class SupplierCreateRequest(BaseModel):
    """tenant_id, created_by and updated_by are never client-supplied - the
    router populates them from the authenticated user. `outstanding_amount`
    and `status` are not accepted here at all: the server always owns them
    (SupplierService.create) - outstanding_amount always starts at 0, status
    always ACTIVE (TASKS.md Sprint 11 Session 2: "Server owns:
    outstanding_amount, status")."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "SUP-001",
                "name": "Coastal Fish Suppliers",
                "legal_name": "Coastal Fish Suppliers Pvt Ltd",
                "gstin": "27ABCDE1234F1Z5",
                "phone": "9876543210",
                "email": "contact@coastalfish.example",
                "address": "12 Harbour Road",
                "city": "Mumbai",
                "state": "Maharashtra",
                "country": "India",
                "contact_person": "Ravi Kumar",
                "credit_days": 30,
                "opening_balance": "0.00",
            }
        }
    )

    code: str = Field(min_length=1, max_length=50, examples=["SUP-001"])
    name: str = Field(min_length=1, max_length=255, examples=["Coastal Fish Suppliers"])
    legal_name: str | None = Field(default=None, max_length=255)
    gstin: str | None = Field(default=None, max_length=15, examples=["27ABCDE1234F1Z5"])
    phone: str | None = Field(default=None, max_length=20, examples=["9876543210"])
    email: str | None = Field(default=None, max_length=255, examples=["contact@example.com"])
    address: str | None = None
    city: str | None = Field(default=None, max_length=100, examples=["Mumbai"])
    state: str | None = Field(default=None, max_length=100, examples=["Maharashtra"])
    country: str | None = Field(default=None, max_length=100, examples=["India"])
    contact_person: str | None = Field(default=None, max_length=255)
    credit_days: int = Field(default=0, ge=0)
    opening_balance: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)

    _check_email = field_validator("email")(_validate_email)
    _check_phone = field_validator("phone")(_validate_phone)
    _check_gstin = field_validator("gstin")(_validate_gstin)


class SupplierUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are changed.
    `outstanding_amount`/`status` are not accepted here either, for the same
    reason as SupplierCreateRequest."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "contact_person": "Rakesh Shah",
                "credit_days": 45,
            }
        }
    )

    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    gstin: str | None = Field(default=None, max_length=15)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    contact_person: str | None = Field(default=None, max_length=255)
    credit_days: int | None = Field(default=None, ge=0)
    opening_balance: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)

    _check_email = field_validator("email")(_validate_email)
    _check_phone = field_validator("phone")(_validate_phone)
    _check_gstin = field_validator("gstin")(_validate_gstin)


class SupplierListParams(BaseModel):
    """Query params for GET /suppliers - bound via FastAPI's Depends() model
    support."""

    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across code, name and gstin.",
        examples=["coastal"],
    )
    status: SupplierStatus | None = Field(default=None, examples=[SupplierStatus.ACTIVE])
    city: str | None = Field(default=None, max_length=100, examples=["Mumbai"])
    state: str | None = Field(default=None, max_length=100, examples=["Maharashtra"])
    sort: str = Field(
        default="-created_at",
        description="One of name, code, created_at; prefix with '-' for descending.",
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
