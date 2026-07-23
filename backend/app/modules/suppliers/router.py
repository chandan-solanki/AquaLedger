import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.common.schemas import ErrorResponse, PaginatedResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.suppliers.dependencies import get_supplier_service
from app.modules.suppliers.permissions import (
    SUPPLIER_CREATE,
    SUPPLIER_DELETE,
    SUPPLIER_EDIT,
    SUPPLIER_VIEW,
)
from app.modules.suppliers.schemas import (
    SupplierCreateRequest,
    SupplierListParams,
    SupplierResponse,
    SupplierUpdateRequest,
)
from app.modules.suppliers.service import SupplierService

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _error_example(code: str, message: str) -> dict[str, object]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": None,
            "field_errors": None,
            "request_id": "e9fefc78-4d47-4788-8d33-427f5b7852c8",
            "timestamp": "2026-07-23T04:00:00Z",
        }
    }


_COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Missing required permission"},
}
_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Supplier not found",
        "content": {
            "application/json": {
                "example": _error_example("SUPPLIER_NOT_FOUND", "Supplier not found")
            }
        },
    },
}
_DUPLICATE_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "Duplicate supplier code or name",
        "content": {
            "application/json": {
                "examples": {
                    "duplicate_code": {
                        "summary": "code already used by another supplier in this tenant",
                        "value": _error_example(
                            "DUPLICATE_SUPPLIER_CODE", "A supplier with this code already exists"
                        ),
                    },
                    "duplicate_name": {
                        "summary": "name already used (case-insensitive) by another "
                        "supplier in this tenant",
                        "value": _error_example(
                            "DUPLICATE_SUPPLIER_NAME", "A supplier with this name already exists"
                        ),
                    },
                }
            }
        },
    },
}
_VALIDATION_ERROR_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": "Request validation failed (invalid email/phone/gstin format, "
        "negative amount, etc.)",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Request validation failed.",
                        "details": None,
                        "field_errors": {"email": ["Invalid email address format"]},
                        "request_id": "e9fefc78-4d47-4788-8d33-427f5b7852c8",
                        "timestamp": "2026-07-23T04:00:00Z",
                    }
                }
            }
        },
    },
}

_SUPPLIER_EXAMPLE: dict[str, object] = {
    "id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
    "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
    "code": "SUP-001",
    "name": "Coastal Fish Suppliers",
    "legal_name": "Coastal Fish Suppliers Pvt Ltd",
    "gstin": "27ABCDE1234F1Z5",
    "phone": "9876543210",
    "email": "contact@coastalfish.example",
    "address": "12 Harbour Road",
    "city": "Mumbai",
    "state": "Maharashtra",
    "country": "India",
    "contact_person": "Ravi Kumar",
    "credit_days": 30,
    "opening_balance": "0.00",
    "outstanding_amount": "0.00",
    "status": "active",
    "created_at": "2026-07-23T04:00:00Z",
    "updated_at": "2026-07-23T04:00:00Z",
}
_LIST_RESPONSE_EXAMPLE: dict[str, object] = {
    "data": [_SUPPLIER_EXAMPLE],
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
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a supplier",
    description=(
        "`outstanding_amount` always starts at 0 and `status` is always `active` - neither "
        "is accepted in the request body, the server always owns them."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_DUPLICATE_RESPONSE,
        **_VALIDATION_ERROR_RESPONSE,
        201: {"content": {"application/json": {"example": _SUPPLIER_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(SUPPLIER_CREATE))],
)
async def create_supplier(
    payload: SupplierCreateRequest,
    current_user: User = Depends(get_current_user),
    service: SupplierService = Depends(get_supplier_service),
) -> SupplierResponse:
    return await service.create(payload, tenant_id=current_user.tenant_id, actor_id=current_user.id)


@router.get(
    "",
    response_model=PaginatedResponse[SupplierResponse],
    summary="Search, filter, sort and paginate suppliers",
    description=(
        "Every non-deleted supplier for the caller's tenant. `q` searches code, name and "
        "gstin (case-insensitive substring). Combine with status/city/state filters, "
        "`sort` (one of `name`, `code`, `created_at`; prefix with `-` for descending, e.g. "
        "`-created_at`) and page/page_size."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        200: {"content": {"application/json": {"example": _LIST_RESPONSE_EXAMPLE}}},
        422: {
            "model": ErrorResponse,
            "description": "Invalid sort field, or page/page_size out of range",
        },
    },
    dependencies=[Depends(require_permission(SUPPLIER_VIEW))],
)
async def list_suppliers(
    params: Annotated[SupplierListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: SupplierService = Depends(get_supplier_service),
) -> PaginatedResponse[SupplierResponse]:
    return await service.list_suppliers(tenant_id=current_user.tenant_id, params=params)


@router.get(
    "/{supplier_id}",
    response_model=SupplierResponse,
    summary="Get a supplier by id",
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        200: {"content": {"application/json": {"example": _SUPPLIER_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(SUPPLIER_VIEW))],
)
async def get_supplier(
    supplier_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: SupplierService = Depends(get_supplier_service),
) -> SupplierResponse:
    return await service.get(supplier_id, tenant_id=current_user.tenant_id)


@router.put(
    "/{supplier_id}",
    response_model=SupplierResponse,
    summary="Update a supplier",
    description=(
        "Partial update: only fields present in the request body are changed. "
        "`outstanding_amount`/`status` are not accepted here either. A soft-deleted "
        "supplier is treated as not found."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        **_DUPLICATE_RESPONSE,
        **_VALIDATION_ERROR_RESPONSE,
    },
    dependencies=[Depends(require_permission(SUPPLIER_EDIT))],
)
async def update_supplier(
    supplier_id: uuid.UUID,
    payload: SupplierUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: SupplierService = Depends(get_supplier_service),
) -> SupplierResponse:
    return await service.update(
        supplier_id, payload, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.delete(
    "/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a supplier",
    description="Sets deleted_at/deleted_by rather than removing the row (ARCHITECTURE.md §38).",
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission(SUPPLIER_DELETE))],
)
async def delete_supplier(
    supplier_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: SupplierService = Depends(get_supplier_service),
) -> None:
    await service.delete(supplier_id, tenant_id=current_user.tenant_id, actor_id=current_user.id)
