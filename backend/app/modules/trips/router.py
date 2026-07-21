import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.common.schemas import ErrorResponse, PaginatedResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.trips.dependencies import get_trip_service
from app.modules.trips.permissions import TRIP_CREATE, TRIP_DELETE, TRIP_EDIT, TRIP_VIEW
from app.modules.trips.schemas import (
    TripCreateRequest,
    TripListParams,
    TripResponse,
    TripUpdateRequest,
)
from app.modules.trips.service import TripService

router = APIRouter(prefix="/trips", tags=["trips"])


def _error_example(code: str, message: str) -> dict[str, object]:
    """A representative error envelope for Swagger's "Example Value" tab -
    request_id/timestamp are illustrative, the real response fills them in
    per-request."""
    return {
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": code,
                        "message": message,
                        "details": None,
                        "field_errors": None,
                        "request_id": "e9fefc78-4d47-4788-8d33-427f5b7852c8",
                        "timestamp": "2026-07-22T04:00:00Z",
                    }
                }
            }
        }
    }


_COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Missing required permission"},
}
_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Trip not found",
        **_error_example("TRIP_NOT_FOUND", "Trip not found"),
    },
}
_BOAT_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Trip or referenced boat not found",
        **_error_example("TRIP_BOAT_NOT_FOUND", "The specified boat does not exist"),
    },
}
_DUPLICATE_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "Duplicate trip number",
        **_error_example("DUPLICATE_TRIP_NUMBER", "A trip with this trip number already exists"),
    },
}
_UPDATE_CONFLICT_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "Duplicate trip number, or boat reassignment on a returned trip",
        **_error_example("TRIP_BOAT_CHANGE_NOT_ALLOWED", "Returned trips cannot change boat"),
    },
}
_BUSINESS_RULE_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": (
            "Business rule violation: boat is not active, boat already has an active "
            "trip, or actual_return_datetime is before departure_datetime"
        ),
        **_error_example("TRIP_BOAT_ALREADY_ACTIVE", "This boat already has an active trip"),
    },
}


@router.post(
    "",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a trip",
    description=(
        "`trip_number` must be unique per tenant; returns 409 on conflict. `boat_id` "
        "must reference an existing, active, non-deleted boat for the caller's tenant "
        "(404 if not found, 422 if inactive). If `status` is `planned` or `departed`, "
        "the boat must not already have another active trip (422)."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_BOAT_NOT_FOUND_RESPONSE,
        **_DUPLICATE_RESPONSE,
        **_BUSINESS_RULE_RESPONSE,
    },
    dependencies=[Depends(require_permission(TRIP_CREATE))],
)
async def create_trip(
    payload: TripCreateRequest,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> TripResponse:
    return await service.create(payload, tenant_id=current_user.tenant_id, actor_id=current_user.id)


_LIST_RESPONSE_EXAMPLE: dict[str, object] = {
    "data": [
        {
            "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c02",
            "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
            "boat_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
            "trip_number": "TRIP-2026-001",
            "trip_type": "fishing",
            "captain_name": "Suresh Patil",
            "departure_port": "Sassoon Dock",
            "arrival_port": None,
            "departure_datetime": "2026-07-22T04:30:00Z",
            "expected_return_datetime": "2026-07-25T18:00:00Z",
            "actual_return_datetime": None,
            "status": "planned",
            "notes": None,
            "is_active": True,
            "created_at": "2026-07-22T04:00:00Z",
            "updated_at": "2026-07-22T04:00:00Z",
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
    response_model=PaginatedResponse[TripResponse],
    summary="Search, filter, sort and paginate trips",
    description=(
        "Every non-deleted trip for the caller's tenant. `q` searches trip_number, "
        "boat name and captain_name (case-insensitive substring). Combine with "
        "boat_id/status/trip_type/departure_date_from/departure_date_to/"
        "return_date_from/return_date_to filters, `sort` (e.g. `trip_number`, "
        "`-departure_datetime`) and page/page_size."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        200: {"content": {"application/json": {"example": _LIST_RESPONSE_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(TRIP_VIEW))],
)
async def list_trips(
    params: Annotated[TripListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> PaginatedResponse[TripResponse]:
    return await service.list_trips(tenant_id=current_user.tenant_id, params=params)


@router.get(
    "/{trip_id}",
    response_model=TripResponse,
    summary="Get a trip by id",
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission(TRIP_VIEW))],
)
async def get_trip(
    trip_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> TripResponse:
    return await service.get(trip_id, tenant_id=current_user.tenant_id)


@router.put(
    "/{trip_id}",
    response_model=TripResponse,
    summary="Update a trip",
    description=(
        "Partial update: only fields present in the request body are changed. "
        "A soft-deleted trip is treated as not found. If `boat_id` is included and "
        "differs from the current boat, the new boat must exist, be active, and not "
        "already have another active trip (a returned trip can never change boat - "
        "409). If the resulting status is `planned` or `departed`, the boat must not "
        "have another active trip. If `departure_datetime` or `actual_return_datetime` "
        "change, the actual return may not be before departure."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_BOAT_NOT_FOUND_RESPONSE,
        **_UPDATE_CONFLICT_RESPONSE,
        **_BUSINESS_RULE_RESPONSE,
    },
    dependencies=[Depends(require_permission(TRIP_EDIT))],
)
async def update_trip(
    trip_id: uuid.UUID,
    payload: TripUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> TripResponse:
    return await service.update(
        trip_id, payload, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.delete(
    "/{trip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a trip",
    description="Sets deleted_at/deleted_by rather than removing the row (ARCHITECTURE.md §38).",
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission(TRIP_DELETE))],
)
async def delete_trip(
    trip_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> None:
    await service.delete(trip_id, tenant_id=current_user.tenant_id, actor_id=current_user.id)
