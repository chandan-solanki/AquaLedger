import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Deliberately local copies, not shared imports - same convention
# app/modules/users/schemas.py already follows for its own identical
# regexes (module-local validation, no cross-module regex module exists
# in this codebase).
_PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,100}$")


def _validate_optional_phone(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not _PHONE_RE.match(value):
        raise ValueError("Phone number must contain 7-15 digits, optionally prefixed with +")
    return value


def _validate_optional_username(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not _USERNAME_RE.match(value):
        raise ValueError(
            "Username must be 3-100 characters: letters, numbers, dot, underscore or hyphen"
        )
    return value.lower()


class ProfileUpdateRequest(BaseModel):
    """Partial update of the caller's OWN profile - only fields present in
    the request body are changed. No `email`, `role_id`, `status`,
    `is_superuser`, `id` or `tenant_id` field exists here at all: this is
    not an oversight, those changes are deliberately out of reach through
    this endpoint (Sprint 16 Session 2). `extra="forbid"` turns an attempt
    to slip one in into a 422 rather than a silently-ignored no-op, so the
    schema itself - not just the service - is the enforcement point.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"full_name": "Priya S. Nair", "phone": "9876500000"}},
    )

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    username: str | None = None
    phone: str | None = None

    _check_username = field_validator("username")(_validate_optional_username)
    _check_phone = field_validator("phone")(_validate_optional_phone)
