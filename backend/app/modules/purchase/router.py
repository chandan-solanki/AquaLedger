import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.common.schemas import ErrorResponse, PaginatedResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.purchase.dependencies import get_purchase_service
from app.modules.purchase.permissions import (
    PURCHASE_CREATE,
    PURCHASE_DELETE,
    PURCHASE_EDIT,
    PURCHASE_POST,
    PURCHASE_VIEW,
)
from app.modules.purchase.schemas import (
    PurchaseBillCreateRequest,
    PurchaseBillItemCreateRequest,
    PurchaseBillItemListParams,
    PurchaseBillItemResponse,
    PurchaseBillItemUpdateRequest,
    PurchaseBillListParams,
    PurchaseBillResponse,
    PurchaseBillUpdateRequest,
)
from app.modules.purchase.service import PurchaseService

router = APIRouter(prefix="/purchase", tags=["purchase"])


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
        "description": "Purchase bill not found",
        "content": {
            "application/json": {
                "example": _error_example("PURCHASE_BILL_NOT_FOUND", "Purchase bill not found")
            }
        },
    },
}
_SUPPLIER_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Purchase bill not found, or referenced supplier not found",
        "content": {
            "application/json": {
                "examples": {
                    "purchase_bill_not_found": {
                        "summary": "Purchase bill does not exist for this tenant",
                        "value": _error_example(
                            "PURCHASE_BILL_NOT_FOUND", "Purchase bill not found"
                        ),
                    },
                    "supplier_not_found": {
                        "summary": "supplier_id does not exist for this tenant",
                        "value": _error_example(
                            "PURCHASE_BILL_SUPPLIER_NOT_FOUND",
                            "The specified supplier does not exist",
                        ),
                    },
                }
            }
        },
    },
}
_SUPPLIER_INACTIVE_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": "The referenced supplier exists but is not active",
        "content": {
            "application/json": {
                "example": _error_example(
                    "PURCHASE_BILL_SUPPLIER_INACTIVE", "The specified supplier is not active"
                )
            }
        },
    },
}
_NOT_DRAFT_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "The purchase bill is no longer DRAFT and cannot be edited or deleted",
        "content": {
            "application/json": {
                "example": _error_example(
                    "PURCHASE_BILL_NOT_DRAFT", "Only draft purchase bills can be edited or deleted"
                )
            }
        },
    },
}
_VALIDATION_ERROR_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": "Request validation failed, or the referenced supplier is inactive",
        "content": {
            "application/json": {
                "examples": {
                    "missing_supplier_id": {
                        "summary": "supplier_id is missing",
                        "value": {
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "message": "Request validation failed.",
                                "details": None,
                                "field_errors": {"supplier_id": ["Field required"]},
                                "request_id": "e9fefc78-4d47-4788-8d33-427f5b7852c8",
                                "timestamp": "2026-07-23T04:00:00Z",
                            }
                        },
                    },
                    "supplier_inactive": {
                        "summary": "The referenced supplier is not active",
                        "value": _error_example(
                            "PURCHASE_BILL_SUPPLIER_INACTIVE",
                            "The specified supplier is not active",
                        ),
                    },
                }
            }
        },
    },
}

