import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.common.schemas import ErrorResponse, PaginatedResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.payments.dependencies import get_payment_service
from app.modules.payments.permissions import (
    PAYMENT_CREATE,
    PAYMENT_DELETE,
    PAYMENT_EDIT,
    PAYMENT_POST,
    PAYMENT_VIEW,
)
from app.modules.payments.schemas import (
    PaymentAllocationCreateRequest,
    PaymentAllocationResponse,
    PaymentAllocationUpdateRequest,
    PaymentCreateRequest,
    PaymentListParams,
    PaymentResponse,
    PaymentUpdateRequest,
)
from app.modules.payments.service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


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
        "description": "Payment not found",
        "content": {
            "application/json": {
                "example": _error_example("PAYMENT_NOT_FOUND", "Payment not found")
            }
        },
    },
}
_COMPANY_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Payment not found, or referenced company not found",
        "content": {
            "application/json": {
                "examples": {
                    "payment_not_found": {
                        "summary": "Payment does not exist for this tenant",
                        "value": _error_example("PAYMENT_NOT_FOUND", "Payment not found"),
                    },
                    "company_not_found": {
                        "summary": "company_id does not exist for this tenant",
                        "value": _error_example(
                            "PAYMENT_COMPANY_NOT_FOUND", "The specified company does not exist"
                        ),
                    },
                }
            }
        },
    },
}
_COMPANY_INACTIVE_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": "The referenced company exists but is not active",
        "content": {
            "application/json": {
                "example": _error_example(
                    "PAYMENT_COMPANY_INACTIVE", "The specified company is not active"
                )
            }
        },
    },
}
_NOT_DRAFT_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "The payment is no longer DRAFT and cannot be edited or deleted",
        "content": {
            "application/json": {
                "example": _error_example(
                    "PAYMENT_NOT_DRAFT", "Only draft payments can be edited or deleted"
                )
            }
        },
    },
}

_PAYMENT_EXAMPLE: dict[str, object] = {
    "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c05",
    "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
    "company_id": "019f7af3-83ae-783a-b139-40a239786b30",
    "payment_number": None,
    "payment_date": "2026-07-23",
    "payment_method": "cheque",
    "reference_number": "445512",
    "bank_name": "State Bank",
    "amount": "200000.00",
    "allocated_amount": "0.00",
    "unallocated_amount": "200000.00",
    "remarks": "Against pending invoices",
    "status": "draft",
    "created_at": "2026-07-23T04:00:00Z",
    "updated_at": "2026-07-23T04:00:00Z",
}

