import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.common.schemas import ErrorResponse, PaginatedResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.boats.dependencies import get_boat_service
from app.modules.boats.permissions import BOAT_CREATE, BOAT_DELETE, BOAT_EDIT, BOAT_VIEW
from app.modules.boats.schemas import (
    BoatCreateRequest,
    BoatListParams,
    BoatResponse,
    BoatUpdateRequest,
)
from app.modules.boats.service import BoatService

router = APIRouter(prefix="/boats", tags=["boats"])

_COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Missing required permission"},
}
_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {"model": ErrorResponse, "description": "Boat not found"},
}
_COMPANY_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {"model": ErrorResponse, "description": "Boat or referenced company not found"},
}
_DUPLICATE_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {"model": ErrorResponse, "description": "Duplicate boat code or registration number"},
}


@router.post(
    "",
    response_model=BoatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a boat",
    description=(
        "`code` and `registration_number` must each be unique per tenant; both return "
        "409 on conflict. `company_id` must reference an existing, non-deleted company "
        "for the caller's tenant, or this returns 404."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_COMPANY_NOT_FOUND_RESPONSE, **_DUPLICATE_RESPONSE},
    dependencies=[Depends(require_permission(BOAT_CREATE))],
)
async def create_boat(
    payload: BoatCreateRequest,
    current_user: User = Depends(get_current_user),
    service: BoatService = Depends(get_boat_service),
) -> BoatResponse:
    return await service.create(payload, tenant_id=current_user.tenant_id, actor_id=current_user.id)


_LIST_RESPONSE_EXAMPLE: dict[str, object] = {
    "data": [
        {
            "id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
            "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
            "company_id": "019f7af3-9c1e-73aa-9c2e-2a6a6e6a6a6a",
            "code": "BOAT-001",
            "name": "Sea Falcon",
            "registration_number": "MH-01-AB-1234",
            "license_number": "LIC-9988",
            "boat_type": "trawler",
            "capacity_kg": "12000.000",
            "engine_number": "ENG-4521",
            "engine_hp": 180,
            "captain_name": "Suresh Patil",
            "captain_phone": "9876543210",
            "insurance_expiry": "2027-03-31",
            "license_expiry": "2027-01-15",
            "notes": None,
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
    response_model=PaginatedResponse[BoatResponse],
    summary="Search, filter, sort and paginate boats",
    description=(
        "Every non-deleted boat for the caller's tenant. `q` searches name, code, "
        "registration_number and captain_name (case-insensitive substring). Combine "
        "with boat_type/company_id/is_active/insurance_expired/license_expired filters, "
        "`sort` (e.g. `name`, `-created_at`) and page/page_size."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        200: {"content": {"application/json": {"example": _LIST_RESPONSE_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(BOAT_VIEW))],
)
async def list_boats(
    params: Annotated[BoatListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: BoatService = Depends(get_boat_service),
) -> PaginatedResponse[BoatResponse]:
    return await service.list_boats(tenant_id=current_user.tenant_id, params=params)


@router.get(
    "/{boat_id}",
    response_model=BoatResponse,
    summary="Get a boat by id",
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission(BOAT_VIEW))],
)
async def get_boat(
    boat_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: BoatService = Depends(get_boat_service),
) -> BoatResponse:
    return await service.get(boat_id, tenant_id=current_user.tenant_id)


@router.put(
    "/{boat_id}",
    response_model=BoatResponse,
    summary="Update a boat",
    description=(
        "Partial update: only fields present in the request body are changed. "
        "A soft-deleted boat is treated as not found. If `company_id` is included, "
        "it must reference an existing, non-deleted company for the caller's tenant."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_COMPANY_NOT_FOUND_RESPONSE, **_DUPLICATE_RESPONSE},
    dependencies=[Depends(require_permission(BOAT_EDIT))],
)
async def update_boat(
    boat_id: uuid.UUID,
    payload: BoatUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: BoatService = Depends(get_boat_service),
) -> BoatResponse:
    return await service.update(
        boat_id, payload, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.delete(
    "/{boat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a boat",
    description="Sets deleted_at/deleted_by rather than removing the row (ARCHITECTURE.md §38).",
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission(BOAT_DELETE))],
)
async def delete_boat(
    boat_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: BoatService = Depends(get_boat_service),
) -> None:
    await service.delete(boat_id, tenant_id=current_user.tenant_id, actor_id=current_user.id)
