import re
import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.companies.constants import CompanyStatus, CompanyType, OpeningBalanceType

# Structural check only, deliberately not pydantic's EmailStr - that needs the
# email-validator extra, which isn't a project dependency (auth/schemas.py made
# the same call for the same reason).
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")
# Indian GSTIN: 2-digit state code + 10-char PAN + 1 entity code + 'Z' + 1 checksum char.
_GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")

_SORTABLE_FIELDS = frozenset({"name", "code", "created_at", "updated_at"})


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


class CompanyResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "code": "CUST-001",
                "name": "Ocean Fresh Traders",
                "legal_name": "Ocean Fresh Traders Pvt Ltd",
                "gstin": "27ABCDE1234F1Z5",
                "pan": "ABCDE1234F",
                "address_line1": "12 Harbour Road",
                "address_line2": None,
                "city": "Mumbai",
                "state": "Maharashtra",
                "state_code": "27",
                "pincode": "400001",
                "country": "India",
                "phone": "9876543210",
                "alt_phone": None,
                "email": "contact@oceanfresh.example",
                "contact_person": "Ravi Kumar",
                "company_type": "customer",
                "credit_limit": "500000.00",
                "credit_days": 30,
                "opening_balance": "0.00",
                "opening_balance_date": None,
                "opening_balance_type": None,
                "outstanding_amount": "0.00",
                "status": "active",
                "notes": None,
                "created_at": "2026-07-20T09:48:08.714017Z",
                "updated_at": "2026-07-20T09:48:08.714017Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    legal_name: str | None
    gstin: str | None
    pan: str | None
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
    contact_person: str | None
    company_type: CompanyType
    credit_limit: Decimal
    credit_days: int
    opening_balance: Decimal
    opening_balance_date: date | None
    opening_balance_type: OpeningBalanceType | None
    outstanding_amount: Decimal
    status: CompanyStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CompanyCreateRequest(BaseModel):
    """tenant_id, created_by and updated_by are never client-supplied - the
    router populates them from the authenticated user."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "CUST-001",
                "name": "Ocean Fresh Traders",
                "legal_name": "Ocean Fresh Traders Pvt Ltd",
                "gstin": "27ABCDE1234F1Z5",
                "pan": "ABCDE1234F",
                "address_line1": "12 Harbour Road",
                "city": "Mumbai",
                "state": "Maharashtra",
                "state_code": "27",
                "pincode": "400001",
                "country": "India",
                "phone": "9876543210",
                "email": "contact@oceanfresh.example",
                "contact_person": "Ravi Kumar",
                "company_type": "customer",
                "credit_limit": "500000.00",
                "credit_days": 30,
            }
        }
    )

    code: str = Field(min_length=1, max_length=50, examples=["CUST-001"])
    name: str = Field(min_length=1, max_length=255, examples=["Ocean Fresh Traders"])
    legal_name: str | None = Field(default=None, max_length=255)
    gstin: str | None = Field(default=None, max_length=15, examples=["27ABCDE1234F1Z5"])
    pan: str | None = Field(default=None, max_length=10)
    address_line1: str | None = Field(default=None, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100, examples=["Mumbai"])
    state: str | None = Field(default=None, max_length=100, examples=["Maharashtra"])
    state_code: str | None = Field(default=None, max_length=2)
    pincode: str | None = Field(default=None, max_length=10)
    country: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=20, examples=["9876543210"])
    alt_phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255, examples=["buyer@example.com"])
    contact_person: str | None = Field(default=None, max_length=255)
    company_type: CompanyType = Field(examples=[CompanyType.CUSTOMER])
    credit_limit: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    credit_days: int = Field(default=0, ge=0)
    opening_balance: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    opening_balance_date: date | None = None
    opening_balance_type: OpeningBalanceType | None = None
    status: CompanyStatus = CompanyStatus.ACTIVE
    notes: str | None = None

    _check_email = field_validator("email")(_validate_email)
    _check_phone = field_validator("phone", "alt_phone")(_validate_phone)
    _check_gstin = field_validator("gstin")(_validate_gstin)


class CompanyUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are changed."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "credit_limit": "750000.00",
                "contact_person": "Rakesh Shah",
            }
        }
    )

    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    gstin: str | None = Field(default=None, max_length=15)
    pan: str | None = Field(default=None, max_length=10)
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
    contact_person: str | None = Field(default=None, max_length=255)
    company_type: CompanyType | None = None
    credit_limit: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    credit_days: int | None = Field(default=None, ge=0)
    opening_balance: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    opening_balance_date: date | None = None
    opening_balance_type: OpeningBalanceType | None = None
    status: CompanyStatus | None = None
    notes: str | None = None

    _check_email = field_validator("email")(_validate_email)
    _check_phone = field_validator("phone", "alt_phone")(_validate_phone)
    _check_gstin = field_validator("gstin")(_validate_gstin)


class CompanyListParams(BaseModel):
    """Query params for GET /companies - bound via FastAPI's Depends() model support."""

    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across name, code, contact_person, phone, "
        "email and gstin.",
        examples=["ocean"],
    )
    company_type: CompanyType | None = Field(default=None, examples=[CompanyType.CUSTOMER])
    status: CompanyStatus | None = Field(default=None, examples=[CompanyStatus.ACTIVE])
    city: str | None = Field(default=None, max_length=100, examples=["Mumbai"])
    state: str | None = Field(default=None, max_length=100, examples=["Maharashtra"])
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
