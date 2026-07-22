import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.common.schemas import ErrorResponse, PaginatedResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.trip_catches.dependencies import get_trip_catch_service
from app.modules.trip_catches.permissions import (
    TRIP_CATCH_CREATE,
    TRIP_CATCH_DELETE,
    TRIP_CATCH_EDIT,
    TRIP_CATCH_VIEW,
)
from app.modules.trip_catches.schemas import (
    TripCatchCreateRequest,
    TripCatchListParams,
    TripCatchResponse,
    TripCatchUpdateRequest,
)
from app.modules.trip_catches.service import TripCatchService

router = APIRouter(prefix="/trip-catches", tags=["trip-catches"])


def _error_example(code: str, message: str) -> dict[str, object]:
    """A representative error envelope for Swagger's "Example Value" tab -
    request_id/timestamp are illustrative, the real response fills them in
    per-request."""
    return {
        "error": {
            "code": code,
            "message": message,
            "details": None,
            "field_errors": None,
            "request_id": "e9fefc78-4d47-4788-8d33-427f5b7852c8",
            "timestamp": "2026-07-22T04:00:00Z",
        }
    }


_COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Missing required permission"},
}
_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Trip catch not found",
        "content": {
            "application/json": {
                "example": _error_example("TRIP_CATCH_NOT_FOUND", "Trip catch not found")
            }
        },
    },
}
_TRIP_OR_FISH_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Referenced trip or referenced fish not found",
        "content": {
            "application/json": {
                "examples": {
                    "trip_not_found": {
                        "summary": "trip_id does not exist for this tenant",
                        "value": _error_example(
                            "TRIP_CATCH_TRIP_NOT_FOUND", "The specified trip does not exist"
                        ),
                    },
                    "fish_not_found": {
                        "summary": "fish_id does not exist for this tenant",
                        "value": _error_example(
                            "TRIP_CATCH_FISH_NOT_FOUND", "The specified fish does not exist"
                        ),
                    },
                }
            }
        },
    },
}
_BUSINESS_RULE_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": (
            "Business rule violation: the referenced trip has not returned yet, or "
            "available_quantity + sold_quantity + waste_quantity no longer equals "
            "quantity_caught"
        ),
        "content": {
            "application/json": {
                "examples": {
                    "trip_not_returned": {
                        "summary": "Trip exists but hasn't come back yet",
                        "value": _error_example(
                            "TRIP_CATCH_TRIP_NOT_RETURNED",
                            "The specified trip has not returned yet",
                        ),
                    },
                    "quantity_invariant_violation": {
                        "summary": "available + sold + waste != quantity_caught",
                        "value": _error_example(
                            "TRIP_CATCH_QUANTITY_INVARIANT_VIOLATION",
                            "available_quantity + sold_quantity + waste_quantity must "
                            "equal quantity_caught",
                        ),
                    },
                }
            }
        },
    },
}

_CATCH_EXAMPLE: dict[str, object] = {
    "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c02",
    "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
    "trip_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c02",
    "fish_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
    "grade": "A",
    "quantity_caught": "120.500",
    "available_quantity": "120.500",
    "sold_quantity": "0.000",
    "waste_quantity": "0.000",
    "landing_date": "2026-07-22",
    "landing_port": "Sassoon Dock",
    "remarks": None,
    "created_at": "2026-07-22T04:00:00Z",
    "updated_at": "2026-07-22T04:00:00Z",
}

_LIST_RESPONSE_EXAMPLE: dict[str, object] = {
    "data": [_CATCH_EXAMPLE],
    "meta": {
        "total_records": 1,
        "total_pages": 1,
        "current_page": 1,
        "page_size": 20,
        "has_next": False,
        "has_previous": False,
    },
}


