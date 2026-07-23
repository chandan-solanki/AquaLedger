import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.common.schemas import ErrorResponse, PaginatedResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.trip_expenses.dependencies import get_trip_expense_service
from app.modules.trip_expenses.permissions import (
    TRIP_EXPENSE_CREATE,
    TRIP_EXPENSE_DELETE,
    TRIP_EXPENSE_EDIT,
    TRIP_EXPENSE_VIEW,
)
from app.modules.trip_expenses.schemas import (
    TripExpenseCreateRequest,
    TripExpenseListParams,
    TripExpenseResponse,
    TripExpenseUpdateRequest,
)
from app.modules.trip_expenses.service import TripExpenseService

router = APIRouter(prefix="/trip-expenses", tags=["trip-expenses"])


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


def _validation_error_example(field: str, message: str) -> dict[str, object]:
    """A representative pydantic-level 422 (VALIDATION_ERROR) - distinct from
    the AppException-based business-rule 422s above: this one carries
    field_errors and fires before the service layer ever runs, e.g. amount
    <= 0 or an unknown expense_type."""
    return {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed.",
            "details": None,
            "field_errors": {field: [message]},
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
        "description": "Trip expense not found",
        "content": {
            "application/json": {
                "example": _error_example("TRIP_EXPENSE_NOT_FOUND", "Trip expense not found")
            }
        },
    },
}
_TRIP_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Referenced trip not found",
        "content": {
            "application/json": {
                "example": _error_example(
                    "TRIP_EXPENSE_TRIP_NOT_FOUND", "The specified trip does not exist"
                )
            }
        },
    },
}
_BUSINESS_RULE_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": (
            "Business rule violation: the referenced trip is cancelled, or expense_date "
            "falls outside the trip's departure/return window"
        ),
        "content": {
            "application/json": {
                "examples": {
                    "trip_cancelled": {
                        "summary": "The referenced trip is CANCELLED",
                        "value": _error_example(
                            "TRIP_EXPENSE_TRIP_CANCELLED",
                            "Cancelled trips cannot receive new expenses",
                        ),
                    },
                    "date_before_departure": {
                        "summary": "expense_date is before the trip's departure_datetime",
                        "value": _error_example(
                            "TRIP_EXPENSE_DATE_BEFORE_DEPARTURE",
                            "Expense date cannot be before the trip's departure date",
                        ),
                    },
                    "date_after_return": {
                        "summary": "expense_date is after the trip's actual_return_datetime",
                        "value": _error_example(
                            "TRIP_EXPENSE_DATE_AFTER_RETURN",
                            "Expense date cannot be after the trip's return date",
                        ),
                    },
                    "amount_not_positive": {
                        "summary": "amount is zero or negative (pydantic-level, not a "
                        "business-rule error - fires before the service layer runs)",
                        "value": _validation_error_example(
                            "amount", "Input should be greater than 0"
                        ),
                    },
                }
            }
        },
    },
}

_EXPENSE_EXAMPLE: dict[str, object] = {
    "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c02",
    "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
    "trip_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c02",
    "expense_type": "diesel",
    "amount": "4500.00",
    "expense_date": "2026-07-22",
    "description": "Diesel refill before departure",
    "vendor_name": "Sassoon Dock Fuel Co",
    "receipt_number": "RCPT-1042",
    "created_at": "2026-07-22T04:00:00Z",
    "updated_at": "2026-07-22T04:00:00Z",
}

_LIST_RESPONSE_EXAMPLE: dict[str, object] = {
    "data": [_EXPENSE_EXAMPLE],
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
    response_model=TripExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a trip expense",
    description=(
        "`trip_id` must reference an existing, non-deleted, non-cancelled trip for the "
        "caller's tenant (404 if not found, 422 if cancelled). `expense_date` must fall "
        "within the trip's departure/return window (422 otherwise; no upper bound if the "
        "trip hasn't returned yet). `amount` must be greater than zero."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_TRIP_NOT_FOUND_RESPONSE,
        **_BUSINESS_RULE_RESPONSE,
        201: {"content": {"application/json": {"example": _EXPENSE_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(TRIP_EXPENSE_CREATE))],
)
async def create_trip_expense(
    payload: TripExpenseCreateRequest,
    current_user: User = Depends(get_current_user),
    service: TripExpenseService = Depends(get_trip_expense_service),
) -> TripExpenseResponse:
    return await service.create(payload, tenant_id=current_user.tenant_id, actor_id=current_user.id)


@router.get(
    "",
    response_model=PaginatedResponse[TripExpenseResponse],
    summary="Search, filter, sort and paginate trip expenses",
    description=(
        "Every non-deleted trip expense for the caller's tenant. `q` searches "
        "vendor_name and receipt_number (case-insensitive substring). Combine with "
        "trip_id/expense_type/expense_date_from/expense_date_to filters, `sort` (one "
        "of `expense_date`, `amount`, `created_at`; prefix with `-` for descending, "
        "e.g. `-amount`) and page/page_size."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        200: {"content": {"application/json": {"example": _LIST_RESPONSE_EXAMPLE}}},
        422: {
            "model": ErrorResponse,
            "description": "Invalid sort field, or page/page_size out of range",
        },
    },
    dependencies=[Depends(require_permission(TRIP_EXPENSE_VIEW))],
)
async def list_trip_expenses(
    params: Annotated[TripExpenseListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: TripExpenseService = Depends(get_trip_expense_service),
) -> PaginatedResponse[TripExpenseResponse]:
    return await service.list_expenses(tenant_id=current_user.tenant_id, params=params)


@router.get(
    "/{trip_expense_id}",
    response_model=TripExpenseResponse,
    summary="Get a trip expense by id",
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        200: {"content": {"application/json": {"example": _EXPENSE_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(TRIP_EXPENSE_VIEW))],
)
async def get_trip_expense(
    trip_expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: TripExpenseService = Depends(get_trip_expense_service),
) -> TripExpenseResponse:
    return await service.get(trip_expense_id, tenant_id=current_user.tenant_id)


@router.put(
    "/{trip_expense_id}",
    response_model=TripExpenseResponse,
    summary="Update a trip expense",
    description=(
        "Partial update: only fields present in the request body are changed. "
        "A soft-deleted trip expense is treated as not found. If `trip_id` and/or "
        "`expense_date` are included, the resulting pair (merged with the record's "
        "current values) is re-validated against the owning trip's cancelled-status "
        "and departure/return window, the same way creation is."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_TRIP_NOT_FOUND_RESPONSE,
        **_BUSINESS_RULE_RESPONSE,
        200: {
            "content": {"application/json": {"example": {**_EXPENSE_EXAMPLE, "amount": "4800.00"}}}
        },
    },
    dependencies=[Depends(require_permission(TRIP_EXPENSE_EDIT))],
)
async def update_trip_expense(
    trip_expense_id: uuid.UUID,
    payload: TripExpenseUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: TripExpenseService = Depends(get_trip_expense_service),
) -> TripExpenseResponse:
    return await service.update(
        trip_expense_id, payload, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.delete(
    "/{trip_expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a trip expense",
    description="Sets deleted_at/deleted_by rather than removing the row (ARCHITECTURE.md §38).",
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission(TRIP_EXPENSE_DELETE))],
)
async def delete_trip_expense(
    trip_expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: TripExpenseService = Depends(get_trip_expense_service),
) -> None:
    await service.delete(
        trip_expense_id, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )
