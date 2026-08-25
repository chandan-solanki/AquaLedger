"""Platform administration - Sprint 17 Session 1 (authorization boundary)
and Session 2 (tenant provisioning/lifecycle).

This module exists to prove and use the platform-admin authorization
boundary established by require_platform_admin()
(app/modules/auth/permissions.py), not to expose cross-tenant business
data. Per Session 1/2's own audits: tenant switching, cross-tenant
dashboards, impersonation, billing and tenant deletion are explicitly out
of scope and are not built here or anywhere else in this codebase.
Creating/listing/suspending a tenant has no effect on how any ordinary
tenant-scoped endpoint (fish, boats, invoices, ...) filters its own
queries - see TenantService's own docstring.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.common.request_context import build_request_context
from app.common.schemas import ErrorResponse, PaginatedResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_platform_admin
from app.modules.platform_admin.dependencies import get_tenant_service
from app.modules.platform_admin.schemas import (
    PlatformAdminProfileResponse,
    PlatformDashboardResponse,
    TenantAdministratorPasswordResetRequest,
    TenantAdministratorResponse,
    TenantCreateRequest,
    TenantListParams,
    TenantProvisioningResponse,
    TenantResponse,
    TenantStatusUpdateRequest,
)
from app.modules.platform_admin.service import TenantService

router = APIRouter(prefix="/platform", tags=["platform-admin"])

_COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Caller is not a platform administrator"},
}
_TENANT_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {"model": ErrorResponse, "description": "Tenant not found"},
}


@router.get(
    "/me",
    response_model=PlatformAdminProfileResponse,
    summary="Prove platform-administration identity/authority",
    description=(
        "Returns the caller's own identity only if they hold platform-admin "
        "authority. A normal user or an ordinary tenant superuser both "
        "receive 403 here - is_superuser never satisfies this check."
    ),
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_platform_admin)],
)
async def get_platform_me(
    current_user: User = Depends(get_current_user),
) -> PlatformAdminProfileResponse:
    return PlatformAdminProfileResponse(
        id=current_user.id,
        tenant_id=current_user.tenant_id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_platform_admin=current_user.is_platform_admin,
    )


@router.get(
    "/dashboard",
    response_model=PlatformDashboardResponse,
    summary="Platform administrator's landing summary",
    description=(
        "Tenant lifecycle counts (total/active/suspended/inactive) and the "
        "most recently provisioned tenants - the same data GET /platform/tenants "
        "already exposes, aggregated for a landing overview. Never business "
        "data belonging to any tenant."
    ),
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_platform_admin)],
)
async def get_platform_dashboard(
    service: TenantService = Depends(get_tenant_service),
) -> PlatformDashboardResponse:
    return await service.get_dashboard_summary()


@router.post(
    "/tenants",
    response_model=TenantProvisioningResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision a new tenant with its system roles and initial administrator",
    description=(
        "Creates the tenant, replicates the default tenant's current system "
        "roles/permissions for it, and creates its first user as a tenant "
        "administrator (is_superuser=True, role='admin') - never a platform "
        "admin. Fully transactional: any failure (duplicate slug, duplicate "
        "administrator email/username, or anything else) leaves no tenant, "
        "no role, and no user behind."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        409: {"model": ErrorResponse, "description": "Duplicate slug, email or username"},
    },
    dependencies=[Depends(require_platform_admin)],
)
async def create_tenant(
    payload: TenantCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: TenantService = Depends(get_tenant_service),
) -> TenantProvisioningResponse:
    return await service.create_tenant(
        payload, actor=current_user, ctx=build_request_context(request)
    )


@router.get(
    "/tenants",
    response_model=PaginatedResponse[TenantResponse],
    summary="List tenants",
    description="Tenant summaries only - never business data belonging to any tenant.",
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_platform_admin)],
)
async def list_tenants(
    params: Annotated[TenantListParams, Query()],
    service: TenantService = Depends(get_tenant_service),
) -> PaginatedResponse[TenantResponse]:
    return await service.list_tenants(params)


@router.get(
    "/tenants/{tenant_id}",
    response_model=TenantResponse,
    summary="Get a tenant by id",
    responses={**_COMMON_ERROR_RESPONSES, **_TENANT_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_platform_admin)],
)
async def get_tenant(
    tenant_id: uuid.UUID,
    service: TenantService = Depends(get_tenant_service),
) -> TenantResponse:
    return await service.get_tenant(tenant_id)


@router.patch(
    "/tenants/{tenant_id}/status",
    response_model=TenantResponse,
    summary="Change a tenant's lifecycle status",
    description=(
        "Suspending/deactivating a tenant blocks every one of its users - "
        "including its own tenant superusers - from logging in, refreshing "
        "a token, or using an existing access token, effective immediately. "
        "Rejected if it would leave zero platform administrators reachable "
        "on any active tenant."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_TENANT_NOT_FOUND_RESPONSE,
        409: {"model": ErrorResponse, "description": "Tenant is already in this status"},
        422: {
            "model": ErrorResponse,
            "description": "Would leave no platform administrator reachable",
        },
    },
    dependencies=[Depends(require_platform_admin)],
)
async def update_tenant_status(
    tenant_id: uuid.UUID,
    payload: TenantStatusUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: TenantService = Depends(get_tenant_service),
) -> TenantResponse:
    return await service.change_status(
        tenant_id, payload.status, actor=current_user, ctx=build_request_context(request)
    )


_ADMINISTRATOR_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Tenant not found, or user is not one of this tenant's administrators",
    },
}


@router.get(
    "/tenants/{tenant_id}/administrators",
    response_model=list[TenantAdministratorResponse],
    summary="List a tenant's administrators",
    description=(
        "Active administrators only (is_superuser or holding the admin/"
        "super_admin role) - identity fields only, never roles, permissions "
        "or any tenant business data. Exists solely so a platform admin can "
        "identify which user to target for a password reset; this is not a "
        "general user-management listing."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_TENANT_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_platform_admin)],
)
async def list_tenant_administrators(
    tenant_id: uuid.UUID,
    service: TenantService = Depends(get_tenant_service),
) -> list[TenantAdministratorResponse]:
    return await service.list_administrators(tenant_id)


@router.patch(
    "/tenants/{tenant_id}/administrators/{user_id}/password",
    response_model=TenantAdministratorResponse,
    summary="Reset a tenant administrator's password",
    description=(
        "A platform-admin-only escape hatch for a locked-out tenant: sets "
        "the given password, forces a change on next login "
        "(must_change_password), and immediately revokes every existing "
        "session for that user - the same behavior as a tenant admin's own "
        "PATCH /users/{id}/password. `user_id` must already be an "
        "administrator (is_superuser or admin/super_admin role) of this "
        "specific tenant - never an arbitrary tenant user - and this never "
        "touches is_superuser/is_platform_admin/roles or grants the "
        "platform admin any ongoing access to the tenant."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_ADMINISTRATOR_NOT_FOUND_RESPONSE,
        422: {
            "model": ErrorResponse,
            "description": (
                "Cannot reset your own password here, or the new password fails the password policy"
            ),
        },
    },
    dependencies=[Depends(require_platform_admin)],
)
async def reset_tenant_administrator_password(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: TenantAdministratorPasswordResetRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: TenantService = Depends(get_tenant_service),
) -> TenantAdministratorResponse:
    return await service.reset_administrator_password(
        tenant_id,
        user_id,
        payload.new_password,
        actor=current_user,
        ctx=build_request_context(request),
    )