_LIST_RESPONSE_EXAMPLE: dict[str, object] = {
    "data": [_PAYMENT_EXAMPLE],
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
        "description": "The payment is no longer DRAFT - allocations can't be created, "
        "updated or removed",
        "content": {
            "application/json": {
                "example": _error_example(
                    "PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT",
                    "Only draft payments can receive, update or remove allocations",
                )
            }
        },
    },
}
_ALLOCATION_INVOICE_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Payment not found, or referenced invoice not found",
        "content": {
            "application/json": {
                "examples": {
                    "payment_not_found": {
                        "summary": "Payment does not exist for this tenant",
                        "value": _error_example("PAYMENT_NOT_FOUND", "Payment not found"),
                    },
                    "invoice_not_found": {
                        "summary": "invoice_id does not exist for this tenant",
                        "value": _error_example(
                            "PAYMENT_ALLOCATION_INVOICE_NOT_FOUND",
                            "The specified invoice does not exist",
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
            "Business rule violation: the invoice isn't ISSUED or PARTIALLY_PAID, or "
            "allocated_amount exceeds the invoice's balance_amount or the payment's "
            "unallocated_amount"
        ),
        "content": {
            "application/json": {
                "examples": {
                    "invoice_invalid_status": {
                        "summary": "Invoice is draft, cancelled or already fully paid",
                        "value": _error_example(
                            "PAYMENT_ALLOCATION_INVOICE_INVALID_STATUS",
                            "The specified invoice must be issued or partially paid to "
                            "receive an allocation",
                        ),
                    },
                    "exceeds_invoice_balance": {
                        "summary": "allocated_amount exceeds the invoice's balance_amount",
                        "value": _error_example(
                            "PAYMENT_ALLOCATION_AMOUNT_EXCEEDED",
                            "Allocated amount 999999.00 exceeds the invoice's balance 23875.00",
                        ),
                    },
                    "exceeds_unallocated": {
                        "summary": "allocated_amount exceeds the payment's unallocated_amount",
                        "value": _error_example(
                            "PAYMENT_ALLOCATION_AMOUNT_EXCEEDED",
                            "Allocated amount 999999.00 exceeds the payment's unallocated "
                            "amount 200000.00",
                        ),
                    },
                    "amount_not_positive": {
                        "summary": "allocated_amount is zero or negative (pydantic-level, "
                        "not a business-rule error - fires before the service layer runs)",
                        "value": _validation_error_example(
                            "allocated_amount", "Input should be greater than 0"
                        ),
                    },
                    "invoice_reconciliation_error": {
                        "summary": "The outstanding engine rejected a recalculated invoice "
                        "total - not reachable through normal use, the ceilings above "
                        "already keep this unreachable",
                        "value": _error_example(
                            "INVOICE_RECONCILIATION_ERROR",
                            "Computed paid amount 999999.00 exceeds the invoice's total 23875.00",
                        ),
                    },
                    "company_outstanding_calculation_error": {
                        "summary": "The outstanding engine computed a negative company "
                        "outstanding_amount - not reachable through normal use",
                        "value": _error_example(
                            "COMPANY_OUTSTANDING_CALCULATION_ERROR",
                            "Computed outstanding amount -100.00 is negative",
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
        "description": "Payment not found, or allocation not found",
        "content": {
            "application/json": {
                "examples": {
                    "payment_not_found": {
                        "summary": "Payment does not exist for this tenant",
                        "value": _error_example("PAYMENT_NOT_FOUND", "Payment not found"),
                    },
                    "allocation_not_found": {
                        "summary": "allocation_id does not exist on this payment for this tenant",
                        "value": _error_example(
                            "PAYMENT_ALLOCATION_NOT_FOUND", "Payment allocation not found"
                        ),
                    },
                }
            }
        },
    },
}

_ALLOCATION_EXAMPLE: dict[str, object] = {
    "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c06",
    "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
    "payment_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c05",
    "invoice_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c03",
    "allocated_amount": "120000.00",
    "created_at": "2026-07-23T04:05:00Z",
}
_ALLOCATION_LIST_RESPONSE_EXAMPLE: list[dict[str, object]] = [_ALLOCATION_EXAMPLE]

_POSTED_PAYMENT_EXAMPLE: dict[str, object] = {
    **_PAYMENT_EXAMPLE,
    "payment_number": "PAY/2026-27/00001",
    "allocated_amount": "120000.00",
    "unallocated_amount": "80000.00",
    "status": "posted",
}

_NOT_DRAFT_FOR_POSTING_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "The payment is no longer DRAFT - already posted, or cancelled",
        "content": {
            "application/json": {
                "example": _error_example(
                    "PAYMENT_NOT_DRAFT", "Only draft payments can be edited or deleted"
                )
            }
        },
    },
}
_POST_BUSINESS_RULE_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": (
            "Business rule violation: the payment has no allocations, or its totals are "
            "internally inconsistent"
        ),
        "content": {
            "application/json": {
                "examples": {
                    "no_allocations": {
                        "summary": "The payment has zero allocations",
                        "value": _error_example(
                            "PAYMENT_NO_ALLOCATIONS",
                            "A payment must have at least one allocation to be posted",
                        ),
                    },
                    "totals_invalid": {
                        "summary": "allocated_amount + unallocated_amount != amount - a "
                        "defensive check that should be unreachable in normal use",
                        "value": _error_example(
                            "PAYMENT_TOTALS_INVALID",
                            "Payment totals are inconsistent and cannot be posted",
                        ),
                    },
                }
            }
        },
    },
}


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft payment",
    description=(
        "Always created in `draft` status with `payment_number` NULL, `allocated_amount` 0 "
        "and `unallocated_amount` equal to `amount`; none of those four fields is accepted "
        "in the request body - the server always owns them. Numbers are assigned only at "
        "posting (a future session). `company_id` must reference an existing, active, "
        "non-deleted company for the caller's tenant (404 if not found, 422 if inactive). "
        "No allocation, posting or outstanding-balance logic runs here - that arrives in "
        "later sessions."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_COMPANY_NOT_FOUND_RESPONSE,
        **_COMPANY_INACTIVE_RESPONSE,
        201: {"content": {"application/json": {"example": _PAYMENT_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(PAYMENT_CREATE))],
)
async def create_payment(
    payload: PaymentCreateRequest,
    current_user: User = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    return await service.create(payload, tenant_id=current_user.tenant_id, actor_id=current_user.id)


@router.get(
    "",
    response_model=PaginatedResponse[PaymentResponse],
    summary="Search, filter, sort and paginate payments",
    description=(
        "Every non-deleted payment for the caller's tenant. `q` searches payment_number, "
        "reference_number and the paying company's name (case-insensitive substring). "
        "Combine with status/company_id/payment_method/payment_date_from/payment_date_to "
        "filters, `sort` (one of `payment_date`, `payment_number`, `amount`, `created_at`; "
        "prefix with `-` for descending, e.g. `-payment_date`) and page/page_size."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        200: {"content": {"application/json": {"example": _LIST_RESPONSE_EXAMPLE}}},
        422: {
            "model": ErrorResponse,
            "description": "Invalid sort field, or page/page_size out of range",
        },
    },
    dependencies=[Depends(require_permission(PAYMENT_VIEW))],
)
async def list_payments(
    params: Annotated[PaymentListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> PaginatedResponse[PaymentResponse]:
    return await service.list_payments(tenant_id=current_user.tenant_id, params=params)


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="Get a payment by id",
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        200: {"content": {"application/json": {"example": _PAYMENT_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(PAYMENT_VIEW))],
)
async def get_payment(
    payment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    return await service.get(payment_id, tenant_id=current_user.tenant_id)


@router.put(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="Update a draft payment",
    description=(
        "Partial update: only fields present in the request body are changed. Only "
        "`draft` payments may be updated (409 otherwise). A soft-deleted payment is "
        "treated as not found. If `company_id` is included and differs from the current "
        "company, the new company must exist and be active (404/422). If `amount` "
        "changes, `unallocated_amount` is recomputed from it (`allocated_amount` stays 0 "
        "in this session, so `unallocated_amount` always ends up equal to `amount`)."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_COMPANY_NOT_FOUND_RESPONSE,
        **_COMPANY_INACTIVE_RESPONSE,
        **_NOT_DRAFT_RESPONSE,
        200: {
            "content": {
                "application/json": {"example": {**_PAYMENT_EXAMPLE, "remarks": "Revised amount"}}
            }
        },
    },
    dependencies=[Depends(require_permission(PAYMENT_EDIT))],
)
async def update_payment(
    payment_id: uuid.UUID,
    payload: PaymentUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    return await service.update(
        payment_id, payload, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.delete(
    "/{payment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a draft payment",
    description=(
        "Sets deleted_at/deleted_by rather than removing the row (ARCHITECTURE.md §38). "
        "Only `draft` payments may be deleted (409 otherwise) - CLAUDE.md's \"Payments are "
        'never deleted" business rule applies once a payment is posted, the same '
        "immutability boundary Invoice draws at `issued`."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE, **_NOT_DRAFT_RESPONSE},
    dependencies=[Depends(require_permission(PAYMENT_DELETE))],
)
async def delete_payment(
    payment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> None:
    await service.delete(payment_id, tenant_id=current_user.tenant_id, actor_id=current_user.id)


@router.post(
    "/{payment_id}/allocations",
    response_model=PaymentAllocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Allocate a draft payment against an invoice",
    description=(
        "Only `draft` payments may receive allocations (409 otherwise). `invoice_id` must "
        "reference an existing, non-deleted invoice for the caller's tenant that is "
        "`issued` or `partially_paid` (404 if not found, 422 if draft/cancelled/paid). "
        "`allocated_amount` must not exceed the invoice's current `balance_amount` nor the "
        "payment's current `unallocated_amount` (422 otherwise). On success, the whole "
        "outstanding engine runs in one transaction: `Payment.allocated_amount`/"
        "`unallocated_amount` are recalculated from the sum of all active allocations, "
        "then `Invoice.paid_amount`/`balance_amount`/`status` are recalculated from the "
        "sum of every allocation against that invoice across all payments "
        "(`issued` -> `partially_paid` -> `paid` as `balance_amount` falls to 0), and "
        "finally the invoice's billed `Company.outstanding_amount` is recalculated from "
        "the sum of every still-open invoice's `balance_amount` - never incremented, "
        "always recomputed from source."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_ALLOCATION_INVOICE_NOT_FOUND_RESPONSE,
        **_ALLOCATION_BUSINESS_RULE_RESPONSE,
        **_ALLOCATION_NOT_DRAFT_RESPONSE,
        201: {"content": {"application/json": {"example": _ALLOCATION_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(PAYMENT_CREATE))],
)
async def create_payment_allocation(
    payment_id: uuid.UUID,
    payload: PaymentAllocationCreateRequest,
    current_user: User = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentAllocationResponse:
    return await service.create_allocation(
        payment_id, payload, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.get(
    "/{payment_id}/allocations",
    response_model=list[PaymentAllocationResponse],
    summary="List the allocations on a payment",
    description=(
        "Every allocation on this payment, oldest first - allowed regardless of payment "
        "status (only create/update/delete are draft-only). No pagination - a payment's "
        "allocation count is small and bounded."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        200: {"content": {"application/json": {"example": _ALLOCATION_LIST_RESPONSE_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(PAYMENT_VIEW))],
)
async def list_payment_allocations(
    payment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> list[PaymentAllocationResponse]:
    return await service.list_allocations(payment_id, tenant_id=current_user.tenant_id)


@router.put(
    "/{payment_id}/allocations/{allocation_id}",
    response_model=PaymentAllocationResponse,
    summary="Update an allocation on a draft payment",
    description=(
        "Partial update: only fields present in the request body are changed. Only "
        "allocations on `draft` payments may be updated (409 otherwise). The full merged "
        "state (invoice_id, allocated_amount) is revalidated on every update, regardless "
        "of which fields changed - same rules as creating an allocation (404/422 as "
        "appropriate), except that editing an allocation against the invoice it already "
        "targets is still allowed even if that invoice has since become `paid` (possibly "
        "as a result of this very allocation) - only *retargeting* onto a different "
        "invoice requires it to still be `issued` or `partially_paid`. "
        "`Payment.allocated_amount`/`unallocated_amount`, the affected invoice(s)' "
        "`paid_amount`/`balance_amount`/`status`, and their billed compan(y/ies)' "
        "`outstanding_amount` are all recalculated from source afterwards - see the "
        "create endpoint's description for the full cascade."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_ALLOCATION_NOT_FOUND_RESPONSE,
        **_ALLOCATION_INVOICE_NOT_FOUND_RESPONSE,
        **_ALLOCATION_BUSINESS_RULE_RESPONSE,
        **_ALLOCATION_NOT_DRAFT_RESPONSE,
        200: {
            "content": {
                "application/json": {
                    "example": {**_ALLOCATION_EXAMPLE, "allocated_amount": "150000.00"}
                }
            }
        },
    },
    dependencies=[Depends(require_permission(PAYMENT_EDIT))],
)
async def update_payment_allocation(
    payment_id: uuid.UUID,
    allocation_id: uuid.UUID,
    payload: PaymentAllocationUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentAllocationResponse:
    return await service.update_allocation(
        payment_id, allocation_id, payload, tenant_id=current_user.tenant_id
    )


@router.delete(
    "/{payment_id}/allocations/{allocation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an allocation from a draft payment",
    description=(
        "Hard-deletes the allocation row - PaymentAllocation carries no deleted_at, "
        "unlike Payment itself (see its docstring). Only allocations on `draft` payments "
        "may be removed (409 otherwise). `Payment.allocated_amount`/`unallocated_amount` "
        "are recalculated afterwards (the removed allocation's amount is restored to "
        "`unallocated_amount`), and the affected invoice's `paid_amount`/`balance_amount`/"
        "`status` and its billed company's `outstanding_amount` are recalculated from "
        "source too - a removed allocation can move an invoice back down from `paid` to "
        "`partially_paid`, or from `partially_paid`/`paid` to `issued`."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_ALLOCATION_NOT_FOUND_RESPONSE,
        **_ALLOCATION_NOT_DRAFT_RESPONSE,
        **_ALLOCATION_BUSINESS_RULE_RESPONSE,
    },
    dependencies=[Depends(require_permission(PAYMENT_DELETE))],
)
async def delete_payment_allocation(
    payment_id: uuid.UUID,
    allocation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> None:
    await service.delete_allocation(payment_id, allocation_id, tenant_id=current_user.tenant_id)


@router.post(
    "/{payment_id}/post",
    response_model=PaymentResponse,
    summary="Post a draft payment",
    description=(
        "The core business transaction of this module (TASKS.md Sprint 10 Session 5) - "
        "irreversibly transitions `draft` to `posted`, inside one database transaction: "
        "the payment row is locked (`SELECT ... FOR UPDATE`), its `allocated_amount`/"
        "`unallocated_amount` are recalculated server-side from its current allocations, "
        "a sequential `payment_number` is assigned (`PAY/{fiscal_year}/{seq}`, "
        "concurrency-safe via a locked per-tenant counter row), and the payment is marked "
        "`posted` - all committed together or none of it is. Requires the `draft` status "
        "(409 if already posted or cancelled) and at least one allocation (422 if none). "
        "`Invoice.paid_amount`/`balance_amount`/`status` and `Company.outstanding_amount` "
        "are NOT touched here - the Session 4 outstanding engine already keeps them "
        "correct as of every allocation change made while this payment was draft. Once "
        "posted, the payment and its allocations become fully immutable: no further "
        "edit, delete, or allocation create/update/delete is possible (409 on any "
        "attempt). Ledger posting, receipt generation, outbox event publishing and bank "
        "reconciliation are not implemented yet - reserved for future sprints."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        **_NOT_DRAFT_FOR_POSTING_RESPONSE,
        **_POST_BUSINESS_RULE_RESPONSE,
        200: {"content": {"application/json": {"example": _POSTED_PAYMENT_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(PAYMENT_POST))],
)
async def post_payment(
    payment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    return await service.post(
        payment_id, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )
