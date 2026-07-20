import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.auth.constants import AccountStatus

# Structural check only (local-part@domain.tld) - deliberately not using
# pydantic's EmailStr/email-validator here: it rejects .local as a reserved
# TLD (RFC 6762), but the seeded super admin intentionally uses
# admin@fisherp.local (ARCHITECTURE §5.2 / TASKS.md), an internal account
# with no real mailbox, so deliverability-oriented checks don't apply.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AccessTokenPayload(BaseModel):
    sub: uuid.UUID
    tenant_id: uuid.UUID
    roles: list[str]
    permissions: list[str]
    jti: uuid.UUID
    iat: int
    exp: int


class LoginRequest(BaseModel):
    email: str = Field(examples=["admin@fisherp.local"])
    password: str = Field(min_length=1, examples=["Admin@123"])

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        value = value.strip()
        if not _EMAIL_RE.match(value):
            raise ValueError("Invalid email address format")
        return value.lower()


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1, examples=["v1.Mn7k...opaque-refresh-token...9fQ"])


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, examples=["Admin@123"])
    new_password: str = Field(min_length=8, examples=["NewStrong@1"])


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    username: str
    full_name: str
    phone: str | None
    status: AccountStatus
    is_superuser: bool
    last_login_at: datetime | None
    roles: list[str]
    permissions: list[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "019f7af3-83d5-7723-9cec-97060761aae4",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "email": "admin@fisherp.local",
                "username": "admin",
                "full_name": "Super Admin",
                "phone": None,
                "status": "active",
                "is_superuser": True,
                "last_login_at": "2026-07-19T17:28:35.848386Z",
                "roles": ["super_admin"],
                "permissions": ["audit_log:view", "invoice:issue", "user:manage"],
            }
        }
    )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth2 token type label, not a credential
    expires_in: int = Field(description="Access token lifetime in seconds")
    must_change_password: bool
    user: UserProfileResponse

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "v1.Mn7k...opaque-refresh-token...9fQ",
                "token_type": "bearer",
                "expires_in": 900,
                "must_change_password": True,
                "user": {
                    "id": "019f7af3-83d5-7723-9cec-97060761aae4",
                    "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                    "email": "admin@fisherp.local",
                    "username": "admin",
                    "full_name": "Super Admin",
                    "phone": None,
                    "status": "active",
                    "is_superuser": True,
                    "last_login_at": "2026-07-19T17:28:35.848386Z",
                    "roles": ["super_admin"],
                    "permissions": ["audit_log:view", "invoice:issue", "user:manage"],
                },
            }
        }
    )
