import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.common.schemas import ErrorResponse, PaginatedResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.supplier_payments.dependencies import get_supplier_payment_service
from app.modules.supplier_payments.permissions import (
    SUPPLIER_PAYMENT_CREATE,
    SUPPLIER_PAYMENT_DELETE,
    SUPPLIER_PAYMENT_EDIT,
    SUPPLIER_PAYMENT_POST,
    SUPPLIER_PAYMENT_VIEW,
)
from app.modules.supplier_payments.schemas import (
    SupplierPaymentAllocationCreateRequest,
    SupplierPaymentAllocationResponse,
    SupplierPaymentAllocationUpdateRequest,
    SupplierPaymentCreateRequest,
    SupplierPaymentListParams,
    SupplierPaymentResponse,
    SupplierPaymentUpdateRequest,
)
from app.modules.supplier_payments.service import SupplierPaymentService

router = APIRouter(prefix="/supplier-payments", tags=["supplier-payments"])


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
            "timestamp": "2026-07-23T04:00:00Z",
        }
    }


def _validation_error_example(field: str, message: str) -> dict[str, object]:
    """A representative pydantic-level 422 (VALIDATION_ERROR) - distinct from
    the AppException-based business-rule 422s above: this one carries
    field_errors and fires before the service layer ever runs."""
    return {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed.",
            "details": None,
            "field_errors": {field: [message]},
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
        "description": "Supplier payment not found",
        "content": {
            "application/json": {
                "example": _error_example(
                    "SUPPLIER_PAYMENT_NOT_FOUND", "Supplier payment not found"
                )
            }
        },
    },
}
_SUPPLIER_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Supplier payment not found, or referenced supplier not found",
        "content": {
            "application/json": {
                "examples": {
                    "supplier_payment_not_found": {
                        "summary": "Supplier payment does not exist for this tenant",
                        "value": _error_example(
                            "SUPPLIER_PAYMENT_NOT_FOUND", "Supplier payment not found"
                        ),
                    },
                    "supplier_not_found": {
                        "summary": "supplier_id does not exist for this tenant",
                        "value": _error_example(
                            "SUPPLIER_PAYMENT_SUPPLIER_NOT_FOUND",
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
                    "SUPPLIER_PAYMENT_SUPPLIER_INACTIVE", "The specified supplier is not active"
                )
            }
        },
    },
}
_NOT_DRAFT_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "The supplier payment is no longer DRAFT and cannot be edited or deleted",
        "content": {
            "application/json": {
                "example": _error_example(
                    "SUPPLIER_PAYMENT_NOT_DRAFT",
                    "Only draft supplier payments can be edited or deleted",
                )
            }
        },
    },
}

_SUPPLIER_PAYMENT_EXAMPLE: dict[str, object] = {
    "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c07",
    "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
    "supplier_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
    "payment_number": None,
    "payment_date": "2026-07-23",
    "payment_method": "cheque",
    "reference_number": "778821",
    "bank_name": "State Bank",
    "amount": "150000.00",
    "allocated_amount": "0.00",
    "unallocated_amount": "150000.00",
    "remarks": "Against pending purchase bills",
    "status": "draft",
    "posted_at": None,
    "created_at": "2026-07-23T04:00:00Z",
    "updated_at": "2026-07-23T04:00:00Z",
}

_LIST_RESPONSE_EXAMPLE: dict[str, object] = {
    "data": [_SUPPLIER_PAYMENT_EXAMPLE],
    "meta": {
        "total_records": 1,
        "total_pages": 1,
        "current_page": 1,
        "page_size": 20,
        "has_next": False,
        "has_previous": False,
    },
}

