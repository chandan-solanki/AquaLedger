"""Roles & Permissions administration - Sprint 14 Session 4.

Deliberately read-only: there is no POST/PUT/PATCH here to assign or
revoke a role's permissions. Reasons, per the session's own audit:

1. Every role seeded today (super_admin, admin, manager, accountant,
   operator) is `is_system=True` - the architecture has no concept yet of
   an admin-created custom role, so there is nothing to safely "edit" that
   isn't one of the five roles the whole permission matrix
   (ARCHITECTURE.md Sec 9.2) is built around.
2. No repository/service helper for mutating `role_permissions` exists
   anywhere in the codebase to build on - adding one now, with the
   necessary guardrails (a mis-click can't silently strip `user:manage`
   from every admin-capable role and lock out administration, or hand
   `settings:manage` to `operator`), is a new safety-critical feature in
   its own right, not a small addition.
3. `require_permission` reads permissions from the JWT (`permissions.py`'s
   documented trade-off) - even a correctly-guarded edit wouldn't take
   effect for an already-logged-in holder of that role until their access
   token expires, which the UI would need to communicate honestly.

ARCHITECTURE.md Sec 9.1 ("roles are a bundling convenience that admins can
edit") states that as an eventual intent, not a currently-implemented
capability - this module lets an administrator see exactly what each role
grants and who holds it, which is the prerequisite for building that
safely later, without inventing a half-finished mutation path now.

Reuses `user:manage` (app/modules/users/constants.py) - the same
permission code that already gates the Administration -> Roles & Permissions
nav entry (frontend navigation.ts) and the Users module beside it. No new
permission code was needed.
"""

import uuid

from fastapi import APIRouter, Depends

from app.common.schemas import ErrorResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.roles.dependencies import get_role_service
from app.modules.roles.schemas import PermissionSummary, RoleDetailResponse, RoleListItem
from app.modules.roles.service import RoleService
from app.modules.users.constants import USER_MANAGE_PERMISSION

router = APIRouter(prefix="/roles", tags=["roles"])

_COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Missing required permission"},
}
_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {"model": ErrorResponse, "description": "Role not found"},
}

# Registered before "/{role_id}" - a static path always takes precedence
# over a uuid-typed path parameter, but keeping it first in file order too
# avoids relying on that (same convention as users/router.py's "/roles").


@router.get(
    "/permissions",
    response_model=list[PermissionSummary],
    summary="List every permission in the system",
    description=(
        "Global reference data (Permission is not tenant-scoped) - the same "
        "set for every tenant. Grouping by `resource` for display is a "
        "client-side concern; this returns a flat list sorted by resource, action."
    ),
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_permission(USER_MANAGE_PERMISSION))],
)
async def list_permissions(
    service: RoleService = Depends(get_role_service),
) -> list[PermissionSummary]:
    return await service.list_permissions()


@router.get(
    "",
    response_model=list[RoleListItem],
    summary="List roles for the caller's tenant, with user/permission counts",
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_permission(USER_MANAGE_PERMISSION))],
)
async def list_roles(
    current_user: User = Depends(get_current_user),
    service: RoleService = Depends(get_role_service),
) -> list[RoleListItem]:
    return await service.list_roles(tenant_id=current_user.tenant_id)


@router.get(
    "/{role_id}",
    response_model=RoleDetailResponse,
    summary="Get a role's full permission set and current members",
    description="A role belonging to another tenant is treated as not found, never leaked.",
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission(USER_MANAGE_PERMISSION))],
)
async def get_role(
    role_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: RoleService = Depends(get_role_service),
) -> RoleDetailResponse:
    return await service.get_role_detail(role_id, tenant_id=current_user.tenant_id)
