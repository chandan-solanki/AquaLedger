import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.auth.constants import TenantStatus

# Deliberately local copies, not shared imports - same convention
# app/modules/profile/schemas.py already follows for its own identical
# regexes (module-local validation, no cross-module regex module exists in
# this codebase).
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,100}$")
_SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _validate_email(value: str) -> str:
    value = value.strip()
    if not _EMAIL_RE.match(value):
        raise ValueError("Invalid email address format")
    return value.lower()


def _validate_username(value: str) -> str:
    value = value.strip()
    if not _USERNAME_RE.match(value):
        raise ValueError(
            "Username must be 3-100 characters: letters, numbers, dot, underscore or hyphen"
        )
    return value.lower()


def _validate_slug(value: str) -> str:
    value = value.strip().lower()
    if not _SLUG_RE.match(value) or len(value) > 100:
        raise ValueError(
            "Slug must be lowercase letters, numbers and single hyphens only "
            "(e.g. 'ocean-fresh-traders'), max 100 characters"
        )
    return value


class PlatformAdminProfileResponse(BaseModel):
    """Identity/status proof for GET /platform/me.

    Deliberately minimal (Sprint 17 Session 1): this is the proof that the
    platform-admin authorization boundary works, not the start of a
    cross-tenant business-data API. `tenant_id` is included because a
    platform admin still belongs to a tenant like any other user - there is
    no platform-level identity separate from a tenant user in this design.
    """

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    full_name: str
    is_platform_admin: bool

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "019f7af3-83d5-7723-9cec-97060761aae4",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "email": "admin@fisherp.local",
                "full_name": "Super Admin",
                "is_platform_admin": True,
            }
        }
    )


class TenantResponse(BaseModel):
    """Tenant management summary/detail (Sprint 17 Session 2). Deliberately
    excludes `settings` (arbitrary JSONB, no real use case yet per the
    session's own scope) - id/name/slug/status/plan/currency/fiscal month
    plus timestamps only, never tenant users/invoices/fish/financial data.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    status: TenantStatus
    plan: str | None
    base_currency: str
    fiscal_year_start_month: int
    created_at: datetime
    updated_at: datetime


class TenantAdministratorCreateRequest(BaseModel):
    """The new tenant's first user. Never accepts is_superuser,
    is_platform_admin or a role_id - see TenantService.create_tenant for why
    this account is provisioned with is_superuser=True and the tenant's
    "admin" role, and is_platform_admin=False unconditionally."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "email": "owner@oceanfresh.example",
                "username": "oceanfresh-owner",
                "full_name": "Priya Nair",
                "password": "TempPass@123",
            }
        },
    )

    email: str = Field(examples=["owner@oceanfresh.example"])
    username: str = Field(examples=["oceanfresh-owner"])
    full_name: str = Field(min_length=1, max_length=255, examples=["Priya Nair"])
    password: str = Field(min_length=8, max_length=128, examples=["TempPass@123"])

    _check_email = field_validator("email")(_validate_email)
    _check_username = field_validator("username")(_validate_username)


class TenantCreateRequest(BaseModel):
    """Platform-admin-only tenant provisioning. `extra="forbid"` (matching
    profile.schemas.ProfileUpdateRequest's own precedent) turns any attempt
    to slip in a tenant_id/is_platform_admin/role_id/etc. into a 422 rather
    than a silently-ignored field."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "name": "Ocean Fresh Traders",
                "slug": "ocean-fresh-traders",
                "plan": None,
                "base_currency": "INR",
                "fiscal_year_start_month": 4,
                "administrator": {
                    "email": "owner@oceanfresh.example",
                    "username": "oceanfresh-owner",
                    "full_name": "Priya Nair",
                    "password": "TempPass@123",
                },
            }
        },
    )

    name: str = Field(min_length=1, max_length=255, examples=["Ocean Fresh Traders"])
    slug: str = Field(examples=["ocean-fresh-traders"])
    plan: str | None = Field(default=None, max_length=50)
    base_currency: str = Field(default="INR", min_length=3, max_length=3)
    fiscal_year_start_month: int = Field(default=4, ge=1, le=12)
    administrator: TenantAdministratorCreateRequest

    _check_slug = field_validator("slug")(_validate_slug)


class TenantAdministratorSummary(BaseModel):
    """Never includes password/password_hash - returned once, at creation,
    so the platform admin can hand the initial admin their login email."""

    id: uuid.UUID
    email: str
    username: str
    full_name: str


class TenantProvisioningResponse(BaseModel):
    tenant: TenantResponse
    administrator: TenantAdministratorSummary


class TenantListParams(BaseModel):
    """Query params for GET /platform/tenants - mirrors FishListParams'
    q/page/page_size shape (app/modules/fish/schemas.py)."""

    q: str | None = Field(default=None, max_length=255, examples=["ocean"])
    status: TenantStatus | None = Field(default=None, examples=[TenantStatus.ACTIVE])
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class TenantStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid", json_schema_extra={"example": {"status": "suspended"}}
    )

    status: TenantStatus


class PlatformDashboardResponse(BaseModel):
    """GET /platform/dashboard - a platform admin's landing summary (Sprint
    17 Session 5). Deliberately limited to real tenant lifecycle metadata
    already served by GET /platform/tenants: counts by status and the most
    recently provisioned tenants. No cross-tenant business data, billing or
    analytics of any kind - see this module's own docstring."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_tenants": 12,
                "active_tenants": 10,
                "suspended_tenants": 1,
                "inactive_tenants": 1,
                "recent_tenants": [
                    {
                        "id": "019f7af3-83d5-7723-9cec-97060761aae4",
                        "name": "Ocean Fresh Traders",
                        "slug": "ocean-fresh-traders",
                        "status": "active",
                        "plan": None,
                        "base_currency": "INR",
                        "fiscal_year_start_month": 4,
                        "created_at": "2026-08-22T00:00:00Z",
                        "updated_at": "2026-08-22T00:00:00Z",
                    }
                ],
            }
        }
    )

    total_tenants: int
    active_tenants: int
    suspended_tenants: int
    inactive_tenants: int
    recent_tenants: list[TenantResponse]