_ALLOCATION_NOT_DRAFT_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "The supplier payment is no longer DRAFT - allocations can't be "
        "created, updated or removed",
        "content": {
            "application/json": {
                "example": _error_example(
                    "SUPPLIER_PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT",
                    "Only draft supplier payments can receive, update or remove allocations",
                )
            }
        },
    },
}
_ALLOCATION_PURCHASE_BILL_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Supplier payment not found, or referenced purchase bill not found",
        "content": {
            "application/json": {
                "examples": {
                    "supplier_payment_not_found": {
                        "summary": "Supplier payment does not exist for this tenant",
                        "value": _error_example(
                            "SUPPLIER_PAYMENT_NOT_FOUND", "Supplier payment not found"
                        ),
                    },
                    "purchase_bill_not_found": {
                        "summary": "purchase_bill_id does not exist for this tenant",
                        "value": _error_example(
                            "SUPPLIER_PAYMENT_ALLOCATION_PURCHASE_BILL_NOT_FOUND",
                            "The specified purchase bill does not exist",
                        ),
                    },
                }
            }
        },
    },
}
_ALLOCATION_BUSINESS_RULE_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": (
            "Business rule violation: the purchase bill isn't POSTED/PARTIALLY_PAID, or "
            "allocated_amount exceeds the purchase bill's balance_amount or the payment's "
            "unallocated_amount"
        ),
        "content": {
            "application/json": {
                "examples": {
                    "purchase_bill_not_allocatable": {
                        "summary": "Purchase bill is draft, cancelled or already fully paid",
                        "value": _error_example(
                            "SUPPLIER_PAYMENT_PURCHASE_BILL_NOT_ALLOCATABLE",
                            "The specified purchase bill must be posted or partially paid to "
                            "receive an allocation",
                        ),
                    },
                    "exceeds_purchase_bill_balance": {
                        "summary": "allocated_amount exceeds the purchase bill's balance_amount",
                        "value": _error_example(
                            "SUPPLIER_PAYMENT_ALLOCATION_AMOUNT_EXCEEDED",
                            "Allocated amount 999999.00 exceeds the purchase bill's balance "
                            "23625.00",
                        ),
                    },
                    "exceeds_unallocated": {
                        "summary": "allocated_amount exceeds the payment's unallocated_amount",
                        "value": _error_example(
                            "SUPPLIER_PAYMENT_ALLOCATION_AMOUNT_EXCEEDED",
                            "Allocated amount 999999.00 exceeds the payment's unallocated "
                            "amount 150000.00",
                        ),
                    },
                    "amount_not_positive": {
                        "summary": "allocated_amount is zero or negative (pydantic-level, "
                        "not a business-rule error - fires before the service layer runs)",
                        "value": _validation_error_example(
                            "allocated_amount", "Input should be greater than 0"
                        ),
                    },
                }
            }
        },
    },
}
_ALLOCATION_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Supplier payment not found, or allocation not found",
        "content": {
            "application/json": {
                "examples": {
                    "supplier_payment_not_found": {
                        "summary": "Supplier payment does not exist for this tenant",
                        "value": _error_example(
                            "SUPPLIER_PAYMENT_NOT_FOUND", "Supplier payment not found"
                        ),
                    },
                    "allocation_not_found": {
                        "summary": "allocation_id does not exist on this supplier payment "
                        "for this tenant",
                        "value": _error_example(
                            "SUPPLIER_PAYMENT_ALLOCATION_NOT_FOUND",
                            "Supplier payment allocation not found",
                        ),
                    },
                }
            }
        },
    },
}

_ALLOCATION_EXAMPLE: dict[str, object] = {
    "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c08",
    "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
    "supplier_payment_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c07",
    "purchase_bill_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c05",
    "allocated_amount": "90000.00",
    "created_at": "2026-07-23T04:05:00Z",
}
_ALLOCATION_LIST_RESPONSE_EXAMPLE: list[dict[str, object]] = [_ALLOCATION_EXAMPLE]

_POSTED_SUPPLIER_PAYMENT_EXAMPLE: dict[str, object] = {
    **_SUPPLIER_PAYMENT_EXAMPLE,
    "payment_number": "SPAY/2026-27/00001",
    "allocated_amount": "150000.00",
    "unallocated_amount": "0.00",
    "status": "posted",
    "posted_at": "2026-07-23T04:10:00Z",
}

_NOT_DRAFT_FOR_POSTING_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "The supplier payment is no longer DRAFT - already posted, or cancelled",
        "content": {
            "application/json": {
                "example": _error_example(
                    "SUPPLIER_PAYMENT_NOT_DRAFT",
                    "Only draft supplier payments can be edited or deleted",
                )
            }
        },
    },
}
_POST_BUSINESS_RULE_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": (
            "Business rule violation: the supplier payment has no allocations, or its "
            "totals are internally inconsistent"
        ),
        "content": {
            "application/json": {
                "examples": {
                    "no_allocations": {
                        "summary": "The supplier payment has zero allocations",
                        "value": _error_example(
                            "SUPPLIER_PAYMENT_NO_ALLOCATIONS",
                            "A supplier payment must have at least one allocation to be posted",
                        ),
                    },
                    "totals_invalid": {
                        "summary": "allocated_amount + unallocated_amount != amount - a "
                        "defensive check that should be unreachable in normal use",
                        "value": _error_example(
                            "SUPPLIER_PAYMENT_TOTALS_INVALID",
                            "Supplier payment totals are inconsistent and cannot be posted",
                        ),
                    },
                }
            }
        },
    },
}