_ITEM_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Purchase bill not found, or purchase bill item not found",
        "content": {
            "application/json": {
                "examples": {
                    "purchase_bill_not_found": {
                        "summary": "purchase_bill_id does not exist for this tenant",
                        "value": _error_example(
                            "PURCHASE_BILL_NOT_FOUND", "Purchase bill not found"
                        ),
                    },
                    "item_not_found": {
                        "summary": "item_id does not exist on this purchase bill for this tenant",
                        "value": _error_example(
                            "PURCHASE_BILL_ITEM_NOT_FOUND", "Purchase bill item not found"
                        ),
                    },
                }
            }
        },
    },
}
_CALCULATION_ERROR_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": (
            "The financial engine rejected a computed total - not reachable through "
            "normal input (every field that feeds the calculation is already bounded "
            "by the request schemas), except via an extreme quantity x rate overflow"
        ),
        "content": {
            "application/json": {
                "example": _error_example(
                    "PURCHASE_CALCULATION_ERROR",
                    "Computed total 1000000000000.00 exceeds 999999999999.99",
                )
            }
        },
    },
}
_EMPTY_BILL_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": "Business rule violation on post",
        "content": {
            "application/json": {
                "examples": {
                    "empty_bill": {
                        "summary": "Purchase bill has no items",
                        "value": _error_example(
                            "PURCHASE_BILL_EMPTY",
                            "A purchase bill must have at least one item to be posted",
                        ),
                    },
                    "totals_invalid": {
                        "summary": "The final pre-post recalculation rejected a computed "
                        "total - not reachable through normal input",
                        "value": _error_example(
                            "PURCHASE_TOTALS_INVALID",
                            "Computed total 1000000000000.00 exceeds 999999999999.99",
                        ),
                    },
                }
            }
        },
    },
}
_ALREADY_POSTED_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "The purchase bill is not DRAFT - already posted, already "
        "cancelled, or otherwise not eligible to be posted again",
        "content": {
            "application/json": {
                "example": _error_example(
                    "PURCHASE_BILL_NOT_DRAFT", "Only draft purchase bills can be edited or deleted"
                )
            }
        },
    },
}

_PURCHASE_BILL_EXAMPLE: dict[str, object] = {
    "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c05",
    "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
    "supplier_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
    "bill_number": None,
    "bill_date": "2026-07-23",
    "due_date": "2026-08-22",
    "status": "draft",
    "subtotal": "23625.00",
    "discount_amount": "0.00",
    "taxable_amount": "22500.00",
    "tax_amount": "1125.00",
    "transport_charge": "0.00",
    "other_charge": "0.00",
    "round_off": "0.00",
    "total_amount": "23625.00",
    "paid_amount": "0.00",
    "balance_amount": "23625.00",
    "remarks": None,
    "posted_at": None,
    "created_at": "2026-07-23T04:00:00Z",
    "updated_at": "2026-07-23T04:00:00Z",
}
_EMPTY_PURCHASE_BILL_EXAMPLE: dict[str, object] = {
    **_PURCHASE_BILL_EXAMPLE,
    "subtotal": "0.00",
    "taxable_amount": "0.00",
    "tax_amount": "0.00",
    "total_amount": "0.00",
    "balance_amount": "0.00",
}
_POSTED_PURCHASE_BILL_EXAMPLE: dict[str, object] = {
    **_PURCHASE_BILL_EXAMPLE,
    "bill_number": "PUR/2026-27/00001",
    "status": "posted",
    "posted_at": "2026-07-23T04:05:00Z",
}
_PARTIALLY_PAID_PURCHASE_BILL_EXAMPLE: dict[str, object] = {
    **_POSTED_PURCHASE_BILL_EXAMPLE,
    "status": "partially_paid",
    "paid_amount": "15000.00",
    "balance_amount": "8625.00",
}
_PAID_PURCHASE_BILL_EXAMPLE: dict[str, object] = {
    **_POSTED_PURCHASE_BILL_EXAMPLE,
    "status": "paid",
    "paid_amount": "23625.00",
    "balance_amount": "0.00",
}
_LIST_RESPONSE_EXAMPLE: dict[str, object] = {
    "data": [_PURCHASE_BILL_EXAMPLE],
    "meta": {
        "total_records": 1,
        "total_pages": 1,
        "current_page": 1,
        "page_size": 20,
        "has_next": False,
        "has_previous": False,
    },
}

_PURCHASE_BILL_ITEM_EXAMPLE: dict[str, object] = {
    "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c06",
    "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
    "purchase_bill_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c05",
    "line_number": 1,
    "description": "Pomfret - Grade A",
    "quantity": "50.000",
    "unit": "KG",
    "rate": "450.0000",
    "discount_percent": "0.00",
    "discount_amount": "0.00",
    # gross = 50.000 * 450.0000 = 22500.00, 0% discount -> taxable 22500.00,
    # 5% tax -> tax_amount 1125.00, line_total 23625.00.
    "taxable_amount": "22500.00",
    "tax_rate": "5.00",
    "tax_amount": "1125.00",
    "line_total": "23625.00",
    "created_at": "2026-07-23T04:00:00Z",
    "updated_at": "2026-07-23T04:00:00Z",
}
_ITEM_LIST_RESPONSE_EXAMPLE: list[dict[str, object]] = [_PURCHASE_BILL_ITEM_EXAMPLE]


@router.post(
    "",
    response_model=PurchaseBillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft purchase bill",
    description=(
        "Always created in `draft` status with `bill_number`/`posted_at` NULL and no "
        "items, so every financial field (subtotal/discount_amount/taxable_amount/"
        "tax_amount/transport_charge/other_charge/round_off/total_amount/paid_amount/"
        "balance_amount) starts at 0 - none of those is accepted in the request body, "
        "the server always owns them. Add line items afterwards via `POST "
        "/{purchase_bill_id}/items` to see the financial engine "
        "(app.modules.purchase.domain.totals) compute real totals. Numbering and posting "
        "arrive in Session 5. `supplier_id` must reference an existing, active, "
        "non-deleted supplier for the caller's tenant (404 if not found, 422 if inactive)."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_SUPPLIER_NOT_FOUND_RESPONSE,
        **_SUPPLIER_INACTIVE_RESPONSE,
        201: {"content": {"application/json": {"example": _EMPTY_PURCHASE_BILL_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(PURCHASE_CREATE))],
)
async def create_purchase_bill(
    payload: PurchaseBillCreateRequest,
    current_user: User = Depends(get_current_user),
    service: PurchaseService = Depends(get_purchase_service),
) -> PurchaseBillResponse:
    return await service.create(payload, tenant_id=current_user.tenant_id, actor_id=current_user.id)


@router.get(
    "",
    response_model=PaginatedResponse[PurchaseBillResponse],
    summary="Search, filter, sort and paginate purchase bills",
    description=(
        "Every non-deleted purchase bill for the caller's tenant. `q` searches bill_number "
        "and the billing supplier's name (case-insensitive substring). Combine with "
        "status/supplier_id/bill_date_from/bill_date_to filters, `sort` (one of "
        "`bill_date`, `bill_number`, `created_at`; prefix with `-` for descending, e.g. "
        "`-bill_date`) and page/page_size."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        200: {"content": {"application/json": {"example": _LIST_RESPONSE_EXAMPLE}}},
        422: {
            "model": ErrorResponse,
            "description": "Invalid sort field, or page/page_size out of range",
        },
    },
    dependencies=[Depends(require_permission(PURCHASE_VIEW))],
)
async def list_purchase_bills(
    params: Annotated[PurchaseBillListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: PurchaseService = Depends(get_purchase_service),
) -> PaginatedResponse[PurchaseBillResponse]:
    return await service.list_purchase_bills(tenant_id=current_user.tenant_id, params=params)


@router.get(
    "/{purchase_bill_id}",
    response_model=PurchaseBillResponse,
    summary="Get a purchase bill by id",
    description=(
        "`paid_amount`/`balance_amount`/`status` reflect the outstanding engine's latest "
        "recalculation (Sprint 12 Session 4): `posted` (nothing allocated yet) -> "
        "`partially_paid` (`balance_amount` > 0) -> `paid` (`balance_amount` == 0), "
        "driven entirely by supplier payment allocations against this bill - see the "
        "examples."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "draft": {
                            "summary": "Draft - not yet posted",
                            "value": _PURCHASE_BILL_EXAMPLE,
                        },
                        "posted": {
                            "summary": "Posted - no payment allocated yet",
                            "value": _POSTED_PURCHASE_BILL_EXAMPLE,
                        },
                        "partially_paid": {
                            "summary": "Partially paid - some balance remains",
                            "value": _PARTIALLY_PAID_PURCHASE_BILL_EXAMPLE,
                        },
                        "paid": {
                            "summary": "Fully paid - balance_amount is 0",
                            "value": _PAID_PURCHASE_BILL_EXAMPLE,
                        },
                    }
                }
            }
        },
    },
    dependencies=[Depends(require_permission(PURCHASE_VIEW))],
)
async def get_purchase_bill(
    purchase_bill_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PurchaseService = Depends(get_purchase_service),
) -> PurchaseBillResponse:
    return await service.get(purchase_bill_id, tenant_id=current_user.tenant_id)


