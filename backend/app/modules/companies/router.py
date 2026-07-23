import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.common.schemas import ErrorResponse, PaginatedResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.companies.dependencies import get_company_service
from app.modules.companies.schemas import (
    CompanyCreateRequest,
    CompanyListParams,
    CompanyResponse,
    CompanyUpdateRequest,
)
from app.modules.companies.service import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])

_COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Missing required permission"},
}
_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {"model": ErrorResponse, "description": "Company not found"},
}
_DUPLICATE_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {"model": ErrorResponse, "description": "Duplicate company code or name"},
}


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a company",
    responses={**_COMMON_ERROR_RESPONSES, **_DUPLICATE_RESPONSE},
    dependencies=[Depends(require_permission("company:create"))],
)
async def create_company(
    payload: CompanyCreateRequest,
    current_user: User = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
) -> CompanyResponse:
    return await service.create(payload, tenant_id=current_user.tenant_id, actor_id=current_user.id)


_LIST_RESPONSE_EXAMPLE: dict[str, object] = {
    "data": [
        {
            "id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
            "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
            "code": "CUST-001",
            "name": "Ocean Fresh Traders",
            "legal_name": "Ocean Fresh Traders Pvt Ltd",
            "gstin": "27ABCDE1234F1Z5",
            "pan": None,
            "address_line1": None,
            "address_line2": None,
            "city": "Mumbai",
            "state": "Maharashtra",
            "state_code": None,
            "pincode": None,
            "country": None,
            "phone": "9876543210",
            "alt_phone": None,
            "email": "contact@oceanfresh.example",
            "contact_person": "Ravi Kumar",
            "company_type": "customer",
            "credit_limit": "500000.00",
            "credit_days": 30,
            "opening_balance": "0.00",
            "opening_balance_date": None,
            "opening_balance_type": None,
            "outstanding_amount": "0.00",
            "status": "active",
            "notes": None,
            "created_at": "2026-07-20T09:48:08.714017Z",
            "updated_at": "2026-07-20T09:48:08.714017Z",
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
    response_model=PaginatedResponse[CompanyResponse],
    summary="Search, filter, sort and paginate companies",
    description=(
        "Every non-deleted company for the caller's tenant. `q` searches name, code, "
        "contact_person, phone, email and gstin (case-insensitive substring). Combine "
        "with company_type/status/city/state filters, `sort` (e.g. `name`, `-created_at`) "
        "and page/page_size."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        200: {"content": {"application/json": {"example": _LIST_RESPONSE_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission("company:view"))],
)
async def list_companies(
    params: Annotated[CompanyListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
) -> PaginatedResponse[CompanyResponse]:
    return await service.list_companies(tenant_id=current_user.tenant_id, params=params)


@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
    summary="Get a company by id",
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission("company:view"))],
)
async def get_company(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
) -> CompanyResponse:
    return await service.get(company_id, tenant_id=current_user.tenant_id)


@router.put(
    "/{company_id}",
    response_model=CompanyResponse,
    summary="Update a company",
    description=(
        "Partial update: only fields present in the request body are changed. "
        "A soft-deleted company is treated as not found."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE, **_DUPLICATE_RESPONSE},
    dependencies=[Depends(require_permission("company:edit"))],
)
async def update_company(
    company_id: uuid.UUID,
    payload: CompanyUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
) -> CompanyResponse:
    return await service.update(
        company_id, payload, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a company",
    description="Sets deleted_at/deleted_by rather than removing the row (ARCHITECTURE.md §38).",
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission("company:delete"))],
)
async def delete_company(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
) -> None:
    await service.delete(company_id, tenant_id=current_user.tenant_id, actor_id=current_user.id)
