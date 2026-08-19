import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.auth.constants import AccountStatus


class PermissionSummary(BaseModel):
    """Global reference data (Permission is not tenant-scoped, see
    app/modules/auth/models.py) - the same set is returned regardless of
    the caller's tenant."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    resource: str
    action: str
    description: str | None


class RoleUserSummary(BaseModel):
    """A user holding a role - no password/hash fields, mirrors the
    subset of UserResponse (app/modules/users/schemas.py) safe to embed here."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    status: AccountStatus


class RoleListItem(BaseModel):
    """One row of GET /roles - counts only, no permission/user detail (that's
    GET /roles/{id})."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "019f7af3-9000-7abc-9def-0123456789ab",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "name": "accountant",
                "description": "Financial recording and reporting access",
                "is_system": True,
                "user_count": 2,
                "permission_count": 19,
                "created_at": "2026-07-19T20:42:55.230287Z",
                "updated_at": "2026-07-19T20:42:55.230287Z",
            }
        }
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
    user_count: int
    permission_count: int
    created_at: datetime
    updated_at: datetime


class RoleDetailResponse(BaseModel):
    """GET /roles/{id} - read-only: the full permission set this role
    grants, grouped by `resource` on the client, plus every user currently
    holding it. There is no PUT/PATCH counterpart in this module - see the
    router's module docstring for why."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "019f7af3-9000-7abc-9def-0123456789ab",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "name": "accountant",
                "description": "Financial recording and reporting access",
                "is_system": True,
                "permissions": [
                    {
                        "id": "019f7af3-8000-7abc-9def-0123456789ab",
                        "code": "invoice:view",
                        "resource": "invoice",
                        "action": "view",
                        "description": "View invoices",
                    }
                ],
                "users": [
                    {
                        "id": "019f7af3-83d5-7723-9cec-97060761aae4",
                        "full_name": "Priya Nair",
                        "email": "priya@fisherp.local",
                        "status": "active",
                    }
                ],
                "created_at": "2026-07-19T20:42:55.230287Z",
                "updated_at": "2026-07-19T20:42:55.230287Z",
            }
        }
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
    permissions: list[PermissionSummary]
    users: list[RoleUserSummary]
    created_at: datetime
    updated_at: datetime