@router.put(
    "/{purchase_bill_id}",
    response_model=PurchaseBillResponse,
    summary="Update a draft purchase bill",
    description=(
        "Partial update: only fields present in the request body are changed. Only "
        "`draft` purchase bills may be updated (409 otherwise). A soft-deleted purchase "
        "bill is treated as not found. If `supplier_id` is included and differs from the "
        "current supplier, the new supplier must exist and be active (404/422). "
        "Financial fields/`bill_number`/`status`/`posted_at` are not accepted here either."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_SUPPLIER_NOT_FOUND_RESPONSE,
        **_SUPPLIER_INACTIVE_RESPONSE,
        **_NOT_DRAFT_RESPONSE,
        200: {
            "content": {
                "application/json": {
                    "example": {**_PURCHASE_BILL_EXAMPLE, "remarks": "Revised due date"}
                }
            }
        },
    },
    dependencies=[Depends(require_permission(PURCHASE_EDIT))],
)
async def update_purchase_bill(
    purchase_bill_id: uuid.UUID,
    payload: PurchaseBillUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: PurchaseService = Depends(get_purchase_service),
) -> PurchaseBillResponse:
    return await service.update(
        purchase_bill_id, payload, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.delete(
    "/{purchase_bill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a draft purchase bill",
    description=(
        "Sets deleted_at/deleted_by rather than removing the row (ARCHITECTURE.md §38). "
        "Only `draft` purchase bills may be deleted (409 otherwise)."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE, **_NOT_DRAFT_RESPONSE},
    dependencies=[Depends(require_permission(PURCHASE_DELETE))],
)
async def delete_purchase_bill(
    purchase_bill_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PurchaseService = Depends(get_purchase_service),
) -> None:
    await service.delete(
        purchase_bill_id, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.post(
    "/{purchase_bill_id}/items",
    response_model=PurchaseBillItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a line item to a draft purchase bill",
    description=(
        "Only `draft` purchase bills may receive new items (409 otherwise). "
        "`line_number` is assigned server-side - sequential, starting at 1, never "
        "reused even if a later item is deleted. `discount_amount`/`taxable_amount`/"
        "`tax_amount`/`line_total` are computed server-side "
        "(app.modules.purchase.domain.totals) from `quantity`/`rate`/`discount_percent`/"
        "`tax_rate` - any such field in the request body is ignored - and the purchase "
        "bill's own totals (subtotal/discount_amount/taxable_amount/tax_amount/"
        "total_amount/balance_amount) are recalculated from every item in the same "
        "transaction."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_ITEM_NOT_FOUND_RESPONSE,
        **_NOT_DRAFT_RESPONSE,
        **_CALCULATION_ERROR_RESPONSE,
        201: {"content": {"application/json": {"example": _PURCHASE_BILL_ITEM_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(PURCHASE_CREATE))],
)
async def add_purchase_bill_item(
    purchase_bill_id: uuid.UUID,
    payload: PurchaseBillItemCreateRequest,
    current_user: User = Depends(get_current_user),
    service: PurchaseService = Depends(get_purchase_service),
) -> PurchaseBillItemResponse:
    return await service.add_item(purchase_bill_id, payload, tenant_id=current_user.tenant_id)


@router.get(
    "/{purchase_bill_id}/items",
    response_model=list[PurchaseBillItemResponse],
    summary="List the line items on a purchase bill",
    description=(
        "Every item on this purchase bill - allowed regardless of bill status (only "
        "add/edit/delete are draft-only). `q` searches description (case-insensitive "
        "substring). `sort` is one of `line_number`, `description`, `created_at` "
        "(default `line_number`); prefix with `-` for descending. No pagination - a "
        "bill's line count is small and bounded."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        200: {"content": {"application/json": {"example": _ITEM_LIST_RESPONSE_EXAMPLE}}},
        422: {"model": ErrorResponse, "description": "Invalid sort field"},
    },
    dependencies=[Depends(require_permission(PURCHASE_VIEW))],
)
async def list_purchase_bill_items(
    purchase_bill_id: uuid.UUID,
    params: Annotated[PurchaseBillItemListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: PurchaseService = Depends(get_purchase_service),
) -> list[PurchaseBillItemResponse]:
    return await service.list_items(
        purchase_bill_id, tenant_id=current_user.tenant_id, q=params.q, sort=params.sort
    )


@router.put(
    "/{purchase_bill_id}/items/{item_id}",
    response_model=PurchaseBillItemResponse,
    summary="Update a line item on a draft purchase bill",
    description=(
        "Partial update: only fields present in the request body are changed. Only "
        "items on `draft` purchase bills may be updated (409 otherwise). "
        "`discount_amount`/`taxable_amount`/`tax_amount`/`line_total` are recomputed "
        "server-side from the resulting quantity/rate/discount_percent/tax_rate, and "
        "the purchase bill's own totals are recalculated from every item in the same "
        "transaction."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_ITEM_NOT_FOUND_RESPONSE,
        **_NOT_DRAFT_RESPONSE,
        **_CALCULATION_ERROR_RESPONSE,
        200: {
            "content": {
                "application/json": {
                    "example": {
                        **_PURCHASE_BILL_ITEM_EXAMPLE,
                        "quantity": "40.000",
                        "taxable_amount": "18000.00",
                        "tax_amount": "900.00",
                        "line_total": "18900.00",
                    }
                }
            }
        },
    },
    dependencies=[Depends(require_permission(PURCHASE_EDIT))],
)
async def update_purchase_bill_item(
    purchase_bill_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: PurchaseBillItemUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: PurchaseService = Depends(get_purchase_service),
) -> PurchaseBillItemResponse:
    return await service.update_item(
        purchase_bill_id, item_id, payload, tenant_id=current_user.tenant_id
    )


@router.delete(
    "/{purchase_bill_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a line item from a draft purchase bill",
    description=(
        "Hard delete - PurchaseBillItem carries no soft-delete columns. Only items on "
        "`draft` purchase bills may be deleted (409 otherwise). The deleted item's "
        "line_number is never reused. The purchase bill's own totals are recalculated "
        "from the remaining items in the same transaction."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_ITEM_NOT_FOUND_RESPONSE, **_NOT_DRAFT_RESPONSE},
    dependencies=[Depends(require_permission(PURCHASE_DELETE))],
)
async def delete_purchase_bill_item(
    purchase_bill_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PurchaseService = Depends(get_purchase_service),
) -> None:
    await service.delete_item(purchase_bill_id, item_id, tenant_id=current_user.tenant_id)


@router.post(
    "/{purchase_bill_id}/post",
    response_model=PurchaseBillResponse,
    summary="Post a draft purchase bill",
    description=(
        "The core business transaction of this module - irreversibly transitions "
        "`draft` to `posted`, inside one database transaction: the purchase bill row "
        "is locked (`SELECT ... FOR UPDATE`), all totals are recalculated server-side "
        "from its current items, a sequential `bill_number` is assigned "
        "(`PUR/{fiscal_year}/{seq}`, concurrency-safe via a locked per-tenant counter "
        "row), and the billing supplier's `outstanding_amount` is increased by "
        "`balance_amount` - all committed together or none of it is. Requires the "
        "`draft` status (409 if already posted or cancelled) and at least one item "
        "(422 if empty). Once posted, the purchase bill and its items become fully "
        "immutable: no further edit, delete, or item CRUD is possible (409 "
        "PURCHASE_BILL_NOT_DRAFT on any attempt). From this point, `paid_amount`/"
        "`balance_amount`/`status` are recalculated automatically whenever a supplier "
        "payment is allocated against this bill (see the supplier-payments module's "
        "allocation endpoints) - `posted` -> `partially_paid` -> `paid` as "
        "`balance_amount` falls to 0, which in turn recalculates the billing "
        "supplier's `outstanding_amount` from the sum of every still-open bill. Ledger "
        "entries, PDF generation, notifications, inventory and journal entries are not "
        "implemented yet - reserved for future sprints."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        **_EMPTY_BILL_RESPONSE,
        **_ALREADY_POSTED_RESPONSE,
        200: {"content": {"application/json": {"example": _POSTED_PURCHASE_BILL_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(PURCHASE_POST))],
)
async def post_purchase_bill(
    purchase_bill_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PurchaseService = Depends(get_purchase_service),
) -> PurchaseBillResponse:
    return await service.post(
        purchase_bill_id, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )
