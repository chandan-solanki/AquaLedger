import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.common.schemas import ErrorResponse, PaginatedResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.fish.dependencies import get_fish_service
from app.modules.fish.permissions import FISH_MANAGE, FISH_VIEW
from app.modules.fish.schemas import (
    FishCreateRequest,
    FishListParams,
    FishResponse,
    FishUpdateRequest,
)
from app.modules.fish.service import FishService

router = APIRouter(prefix="/fish", tags=["fish"])

_COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Missing required permission"},
}
_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {"model": ErrorResponse, "description": "Fish not found"},
}
_DUPLICATE_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {"model": ErrorResponse, "description": "Duplicate fish code or name"},
}


@router.post(
    "",
    response_model=FishResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a fish master record",
    description=(
        "`code` must be unique per tenant; `name` must be unique per tenant "
        "(case-insensitive). Both return 409 on conflict."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_DUPLICATE_RESPONSE},
    dependencies=[Depends(require_permission(FISH_MANAGE))],
)
async def create_fish(
    payload: FishCreateRequest,
    current_user: User = Depends(get_current_user),
    service: FishService = Depends(get_fish_service),
) -> FishResponse:
    return await service.create(payload, tenant_id=current_user.tenant_id, actor_id=current_user.id)


_LIST_RESPONSE_EXAMPLE: dict[str, object] = {
    "data": [
        {
            "id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
            "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
            "code": "FISH-001",
            "name": "Pomfret",
            "local_name": "Paplet",
            "scientific_name": "Pampus argenteus",
            "category": "Whitefish",
            "unit": "kg",
            "default_purchase_rate": "450.0000",
            "default_sale_rate": "550.0000",
            "hsn_code": "0302",
            "description": None,
            "is_active": True,
            "created_at": "2026-07-21T09:48:08.714017Z",
            "updated_at": "2026-07-21T09:48:08.714017Z",
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
    response_model=PaginatedResponse[FishResponse],
    summary="Search, filter, sort and paginate fish master records",
    description=(
        "Every non-deleted fish record for the caller's tenant. `q` searches code, name, "
        "local_name and scientific_name (case-insensitive substring). Combine with "
        "category/unit/is_active filters, `sort` (e.g. `name`, `-created_at`) and "
        "page/page_size."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        200: {"content": {"application/json": {"example": _LIST_RESPONSE_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(FISH_VIEW))],
)
async def list_fish(
    params: Annotated[FishListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: FishService = Depends(get_fish_service),
) -> PaginatedResponse[FishResponse]:
    return await service.list_fish(tenant_id=current_user.tenant_id, params=params)


@router.get(
    "/{fish_id}",
    response_model=FishResponse,
    summary="Get a fish master record by id",
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission(FISH_VIEW))],
)
async def get_fish(
    fish_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: FishService = Depends(get_fish_service),
) -> FishResponse:
    return await service.get(fish_id, tenant_id=current_user.tenant_id)


@router.put(
    "/{fish_id}",
    response_model=FishResponse,
    summary="Update a fish master record",
    description=(
        "Partial update: only fields present in the request body are changed. "
        "A soft-deleted fish is treated as not found."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE, **_DUPLICATE_RESPONSE},
    dependencies=[Depends(require_permission(FISH_MANAGE))],
)
async def update_fish(
    fish_id: uuid.UUID,
    payload: FishUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: FishService = Depends(get_fish_service),
) -> FishResponse:
    return await service.update(
        fish_id, payload, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.delete(
    "/{fish_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a fish master record",
    description="Sets deleted_at/deleted_by rather than removing the row (ARCHITECTURE.md §38).",
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission(FISH_MANAGE))],
)
async def delete_fish(
    fish_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: FishService = Depends(get_fish_service),
) -> None:
    await service.delete(fish_id, tenant_id=current_user.tenant_id, actor_id=current_user.id)
