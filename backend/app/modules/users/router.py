import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.common.request_context import build_request_context
from app.common.schemas import ErrorResponse, PaginatedResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.users.constants import USER_MANAGE_PERMISSION
from app.modules.users.dependencies import get_user_service
from app.modules.users.schemas import (
    RoleSummary,
    UserCreateRequest,
    UserListParams,
    UserResponse,
    UserStatusUpdateRequest,
    UserUpdateRequest,
)
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])

_COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Missing required permission"},
}
_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {"model": ErrorResponse, "description": "User not found"},
}

# Registered before "/{user_id}" - a static path always takes precedence
# over a uuid-typed path parameter, but keeping it first in file order too
# avoids relying on that.


@router.get(
    "/roles",
    response_model=list[RoleSummary],
    summary="List roles available for assignment in this tenant",
    description="Excludes the super_admin role unless the caller is a superuser.",
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_permission(USER_MANAGE_PERMISSION))],
)
async def list_role_options(
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> list[RoleSummary]:
    return await service.list_role_options(tenant_id=current_user.tenant_id, actor=current_user)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user",
    description=(
        "Creates the account with the given password already set; the account "
        "must change it on first login (see must_change_password on POST "
        "/auth/login). is_superuser is never settable through this endpoint."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        404: {"model": ErrorResponse, "description": "Role not found"},
        409: {"model": ErrorResponse, "description": "Duplicate email or username"},
        422: {"model": ErrorResponse, "description": "Password fails the password policy"},
    },
    dependencies=[Depends(require_permission(USER_MANAGE_PERMISSION))],
)
async def create_user(
    payload: UserCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return await service.create(
        payload,
        tenant_id=current_user.tenant_id,
        actor=current_user,
        ctx=build_request_context(request),
    )


_LIST_RESPONSE_EXAMPLE: dict[str, object] = {
    "data": [
        {
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
    ],
    "meta": {
        "total_records": 1,
        "total_pages": 1,
        "current_page": 1,
        "page_size": 20,
        "has_next": False,
        "has_previous": False,
    },
}


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    summary="Search, filter, sort and paginate users",
    description=(
        "Every non-deleted user for the caller's tenant. `q` searches full_name, "
        "email and username (case-insensitive substring). Combine with role_id/"
        "status filters, `sort` (e.g. `full_name`, `-created_at`) and page/page_size."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        200: {"content": {"application/json": {"example": _LIST_RESPONSE_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(USER_MANAGE_PERMISSION))],
)
async def list_users(
    params: Annotated[UserListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> PaginatedResponse[UserResponse]:
    return await service.list_users(tenant_id=current_user.tenant_id, params=params)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get a user by id",
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission(USER_MANAGE_PERMISSION))],
)
async def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return await service.get(user_id, tenant_id=current_user.tenant_id)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user",
    description=(
        "Partial update: only fields present in the request body are changed. "
        "A soft-deleted user is treated as not found. Changing role_id to/from "
        "super_admin is only permitted for a caller who is themselves a superuser."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        409: {"model": ErrorResponse, "description": "Duplicate email or username"},
    },
    dependencies=[Depends(require_permission(USER_MANAGE_PERMISSION))],
)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return await service.update(
        user_id,
        payload,
        tenant_id=current_user.tenant_id,
        actor=current_user,
        ctx=build_request_context(request),
    )


@router.patch(
    "/{user_id}/status",
    response_model=UserResponse,
    summary="Activate or deactivate a user",
    description=(
        "Deactivating a user immediately revokes all of their refresh tokens "
        "and rejects further requests on their existing access token (see "
        "get_current_user's status check). You cannot deactivate your own "
        "account, or the tenant's last active administrator."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        422: {
            "model": ErrorResponse,
            "description": "Cannot deactivate yourself or the last administrator",
        },
    },
    dependencies=[Depends(require_permission(USER_MANAGE_PERMISSION))],
)
async def update_user_status(
    user_id: uuid.UUID,
    payload: UserStatusUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return await service.set_status(
        user_id,
        payload.status,
        tenant_id=current_user.tenant_id,
        actor=current_user,
        ctx=build_request_context(request),
    )