@router.post(
    "",
    response_model=SupplierPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft supplier payment",
    description=(
        "Always created in `draft` status with `payment_number`/`posted_at` NULL, "
        "`allocated_amount` 0 and `unallocated_amount` equal to `amount`; none of those "
        "fields is accepted in the request body - the server always owns them. Numbers "
        "are assigned only at posting (a future session). `supplier_id` must reference "
        "an existing, active, non-deleted supplier for the caller's tenant (404 if not "
        "found, 422 if inactive). No allocation, posting or outstanding-balance logic "
        "runs here - that arrives in later sessions."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_SUPPLIER_NOT_FOUND_RESPONSE,
        **_SUPPLIER_INACTIVE_RESPONSE,
        201: {"content": {"application/json": {"example": _SUPPLIER_PAYMENT_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(SUPPLIER_PAYMENT_CREATE))],
)
async def create_supplier_payment(
    payload: SupplierPaymentCreateRequest,
    current_user: User = Depends(get_current_user),
    service: SupplierPaymentService = Depends(get_supplier_payment_service),
) -> SupplierPaymentResponse:
    return await service.create(payload, tenant_id=current_user.tenant_id, actor_id=current_user.id)


@router.get(
    "",
    response_model=PaginatedResponse[SupplierPaymentResponse],
    summary="Search, filter, sort and paginate supplier payments",
    description=(
        "Every non-deleted supplier payment for the caller's tenant. `q` searches "
        "payment_number, reference_number and the paying-to supplier's name "
        "(case-insensitive substring). Combine with status/supplier_id/payment_method/"
        "payment_date_from/payment_date_to filters, `sort` (one of `payment_date`, "
        "`payment_number`, `created_at`; prefix with `-` for descending, e.g. "
        "`-payment_date`) and page/page_size."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        200: {"content": {"application/json": {"example": _LIST_RESPONSE_EXAMPLE}}},
        422: {
            "model": ErrorResponse,
            "description": "Invalid sort field, or page/page_size out of range",
        },
    },
    dependencies=[Depends(require_permission(SUPPLIER_PAYMENT_VIEW))],
)
async def list_supplier_payments(
    params: Annotated[SupplierPaymentListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: SupplierPaymentService = Depends(get_supplier_payment_service),
) -> PaginatedResponse[SupplierPaymentResponse]:
    return await service.list_supplier_payments(tenant_id=current_user.tenant_id, params=params)


@router.get(
    "/{supplier_payment_id}",
    response_model=SupplierPaymentResponse,
    summary="Get a supplier payment by id",
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        200: {"content": {"application/json": {"example": _SUPPLIER_PAYMENT_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(SUPPLIER_PAYMENT_VIEW))],
)
async def get_supplier_payment(
    supplier_payment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: SupplierPaymentService = Depends(get_supplier_payment_service),
) -> SupplierPaymentResponse:
    return await service.get(supplier_payment_id, tenant_id=current_user.tenant_id)


@router.put(
    "/{supplier_payment_id}",
    response_model=SupplierPaymentResponse,
    summary="Update a draft supplier payment",
    description=(
        "Partial update: only fields present in the request body are changed. Only "
        "`draft` supplier payments may be updated (409 otherwise). A soft-deleted "
        "payment is treated as not found. If `supplier_id` is included and differs "
        "from the current supplier, the new supplier must exist and be active "
        "(404/422). If `amount` changes, `unallocated_amount` is recomputed from it "
        "(`allocated_amount` stays 0 in this session, so `unallocated_amount` always "
        "ends up equal to `amount`)."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_SUPPLIER_NOT_FOUND_RESPONSE,
        **_SUPPLIER_INACTIVE_RESPONSE,
        **_NOT_DRAFT_RESPONSE,
        200: {
            "content": {
                "application/json": {
                    "example": {**_SUPPLIER_PAYMENT_EXAMPLE, "remarks": "Revised amount"}
                }
            }
        },
    },
    dependencies=[Depends(require_permission(SUPPLIER_PAYMENT_EDIT))],
)
async def update_supplier_payment(
    supplier_payment_id: uuid.UUID,
    payload: SupplierPaymentUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: SupplierPaymentService = Depends(get_supplier_payment_service),
) -> SupplierPaymentResponse:
    return await service.update(
        supplier_payment_id, payload, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.delete(
    "/{supplier_payment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a draft supplier payment",
    description=(
        "Sets deleted_at/deleted_by rather than removing the row (ARCHITECTURE.md §38). "
        "Only `draft` supplier payments may be deleted (409 otherwise) - CLAUDE.md's "
        '"Payments are never deleted" business rule applies once a payment is posted, '
        "the same immutability boundary Payment/PurchaseBill draw at posted."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE, **_NOT_DRAFT_RESPONSE},
    dependencies=[Depends(require_permission(SUPPLIER_PAYMENT_DELETE))],
)
async def delete_supplier_payment(
    supplier_payment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: SupplierPaymentService = Depends(get_supplier_payment_service),
) -> None:
    await service.delete(
        supplier_payment_id, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.post(
    "/{supplier_payment_id}/allocations",
    response_model=SupplierPaymentAllocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Allocate a draft supplier payment against a purchase bill",
    description=(
        "Only `draft` supplier payments may receive allocations (409 otherwise). "
        "`purchase_bill_id` must reference an existing, non-deleted purchase bill for the "
        "caller's tenant that is `posted` or `partially_paid` (404 if not found, 422 if "
        "draft/cancelled/paid). `allocated_amount` must not exceed the purchase bill's "
        "current `balance_amount` nor the payment's current `unallocated_amount` (422 "
        "otherwise). On success, the whole outstanding engine runs in one transaction: "
        "`SupplierPayment.allocated_amount`/`unallocated_amount` are recalculated from the "
        "sum of all active allocations, then `PurchaseBill.paid_amount`/`balance_amount`/"
        "`status` are recalculated from the sum of every allocation against that bill "
        "across all supplier payments (`posted` -> `partially_paid` -> `paid` as "
        "`balance_amount` falls to 0), and finally the bill's supplier's "
        "`outstanding_amount` is recalculated from the sum of every still-open bill's "
        "`balance_amount` - never incremented, always recomputed from source."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_ALLOCATION_PURCHASE_BILL_NOT_FOUND_RESPONSE,
        **_ALLOCATION_BUSINESS_RULE_RESPONSE,
        **_ALLOCATION_NOT_DRAFT_RESPONSE,
        201: {"content": {"application/json": {"example": _ALLOCATION_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(SUPPLIER_PAYMENT_CREATE))],
)
async def create_supplier_payment_allocation(
    supplier_payment_id: uuid.UUID,
    payload: SupplierPaymentAllocationCreateRequest,
    current_user: User = Depends(get_current_user),
    service: SupplierPaymentService = Depends(get_supplier_payment_service),
) -> SupplierPaymentAllocationResponse:
    return await service.create_allocation(
        supplier_payment_id, payload, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.get(
    "/{supplier_payment_id}/allocations",
    response_model=list[SupplierPaymentAllocationResponse],
    summary="List the allocations on a supplier payment",
    description=(
        "Every allocation on this supplier payment, oldest first - allowed regardless of "
        "payment status (only create/update/delete are draft-only). No pagination - a "
        "payment's allocation count is small and bounded."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        200: {"content": {"application/json": {"example": _ALLOCATION_LIST_RESPONSE_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(SUPPLIER_PAYMENT_VIEW))],
)
async def list_supplier_payment_allocations(
    supplier_payment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: SupplierPaymentService = Depends(get_supplier_payment_service),
) -> list[SupplierPaymentAllocationResponse]:
    return await service.list_allocations(supplier_payment_id, tenant_id=current_user.tenant_id)


@router.put(
    "/{supplier_payment_id}/allocations/{allocation_id}",
    response_model=SupplierPaymentAllocationResponse,
    summary="Update an allocation on a draft supplier payment",
    description=(
        "Partial update: only fields present in the request body are changed. Only "
        "allocations on `draft` supplier payments may be updated (409 otherwise). The full "
        "merged state (purchase_bill_id, allocated_amount) is revalidated on every update, "
        "regardless of which fields changed - same rules as creating an allocation "
        "(404/422 as appropriate), except that editing an allocation against the purchase "
        "bill it already targets is still allowed even if that bill has since become "
        "`paid` (possibly as a result of this very allocation) - only *retargeting* onto a "
        "different bill requires it to still be `posted` or `partially_paid`. "
        "`SupplierPayment.allocated_amount`/`unallocated_amount`, the affected purchase "
        "bill(s)' `paid_amount`/`balance_amount`/`status`, and their supplier(s)' "
        "`outstanding_amount` are all recalculated from source afterwards - see the create "
        "endpoint's description for the full cascade."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_ALLOCATION_NOT_FOUND_RESPONSE,
        **_ALLOCATION_PURCHASE_BILL_NOT_FOUND_RESPONSE,
        **_ALLOCATION_BUSINESS_RULE_RESPONSE,
        **_ALLOCATION_NOT_DRAFT_RESPONSE,
        200: {
            "content": {
                "application/json": {
                    "example": {**_ALLOCATION_EXAMPLE, "allocated_amount": "120000.00"}
                }
            }
        },
    },
    dependencies=[Depends(require_permission(SUPPLIER_PAYMENT_EDIT))],
)
async def update_supplier_payment_allocation(
    supplier_payment_id: uuid.UUID,
    allocation_id: uuid.UUID,
    payload: SupplierPaymentAllocationUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: SupplierPaymentService = Depends(get_supplier_payment_service),
) -> SupplierPaymentAllocationResponse:
    return await service.update_allocation(
        supplier_payment_id, allocation_id, payload, tenant_id=current_user.tenant_id
    )


@router.delete(
    "/{supplier_payment_id}/allocations/{allocation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an allocation from a draft supplier payment",
    description=(
        "Hard-deletes the allocation row - SupplierPaymentAllocation carries no "
        "deleted_at, unlike SupplierPayment itself (see its docstring). Only allocations "
        "on `draft` supplier payments may be removed (409 otherwise). "
        "`SupplierPayment.allocated_amount`/`unallocated_amount` are recalculated "
        "afterwards (the removed allocation's amount is restored to `unallocated_amount`), "
        "and the affected purchase bill's `paid_amount`/`balance_amount`/`status` and its "
        "supplier's `outstanding_amount` are recalculated from source too - a removed "
        "allocation can move a bill back down from `paid` to `partially_paid`, or from "
        "`partially_paid`/`paid` to `posted`."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_ALLOCATION_NOT_FOUND_RESPONSE,
        **_ALLOCATION_NOT_DRAFT_RESPONSE,
    },
    dependencies=[Depends(require_permission(SUPPLIER_PAYMENT_DELETE))],
)
async def delete_supplier_payment_allocation(
    supplier_payment_id: uuid.UUID,
    allocation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: SupplierPaymentService = Depends(get_supplier_payment_service),
) -> None:
    await service.delete_allocation(
        supplier_payment_id, allocation_id, tenant_id=current_user.tenant_id
    )


@router.post(
    "/{supplier_payment_id}/post",
    response_model=SupplierPaymentResponse,
    summary="Post a draft supplier payment",
    description=(
        "The core business transaction of this module (TASKS.md Sprint 12 Session 5) - "
        "irreversibly transitions `draft` to `posted`, inside one database transaction: "
        "the supplier payment row is locked (`SELECT ... FOR UPDATE`), its "
        "`allocated_amount`/`unallocated_amount` are recalculated server-side from its "
        "current allocations, a sequential `payment_number` is assigned "
        "(`SPAY/{fiscal_year}/{seq}`, concurrency-safe via a locked per-tenant counter "
        "row), and the payment is marked `posted` - all committed together or none of it "
        "is. Requires the `draft` status (409 if already posted or cancelled) and at "
        "least one allocation (422 if none). `PurchaseBill.paid_amount`/`balance_amount`/"
        "`status` and `Supplier.outstanding_amount` are NOT touched here - the Session 4 "
        "outstanding engine already keeps them correct as of every allocation change made "
        "while this payment was draft. Once posted, the payment and its allocations "
        "become fully immutable: no further edit, delete, or allocation create/update/"
        "delete is possible (409 on any attempt). Ledger posting, receipt generation, "
        "outbox event publishing and bank reconciliation are not implemented yet - "
        "reserved for future sprints."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        **_NOT_DRAFT_FOR_POSTING_RESPONSE,
        **_POST_BUSINESS_RULE_RESPONSE,
        200: {"content": {"application/json": {"example": _POSTED_SUPPLIER_PAYMENT_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(SUPPLIER_PAYMENT_POST))],
)
async def post_supplier_payment(
    supplier_payment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: SupplierPaymentService = Depends(get_supplier_payment_service),
) -> SupplierPaymentResponse:
    return await service.post(
        supplier_payment_id, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )
