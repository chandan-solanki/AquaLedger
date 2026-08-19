import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.auth.constants import AccountStatus

# Structural check only - deliberately not pydantic's EmailStr, same call as
# auth/schemas.py and companies/schemas.py (no email-validator dependency).
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,100}$")

_SORTABLE_FIELDS = frozenset({"full_name", "email", "username", "created_at", "last_login_at"})


def _validate_email(value: str) -> str:
    value = value.strip()
    if not _EMAIL_RE.match(value):
        raise ValueError("Invalid email address format")
    return value.lower()


def _validate_optional_email(value: str | None) -> str | None:
    return None if value is None else _validate_email(value)


def _validate_phone(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not _PHONE_RE.match(value):
        raise ValueError("Phone number must contain 7-15 digits, optionally prefixed with +")
    return value


def _validate_username(value: str) -> str:
    value = value.strip()
    if not _USERNAME_RE.match(value):
        raise ValueError(
            "Username must be 3-100 characters: letters, numbers, dot, underscore or hyphen"
        )
    return value.lower()


def _validate_optional_username(value: str | None) -> str | None:
    return None if value is None else _validate_username(value)


class RoleSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None


class UserResponse(BaseModel):
    """password_hash is intentionally never a field here."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "019f9a12-1234-7abc-9def-0123456789ab",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "email": "priya@fisherp.local",
                "username": "priya",
                "full_name": "Priya Nair",
                "phone": "9876543210",
                "status": "active",
                "is_superuser": False,
                "last_login_at": "2026-08-10T09:15:00Z",
                "role": {
                    "id": "019f7af3-9000-7abc-9def-0123456789ab",
                    "name": "accountant",
                    "description": "Financial recording and reporting access",
                },
                "created_at": "2026-08-01T09:48:08.714017Z",
                "updated_at": "2026-08-01T09:48:08.714017Z",
            }
        }
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    username: str
    full_name: str
    phone: str | None
    status: AccountStatus
    is_superuser: bool
    last_login_at: datetime | None
    role: RoleSummary | None
    created_at: datetime
    updated_at: datetime


class UserCreateRequest(BaseModel):
    """tenant_id, is_superuser and password_hash are never client-supplied.

    is_superuser has no field here at all - it is never settable through this
    API (only the seeded super admin has it; ARCHITECTURE.md's privilege
    model treats it as strictly stronger than any role's permission set).
    The account is created with `password` already set and must change it on
    first login - see AuthService._build_token_response's must_change_password
    (password_changed_at is left null by this endpoint on purpose).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "priya@fisherp.local",
                "username": "priya",
                "full_name": "Priya Nair",
                "phone": "9876543210",
                "password": "TempPass@123",
                "role_id": "019f7af3-9000-7abc-9def-0123456789ab",
            }
        }
    )

    email: str = Field(examples=["priya@fisherp.local"])
    username: str = Field(examples=["priya"])
    full_name: str = Field(min_length=1, max_length=255, examples=["Priya Nair"])
    phone: str | None = Field(default=None, max_length=20, examples=["9876543210"])
    password: str = Field(min_length=8, max_length=128, examples=["TempPass@123"])
    role_id: uuid.UUID

    _check_email = field_validator("email")(_validate_email)
    _check_username = field_validator("username")(_validate_username)
    _check_phone = field_validator("phone")(_validate_phone)


class UserUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are changed.

    No password field here - admin-triggered password resets are not
    supported by the existing architecture (only self-service
    /auth/change-password exists); status changes go through
    PATCH /users/{id}/status, not this endpoint.
    """

    model_config = ConfigDict(
        json_schema_extra={"example": {"full_name": "Priya S. Nair", "phone": "9876500000"}}
    )

    email: str | None = Field(default=None, examples=["priya@fisherp.local"])
    username: str | None = Field(default=None, examples=["priya"])
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    role_id: uuid.UUID | None = None

    _check_email = field_validator("email")(_validate_optional_email)
    _check_username = field_validator("username")(_validate_optional_username)
    _check_phone = field_validator("phone")(_validate_phone)


class UserStatusUpdateRequest(BaseModel):
    """Only active/inactive are admin-settable here - locked and
    password_expired are system-managed states driven by login attempts and
    password policy (AuthService), not an administrator action."""

    model_config = ConfigDict(json_schema_extra={"example": {"status": "inactive"}})

    status: Literal[AccountStatus.ACTIVE, AccountStatus.INACTIVE]


class UserListParams(BaseModel):
    """Query params for GET /users - bound via FastAPI's Depends() model support."""

    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across full_name, email and username.",
        examples=["priya"],
    )
    role_id: uuid.UUID | None = None
    status: AccountStatus | None = Field(default=None, examples=[AccountStatus.ACTIVE])
    sort: str = Field(
        default="-created_at",
        description="One of full_name, email, username, created_at, last_login_at; "
        "prefix with '-' for descending.",
        examples=["full_name", "-created_at"],
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