@router.post(
    "",
    response_model=TripCatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a trip catch",
    description=(
        "`trip_id` must reference an existing, non-deleted, RETURNED trip for the "
        "caller's tenant (404 if not found, 422 if not returned). `fish_id` must "
        "reference an existing, non-deleted fish for the caller's tenant (404 if not "
        "found). `available_quantity`/`sold_quantity`/`waste_quantity` are always set "
        "to `quantity_caught`/`0`/`0` server-side and cannot be supplied - the request "
        "body silently ignores those keys if present."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_TRIP_OR_FISH_NOT_FOUND_RESPONSE,
        **_BUSINESS_RULE_RESPONSE,
        201: {"content": {"application/json": {"example": _CATCH_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(TRIP_CATCH_CREATE))],
)
async def create_trip_catch(
    payload: TripCatchCreateRequest,
    current_user: User = Depends(get_current_user),
    service: TripCatchService = Depends(get_trip_catch_service),
) -> TripCatchResponse:
    return await service.create(payload, tenant_id=current_user.tenant_id, actor_id=current_user.id)


@router.get(
    "",
    response_model=PaginatedResponse[TripCatchResponse],
    summary="Search, filter, sort and paginate trip catches",
    description=(
        "Every non-deleted trip catch for the caller's tenant. `q` searches the "
        "owning trip's trip_number and the caught fish's name (case-insensitive "
        "substring). Combine with trip_id/fish_id/grade/landing_date_from/"
        "landing_date_to filters, `sort` (one of `landing_date`, `quantity_caught`, "
        "`created_at`; prefix with `-` for descending, e.g. `-quantity_caught`) and "
        "page/page_size."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        200: {"content": {"application/json": {"example": _LIST_RESPONSE_EXAMPLE}}},
        422: {
            "model": ErrorResponse,
            "description": "Invalid sort field, or page/page_size out of range",
        },
    },
    dependencies=[Depends(require_permission(TRIP_CATCH_VIEW))],
)
async def list_trip_catches(
    params: Annotated[TripCatchListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: TripCatchService = Depends(get_trip_catch_service),
) -> PaginatedResponse[TripCatchResponse]:
    return await service.list_catches(tenant_id=current_user.tenant_id, params=params)


@router.get(
    "/{trip_catch_id}",
    response_model=TripCatchResponse,
    summary="Get a trip catch by id",
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        200: {"content": {"application/json": {"example": _CATCH_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(TRIP_CATCH_VIEW))],
)
async def get_trip_catch(
    trip_catch_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: TripCatchService = Depends(get_trip_catch_service),
) -> TripCatchResponse:
    return await service.get(trip_catch_id, tenant_id=current_user.tenant_id)


@router.put(
    "/{trip_catch_id}",
    response_model=TripCatchResponse,
    summary="Update a trip catch",
    description=(
        "Partial update: only fields present in the request body are changed. "
        "A soft-deleted trip catch is treated as not found. If `trip_id` is included "
        "and differs from the current trip, the new trip must exist and be RETURNED. "
        "If `fish_id` is included, it must reference an existing fish. If any of "
        "quantity_caught/available_quantity/sold_quantity/waste_quantity are included, "
        "the resulting set must still satisfy available + sold + waste = quantity_caught."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_TRIP_OR_FISH_NOT_FOUND_RESPONSE,
        **_BUSINESS_RULE_RESPONSE,
        200: {
            "content": {
                "application/json": {
                    "example": {
                        **_CATCH_EXAMPLE,
                        "sold_quantity": "40.000",
                        "available_quantity": "80.500",
                    }
                }
            }
        },
    },
    dependencies=[Depends(require_permission(TRIP_CATCH_EDIT))],
)
async def update_trip_catch(
    trip_catch_id: uuid.UUID,
    payload: TripCatchUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: TripCatchService = Depends(get_trip_catch_service),
) -> TripCatchResponse:
    return await service.update(
        trip_catch_id, payload, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.delete(
    "/{trip_catch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a trip catch",
    description="Sets deleted_at/deleted_by rather than removing the row (ARCHITECTURE.md §38).",
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission(TRIP_CATCH_DELETE))],
)
async def delete_trip_catch(
    trip_catch_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: TripCatchService = Depends(get_trip_catch_service),
) -> None:
    await service.delete(trip_catch_id, tenant_id=current_user.tenant_id, actor_id=current_user.id)
