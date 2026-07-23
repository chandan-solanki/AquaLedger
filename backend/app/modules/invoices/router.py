import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.common.schemas import ErrorResponse, PaginatedResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.invoices.dependencies import get_invoice_service
from app.modules.invoices.permissions import (
    INVOICE_CREATE,
    INVOICE_DELETE,
    INVOICE_EDIT,
    INVOICE_ISSUE,
    INVOICE_VIEW,
)
from app.modules.invoices.schemas import (
    InvoiceCreateRequest,
    InvoiceItemCreateRequest,
    InvoiceItemResponse,
    InvoiceItemUpdateRequest,
    InvoiceListParams,
    InvoiceResponse,
    InvoiceUpdateRequest,
)
from app.modules.invoices.service import InvoiceService

router = APIRouter(prefix="/invoices", tags=["invoices"])


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
    field_errors and fires before the service layer ever runs, e.g. quantity
    <= 0 or discount_percent/tax_rate out of the 0-100 range."""
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
        "description": "Invoice not found",
        "content": {
            "application/json": {
                "example": _error_example("INVOICE_NOT_FOUND", "Invoice not found")
            }
        },
    },
}
_COMPANY_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Invoice not found, or referenced company not found",
        "content": {
            "application/json": {
                "examples": {
                    "invoice_not_found": {
                        "summary": "Invoice does not exist for this tenant",
                        "value": _error_example("INVOICE_NOT_FOUND", "Invoice not found"),
                    },
                    "company_not_found": {
                        "summary": "company_id does not exist for this tenant",
                        "value": _error_example(
                            "INVOICE_COMPANY_NOT_FOUND", "The specified company does not exist"
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
                    "INVOICE_COMPANY_INACTIVE", "The specified company is not active"
                )
            }
        },
    },
}
_NOT_DRAFT_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "The invoice is no longer DRAFT and cannot be edited or deleted",
        "content": {
            "application/json": {
                "example": _error_example(
                    "INVOICE_NOT_DRAFT", "Only draft invoices can be edited or deleted"
                )
            }
        },
    },
}
_ITEM_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Invoice not found, or invoice item not found",
        "content": {
            "application/json": {
                "examples": {
                    "invoice_not_found": {
                        "summary": "Invoice does not exist for this tenant",
                        "value": _error_example("INVOICE_NOT_FOUND", "Invoice not found"),
                    },
                    "item_not_found": {
                        "summary": "item_id does not exist on this invoice for this tenant",
                        "value": _error_example("INVOICE_ITEM_NOT_FOUND", "Invoice item not found"),
                    },
                }
            }
        },
    },
}
_ITEM_REFERENCE_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": (
            "Invoice not found, invoice item not found, referenced trip catch not found, "
            "or referenced fish not found"
        ),
        "content": {
            "application/json": {
                "examples": {
                    "invoice_not_found": {
                        "summary": "Invoice does not exist for this tenant",
                        "value": _error_example("INVOICE_NOT_FOUND", "Invoice not found"),
                    },
                    "item_not_found": {
                        "summary": "item_id does not exist on this invoice for this tenant",
                        "value": _error_example("INVOICE_ITEM_NOT_FOUND", "Invoice item not found"),
                    },
                    "trip_catch_not_found": {
                        "summary": "trip_catch_id does not exist for this tenant",
                        "value": _error_example(
                            "INVOICE_ITEM_TRIP_CATCH_NOT_FOUND",
                            "The specified trip catch does not exist",
                        ),
                    },
                    "fish_not_found": {
                        "summary": "fish_id does not exist for this tenant",
                        "value": _error_example(
                            "INVOICE_ITEM_FISH_NOT_FOUND", "The specified fish does not exist"
                        ),
                    },
                }
            }
        },
    },
}
_ITEM_BUSINESS_RULE_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": (
            "Business rule violation: fish_id does not match the trip catch's fish, or "
            "quantity exceeds the trip catch's available_quantity"
        ),
        "content": {
            "application/json": {
                "examples": {
                    "fish_mismatch": {
                        "summary": "fish_id doesn't match trip_catch's fish",
                        "value": _error_example(
                            "INVOICE_ITEM_FISH_MISMATCH",
                            "The specified fish does not match the trip catch's fish",
                        ),
                    },
                    "quantity_exceeds_available": {
                        "summary": "quantity is greater than the trip catch's available_quantity",
                        "value": _error_example(
                            "INVOICE_ITEM_QUANTITY_EXCEEDS_AVAILABLE",
                            "Quantity exceeds the trip catch's available quantity",
                        ),
                    },
                    "quantity_not_positive": {
                        "summary": "quantity is zero or negative (pydantic-level, not a "
                        "business-rule error - fires before the service layer runs)",
                        "value": _validation_error_example(
                            "quantity", "Input should be greater than 0"
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
                    "INVOICE_CALCULATION_ERROR",
                    "Computed total 1000000000000.00 exceeds 999999999999.99",
                )
            }
        },
    },
}

_EMPTY_INVOICE_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": "Business rule violation on issue",
        "content": {
            "application/json": {
                "examples": {
                    "empty_invoice": {
                        "summary": "Invoice has no active line items",
                        "value": _error_example(
                            "INVOICE_EMPTY", "An invoice must have at least one item to be issued"
                        ),
                    },
                    "company_inactive": {
                        "summary": "The billed company is no longer active",
                        "value": _error_example(
                            "INVOICE_COMPANY_INACTIVE", "The specified company is not active"
                        ),
                    },
                    "insufficient_inventory": {
                        "summary": "An item's quantity exceeds its trip catch's "
                        "available_quantity, revalidated under lock at issue time",
                        "value": _error_example(
                            "INVOICE_INSUFFICIENT_INVENTORY",
                            "Quantity exceeds the trip catch's available quantity",
                        ),
                    },
                }
            }
        },
    },
}
_ALREADY_ISSUED_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "The invoice is not DRAFT - already issued, already cancelled, "
        "or otherwise not eligible to be issued again",
        "content": {
            "application/json": {
                "example": _error_example(
                    "INVOICE_NOT_DRAFT", "Only draft invoices can be edited or deleted"
                )
            }
        },
    },
}

_ISSUED_INVOICE_EXAMPLE: dict[str, object] = {
    "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c03",
    "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
    "company_id": "019f7af3-83ae-783a-b139-40a239786b30",
    "invoice_number": "INV/2026-27/00001",
    "invoice_date": "2026-07-22",
    "due_date": "2026-08-06",
    "status": "issued",
    "subtotal": "23625.00",
    "discount_amount": "0.00",
    "taxable_amount": "22500.00",
    "tax_amount": "1125.00",
    "transport_charge": "250.00",
    "other_charge": "0.00",
    "round_off": "0.00",
    "total_amount": "23875.00",
    "paid_amount": "0.00",
    "balance_amount": "23875.00",
    "remarks": "Weekly settlement",
    "issued_at": "2026-07-22T04:05:00Z",
    "created_at": "2026-07-22T04:00:00Z",
    "updated_at": "2026-07-22T04:05:00Z",
}

_INVOICE_EXAMPLE: dict[str, object] = {
    "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c03",
    "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
    "company_id": "019f7af3-83ae-783a-b139-40a239786b30",
    "invoice_number": None,
    "invoice_date": "2026-07-22",
    "due_date": "2026-08-06",
    "status": "draft",
    "subtotal": "0.00",
    "discount_amount": "0.00",
    "taxable_amount": "0.00",
    "tax_amount": "0.00",
    "transport_charge": "250.00",
    "other_charge": "0.00",
    "round_off": "0.00",
    "total_amount": "250.00",
    "paid_amount": "0.00",
    "balance_amount": "250.00",
    "remarks": "Weekly settlement",
    "issued_at": None,
    "created_at": "2026-07-22T04:00:00Z",
    "updated_at": "2026-07-22T04:00:00Z",
}

_PARTIALLY_PAID_INVOICE_EXAMPLE: dict[str, object] = {
    **_ISSUED_INVOICE_EXAMPLE,
    "status": "partially_paid",
    "paid_amount": "15000.00",
    "balance_amount": "8875.00",
}

_PAID_INVOICE_EXAMPLE: dict[str, object] = {
    **_ISSUED_INVOICE_EXAMPLE,
    "status": "paid",
    "paid_amount": "23875.00",
    "balance_amount": "0.00",
}

_LIST_RESPONSE_EXAMPLE: dict[str, object] = {
    "data": [_INVOICE_EXAMPLE],
    "meta": {
        "total_records": 1,
        "total_pages": 1,
        "current_page": 1,
        "page_size": 20,
        "has_next": False,
        "has_previous": False,
    },
}

_INVOICE_ITEM_EXAMPLE: dict[str, object] = {
    "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c02",
    "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
    "invoice_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c03",
    "line_number": 1,
    "fish_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
    "trip_catch_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c04",
    "description": "Pomfret - Grade A",
    "quantity": "50.000",
    "unit": "kg",
    "rate": "450.0000",
    "discount_percent": "0.00",
    "discount_amount": "0.00",
    "taxable_amount": "22500.00",
    "tax_rate": "5.00",
    "tax_amount": "1125.00",
    "line_total": "23625.00",
    "created_at": "2026-07-22T04:00:00Z",
    "updated_at": "2026-07-22T04:00:00Z",
}


@router.post(
    "",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft invoice",
    description=(
        "Always created in `draft` status with `invoice_number` NULL. `transport_charge`/"
        "`other_charge` are the only financial inputs accepted (default 0); every "
        "*calculated* field (subtotal/discount_amount/taxable_amount/tax_amount/"
        "total_amount/balance_amount) is computed server-side by the financial engine "
        "(app.modules.invoices.domain.totals) and folds transport_charge/other_charge into "
        "total_amount immediately, even before any items exist. The invoice number is "
        "assigned only at issue (Session 5). `company_id` must reference an existing, "
        "active, non-deleted company for the caller's tenant (404 if not found, 422 if "
        "inactive)."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_COMPANY_NOT_FOUND_RESPONSE,
        **_COMPANY_INACTIVE_RESPONSE,
        **_CALCULATION_ERROR_RESPONSE,
        201: {"content": {"application/json": {"example": _INVOICE_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(INVOICE_CREATE))],
)
async def create_invoice(
    payload: InvoiceCreateRequest,
    current_user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceResponse:
    return await service.create(payload, tenant_id=current_user.tenant_id, actor_id=current_user.id)


@router.get(
    "",
    response_model=PaginatedResponse[InvoiceResponse],
    summary="Search, filter, sort and paginate invoices",
    description=(
        "Every non-deleted invoice for the caller's tenant. `q` searches invoice_number "
        "and the billed company's name (case-insensitive substring). Combine with "
        "status/company_id/invoice_date_from/invoice_date_to filters, `sort` (one of "
        "`invoice_date`, `invoice_number`, `created_at`; prefix with `-` for descending, "
        "e.g. `-invoice_date`) and page/page_size."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        200: {"content": {"application/json": {"example": _LIST_RESPONSE_EXAMPLE}}},
        422: {
            "model": ErrorResponse,
            "description": "Invalid sort field, or page/page_size out of range",
        },
    },
    dependencies=[Depends(require_permission(INVOICE_VIEW))],
)
async def list_invoices(
    params: Annotated[InvoiceListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
) -> PaginatedResponse[InvoiceResponse]:
    return await service.list_invoices(tenant_id=current_user.tenant_id, params=params)


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Get an invoice by id",
    description=(
        "`paid_amount`/`balance_amount`/`status` reflect the outstanding engine's latest "
        "recalculation (Sprint 10 Session 4): `issued` (nothing allocated yet) -> "
        "`partially_paid` (`balance_amount` > 0) -> `paid` (`balance_amount` == 0), "
        "driven entirely by payment allocations against this invoice - see the examples."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "draft": {
                            "summary": "Draft - not yet issued",
                            "value": _INVOICE_EXAMPLE,
                        },
                        "issued": {
                            "summary": "Issued - no payment allocated yet",
                            "value": _ISSUED_INVOICE_EXAMPLE,
                        },
                        "partially_paid": {
                            "summary": "Partially paid - some balance remains",
                            "value": _PARTIALLY_PAID_INVOICE_EXAMPLE,
                        },
                        "paid": {
                            "summary": "Fully paid - balance_amount is 0",
                            "value": _PAID_INVOICE_EXAMPLE,
                        },
                    }
                }
            }
        },
    },
    dependencies=[Depends(require_permission(INVOICE_VIEW))],
)
async def get_invoice(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceResponse:
    return await service.get(invoice_id, tenant_id=current_user.tenant_id)


@router.put(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Update a draft invoice",
    description=(
        "Partial update: only fields present in the request body are changed. Only "
        "`draft` invoices may be updated (409 otherwise - issued/paid/cancelled invoices "
        "are immutable). A soft-deleted invoice is treated as not found. If `company_id` "
        "is included and differs from the current company, the new company must exist "
        "and be active (404/422). Every financial total is unconditionally recalculated "
        "afterwards (app.modules.invoices.domain.totals) - not only when "
        "transport_charge/other_charge change."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_COMPANY_NOT_FOUND_RESPONSE,
        **_COMPANY_INACTIVE_RESPONSE,
        **_NOT_DRAFT_RESPONSE,
        **_CALCULATION_ERROR_RESPONSE,
        200: {
            "content": {
                "application/json": {"example": {**_INVOICE_EXAMPLE, "remarks": "Revised due date"}}
            }
        },
    },
    dependencies=[Depends(require_permission(INVOICE_EDIT))],
)
async def update_invoice(
    invoice_id: uuid.UUID,
    payload: InvoiceUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceResponse:
    return await service.update(
        invoice_id, payload, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.delete(
    "/{invoice_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a draft invoice",
    description=(
        "Sets deleted_at/deleted_by rather than removing the row (ARCHITECTURE.md §38). "
        "Only `draft` invoices may be deleted (409 otherwise)."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE, **_NOT_DRAFT_RESPONSE},
    dependencies=[Depends(require_permission(INVOICE_DELETE))],
)
async def delete_invoice(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
) -> None:
    await service.delete(invoice_id, tenant_id=current_user.tenant_id, actor_id=current_user.id)


@router.post(
    "/{invoice_id}/items",
    response_model=InvoiceItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a line item to a draft invoice",
    description=(
        "Only `draft` invoices may receive new items (409 otherwise). `trip_catch_id` "
        "must reference an existing, non-deleted trip catch for the caller's tenant, and "
        "`fish_id` must reference an existing, non-deleted fish for the caller's tenant "
        "(404 if either is not found). The trip catch's fish must match `fish_id` (422 "
        "otherwise), and `quantity` must not exceed the trip catch's available_quantity "
        "(422 otherwise) - validated only, never deducted or reserved here (that happens "
        "only in the Session 5 issue workflow). `line_number` is assigned server-side. "
        "`discount_amount`/`taxable_amount`/`tax_amount`/`line_total` are computed "
        "server-side (app.modules.invoices.domain.totals) from `quantity`/`rate`/"
        "`discount_percent`/`tax_rate` - any such field in the request body is ignored - "
        "and the invoice's own totals are recalculated in the same transaction."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_ITEM_REFERENCE_NOT_FOUND_RESPONSE,
        **_ITEM_BUSINESS_RULE_RESPONSE,
        **_NOT_DRAFT_RESPONSE,
        **_CALCULATION_ERROR_RESPONSE,
        201: {"content": {"application/json": {"example": _INVOICE_ITEM_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(INVOICE_CREATE))],
)
async def add_invoice_item(
    invoice_id: uuid.UUID,
    payload: InvoiceItemCreateRequest,
    current_user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceItemResponse:
    return await service.add_item(
        invoice_id, payload, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


_ITEM_LIST_RESPONSE_EXAMPLE: list[dict[str, object]] = [_INVOICE_ITEM_EXAMPLE]


@router.get(
    "/{invoice_id}/items",
    response_model=list[InvoiceItemResponse],
    summary="List the line items on an invoice",
    description=(
        "Every non-deleted item on this invoice, ordered by line_number - allowed "
        "regardless of invoice status (only add/edit/delete are draft-only). `q` "
        "searches the item's description and the sold fish's name (case-insensitive "
        "substring). No pagination - an invoice's line count is small and bounded."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        200: {"content": {"application/json": {"example": _ITEM_LIST_RESPONSE_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(INVOICE_VIEW))],
)
async def list_invoice_items(
    invoice_id: uuid.UUID,
    q: Annotated[
        str | None,
        Query(
            max_length=255,
            description="Case-insensitive search across description and fish name.",
            examples=["Pomfret"],
        ),
    ] = None,
    current_user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
) -> list[InvoiceItemResponse]:
    return await service.list_items(invoice_id, tenant_id=current_user.tenant_id, q=q)


@router.put(
    "/{invoice_id}/items/{item_id}",
    response_model=InvoiceItemResponse,
    summary="Update a line item on a draft invoice",
    description=(
        "Partial update: only fields present in the request body are changed. Only "
        "items on `draft` invoices may be updated (409 otherwise). A soft-deleted item "
        "is treated as not found. The full merged state (trip catch, fish, quantity) is "
        "revalidated on every update, regardless of which fields changed - same rules "
        "as adding an item (404/422 as appropriate). discount_amount/taxable_amount/"
        "tax_amount/line_total are recomputed from the resulting quantity/rate/"
        "discount_percent/tax_rate, and the invoice's own totals are recalculated in the "
        "same transaction."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_ITEM_REFERENCE_NOT_FOUND_RESPONSE,
        **_ITEM_BUSINESS_RULE_RESPONSE,
        **_NOT_DRAFT_RESPONSE,
        **_CALCULATION_ERROR_RESPONSE,
        200: {
            "content": {
                "application/json": {"example": {**_INVOICE_ITEM_EXAMPLE, "quantity": "40.000"}}
            }
        },
    },
    dependencies=[Depends(require_permission(INVOICE_EDIT))],
)
async def update_invoice_item(
    invoice_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: InvoiceItemUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceItemResponse:
    return await service.update_item(
        invoice_id, item_id, payload, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.delete(
    "/{invoice_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a line item from a draft invoice",
    description=(
        "Sets deleted_at/deleted_by rather than removing the row (ARCHITECTURE.md §38). "
        "Only items on `draft` invoices may be deleted (409 otherwise). No inventory "
        "changes - the trip catch's available_quantity is untouched. The invoice's own "
        "totals are recalculated from the remaining items in the same transaction."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_ITEM_NOT_FOUND_RESPONSE, **_NOT_DRAFT_RESPONSE},
    dependencies=[Depends(require_permission(INVOICE_DELETE))],
)
async def delete_invoice_item(
    invoice_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
) -> None:
    await service.delete_item(
        invoice_id, item_id, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.post(
    "/{invoice_id}/issue",
    response_model=InvoiceResponse,
    summary="Issue a draft invoice",
    description=(
        "The core business transaction of this module (ARCHITECTURE.md §13.3) - "
        "irreversibly transitions `draft` to `issued`, inside one database transaction: "
        "the invoice row is locked (`SELECT ... FOR UPDATE`), all totals are recalculated "
        "server-side from its current items, a sequential `invoice_number` is assigned "
        "(`INV/{fiscal_year}/{seq}`, concurrency-safe via a locked per-tenant counter "
        "row), every referenced trip catch is locked and its `available_quantity` "
        "revalidated and deducted (`available_quantity -= quantity`, "
        "`sold_quantity += quantity`), and the billed company's `outstanding_amount` is "
        "increased by `total_amount` - all committed together or none of it is. Requires "
        "the `draft` status (409 if already issued or cancelled), at least one active "
        "line item (422 if empty), an active company (422 if inactive), and sufficient "
        "`available_quantity` on every referenced trip catch (422 if not, even if it was "
        "sufficient when the item was added - this is the final, lock-protected check). "
        "Once issued, the invoice and its items become fully immutable: no further edit, "
        "delete, or item CRUD is possible (409 INVOICE_NOT_DRAFT on any attempt). From "
        "this point, `paid_amount`/`balance_amount`/`status` are recalculated automatically "
        "whenever a payment is allocated against this invoice (see the payments module's "
        "allocation endpoints) - `issued` -> `partially_paid` -> `paid` as `balance_amount` "
        "falls to 0. Ledger posting, PDF generation and outbox event publishing are not "
        "implemented yet - reserved for future sprints."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_COMPANY_NOT_FOUND_RESPONSE,
        **_EMPTY_INVOICE_RESPONSE,
        **_ALREADY_ISSUED_RESPONSE,
        **_CALCULATION_ERROR_RESPONSE,
        200: {"content": {"application/json": {"example": _ISSUED_INVOICE_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(INVOICE_ISSUE))],
)
async def issue_invoice(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceResponse:
    return await service.issue(
        invoice_id, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )
