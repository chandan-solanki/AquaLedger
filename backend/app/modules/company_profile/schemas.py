import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Same structural checks as app.modules.companies.schemas (duplicated
# rather than imported - the two modules' fields legitimately diverge
# and no shared regex module exists in this codebase, e.g. suppliers'
# schemas.py makes the identical call for the identical reason).
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")
_GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
# Indian PAN: 5 letters, 4 digits, 1 checksum letter. Not validated on
# Company/Supplier today (those declare the column but never check its
# format) - this is a new, module-local validator.
_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


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


def _validate_pan(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().upper()
    if not _PAN_RE.match(value):
        raise ValueError("Invalid PAN format")
    return value


class CompanyProfileResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c07",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "legal_name": "Ocean Fresh Seafoods Pvt Ltd",
                "display_name": "Ocean Fresh Seafoods",
                "company_code": "OFS",
                "address_line1": "12 Harbour Road",
                "address_line2": None,
                "city": "Mumbai",
                "state": "Maharashtra",
                "state_code": "27",
                "pincode": "400001",
                "country": "India",
                "phone": "9876543210",
                "alt_phone": None,
                "email": "info@oceanfresh.example",
                "website": "https://oceanfresh.example",
                "gstin": "27ABCDE1234F1Z5",
                "pan": "ABCDE1234F",
                "logo_url": "/company-profile/logo",
                "created_at": "2026-08-16T09:00:00Z",
                "updated_at": "2026-08-16T09:00:00Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    legal_name: str
    display_name: str | None
    company_code: str | None
    address_line1: str | None
    address_line2: str | None
    city: str | None
    state: str | None
    state_code: str | None
    pincode: str | None
    country: str | None
    phone: str | None
    alt_phone: str | None
    email: str | None
    website: str | None
    gstin: str | None
    pan: str | None
    logo_url: str | None = None
    created_at: datetime
    updated_at: datetime


class CompanyProfileUpsertRequest(BaseModel):
    """The one editable shape for this single-row-per-tenant resource -
    no separate Create/Update split, since there is never more than one
    row to create. Partial update semantics: only fields present in the
    request body are changed (CompanyProfileService.upsert applies
    `exclude_unset`)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "legal_name": "Ocean Fresh Seafoods Pvt Ltd",
                "display_name": "Ocean Fresh Seafoods",
                "gstin": "27ABCDE1234F1Z5",
                "pan": "ABCDE1234F",
                "phone": "9876543210",
                "email": "info@oceanfresh.example",
                "address_line1": "12 Harbour Road",
                "city": "Mumbai",
                "state": "Maharashtra",
                "state_code": "27",
                "pincode": "400001",
                "country": "India",
            }
        }
    )

    legal_name: str | None = Field(default=None, min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    company_code: str | None = Field(default=None, max_length=50)
    address_line1: str | None = Field(default=None, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    state_code: str | None = Field(default=None, max_length=2)
    pincode: str | None = Field(default=None, max_length=10)
    country: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    alt_phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=255)
    gstin: str | None = Field(default=None, max_length=15)
    pan: str | None = Field(default=None, max_length=10)

    _check_email = field_validator("email")(_validate_email)
    _check_phone = field_validator("phone", "alt_phone")(_validate_phone)
    _check_gstin = field_validator("gstin")(_validate_gstin)
    _check_pan = field_validator("pan")(_validate_pan)
