import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

# Registers PurchaseOrderDocumentRenderer for DocumentType.PURCHASE_ORDER into the shared
# DocumentRegistry singleton, mirroring app.modules.purchase.router's own registration import.
import app.modules.purchase_orders.document_renderer as _purchase_order_document_renderer  # noqa: F401
from app.common.schemas import ErrorResponse, PaginatedResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.documents.constants import PartyType, SourceType
from app.modules.documents.dependencies import get_document_record_service
from app.modules.documents.service import DocumentRecordService
from app.modules.purchase.dependencies import get_purchase_service
from app.modules.purchase.service import PurchaseService
from app.modules.purchase_orders.dependencies import get_purchase_order_service
from app.modules.purchase_orders.document_builder import build_purchase_order_document_data
from app.modules.purchase_orders.domain.billing import OrderedItem, derive_billing_summary
from app.modules.purchase_orders.permissions import (
    PURCHASE_ORDER_CANCEL,
    PURCHASE_ORDER_CONFIRM,
    PURCHASE_ORDER_CREATE,
    PURCHASE_ORDER_DELETE,
    PURCHASE_ORDER_EDIT,
    PURCHASE_ORDER_FULFILL,
    PURCHASE_ORDER_VIEW,
)
from app.modules.purchase_orders.schemas import (
    PurchaseOrderCreateRequest,
    PurchaseOrderDetailResponse,
    PurchaseOrderItemBillingResponse,
    PurchaseOrderItemCreateRequest,
    PurchaseOrderItemListParams,
    PurchaseOrderItemResponse,
    PurchaseOrderItemUpdateRequest,
    PurchaseOrderLinkedBillResponse,
    PurchaseOrderListParams,
    PurchaseOrderResponse,
    PurchaseOrderUpdateRequest,
)
from app.modules.purchase_orders.service import PurchaseOrderService

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])


def _error_example(code: str, message: str) -> dict[str, object]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": None,
            "field_errors": None,
            "request_id": "e9fefc78-4d47-4788-8d33-427f5b7852c8",
            "timestamp": "2026-08-15T04:00:00Z",
        }
    }


_COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Missing required permission"},
}
_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Purchase order not found",
        "content": {
            "application/json": {
                "example": _error_example("PURCHASE_ORDER_NOT_FOUND", "Purchase order not found")
            }
        },
    },
}
_SUPPLIER_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Purchase order not found, or referenced supplier not found",
        "content": {
            "application/json": {
                "examples": {
                    "purchase_order_not_found": {
                        "summary": "Purchase order does not exist for this tenant",
                        "value": _error_example(
                            "PURCHASE_ORDER_NOT_FOUND", "Purchase order not found"
                        ),
                    },
                    "supplier_not_found": {
                        "summary": "supplier_id does not exist for this tenant",
                        "value": _error_example(
                            "PURCHASE_ORDER_SUPPLIER_NOT_FOUND",
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
                    "PURCHASE_ORDER_SUPPLIER_INACTIVE", "The specified supplier is not active"
                )
            }
        },
    },
}
_NOT_DRAFT_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "The purchase order is no longer DRAFT and cannot be edited or deleted",
        "content": {
            "application/json": {
                "example": _error_example(
                    "PURCHASE_ORDER_NOT_DRAFT",
                    "Only draft purchase orders can be edited, deleted, or confirmed",
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
                                "timestamp": "2026-08-15T04:00:00Z",
                            }
                        },
                    },
                    "supplier_inactive": {
                        "summary": "The referenced supplier is not active",
                        "value": _error_example(
                            "PURCHASE_ORDER_SUPPLIER_INACTIVE",
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
        "description": "Purchase order not found, or purchase order item not found",
        "content": {
            "application/json": {
                "examples": {
                    "purchase_order_not_found": {
                        "summary": "purchase_order_id does not exist for this tenant",
                        "value": _error_example(
                            "PURCHASE_ORDER_NOT_FOUND", "Purchase order not found"
                        ),
                    },
                    "item_not_found": {
                        "summary": "item_id does not exist on this purchase order for this tenant",
                        "value": _error_example(
                            "PURCHASE_ORDER_ITEM_NOT_FOUND", "Purchase order item not found"
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
                    "PURCHASE_ORDER_CALCULATION_ERROR",
                    "Computed total 1000000000000.00 exceeds 999999999999.99",
                )
            }
        },
    },
}
_EMPTY_ORDER_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": "Business rule violation on confirm",
        "content": {
            "application/json": {
                "examples": {
                    "empty_order": {
                        "summary": "Purchase order has no items",
                        "value": _error_example(
                            "PURCHASE_ORDER_EMPTY",
                            "A purchase order must have at least one item to be confirmed",
                        ),
                    },
                    "totals_invalid": {
                        "summary": "The final pre-confirm recalculation rejected a computed "
                        "total - not reachable through normal input",
                        "value": _error_example(
                            "PURCHASE_ORDER_TOTALS_INVALID",
                            "Computed total 1000000000000.00 exceeds 999999999999.99",
                        ),
                    },
                }
            }
        },
    },
}
_NOT_CONFIRMABLE_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": (
            "The purchase order is not DRAFT - already confirmed, fulfilled, or cancelled"
        ),
        "content": {
            "application/json": {
                "example": _error_example(
                    "PURCHASE_ORDER_NOT_DRAFT",
                    "Only draft purchase orders can be edited, deleted, or confirmed",
                )
            }
        },
    },
}
_NOT_CANCELLABLE_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "The purchase order is fulfilled or already cancelled",
        "content": {
            "application/json": {
                "example": _error_example(
                    "PURCHASE_ORDER_INVALID_TRANSITION",
                    "Only draft or confirmed purchase orders can be cancelled",
                )
            }
        },
    },
}
_NOT_FULFILLABLE_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "The purchase order is not CONFIRMED",
        "content": {
            "application/json": {
                "example": _error_example(
                    "PURCHASE_ORDER_INVALID_TRANSITION",
                    "Only confirmed purchase orders can be fulfilled",
                )
            }
        },
    },
}

_DOCUMENT_NOT_AVAILABLE_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": (
            "The purchase order has not been confirmed yet (or was cancelled directly "
            "from draft) - it has no po_number to print"
        ),
        "content": {
            "application/json": {
                "example": _error_example(
                    "PURCHASE_ORDER_DOCUMENT_NOT_AVAILABLE",
                    "The purchase order must be confirmed before its document can be generated",
                )
            }
        },
    },
}

_PURCHASE_ORDER_EXAMPLE: dict[str, object] = {
    "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c15",
    "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
    "supplier_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
    "po_number": None,
    "order_date": "2026-08-15",
    "expected_delivery_date": "2026-08-25",
    "status": "draft",
    "subtotal": "23625.00",
    "discount_amount": "0.00",
    "taxable_amount": "22500.00",
    "tax_amount": "1125.00",
    "transport_charge": "0.00",
    "other_charge": "0.00",
    "round_off": "0.00",
    "total_amount": "23625.00",
    "remarks": None,
    "confirmed_at": None,
    "created_at": "2026-08-15T04:00:00Z",
    "updated_at": "2026-08-15T04:00:00Z",
}
_EMPTY_PURCHASE_ORDER_EXAMPLE: dict[str, object] = {
    **_PURCHASE_ORDER_EXAMPLE,
    "subtotal": "0.00",
    "taxable_amount": "0.00",
    "tax_amount": "0.00",
    "total_amount": "0.00",
}
_CONFIRMED_PURCHASE_ORDER_EXAMPLE: dict[str, object] = {
    **_PURCHASE_ORDER_EXAMPLE,
    "po_number": "PO/2026-27/00001",
    "status": "confirmed",
    "confirmed_at": "2026-08-15T04:05:00Z",
}
_FULFILLED_PURCHASE_ORDER_EXAMPLE: dict[str, object] = {
    **_CONFIRMED_PURCHASE_ORDER_EXAMPLE,
    "status": "fulfilled",
}
_CANCELLED_PURCHASE_ORDER_EXAMPLE: dict[str, object] = {
    **_PURCHASE_ORDER_EXAMPLE,
    "status": "cancelled",
}
_LIST_RESPONSE_EXAMPLE: dict[str, object] = {
    "data": [_PURCHASE_ORDER_EXAMPLE],
    "meta": {
        "total_records": 1,
        "total_pages": 1,
        "current_page": 1,
        "page_size": 20,
        "has_next": False,
        "has_previous": False,
    },
}

_PURCHASE_ORDER_ITEM_EXAMPLE: dict[str, object] = {
    "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c16",
    "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
    "purchase_order_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c15",
    "line_number": 1,
    "description": "Pomfret - Grade A",
    "quantity": "50.000",
    "unit": "KG",
    "rate": "450.0000",
    "discount_percent": "0.00",
    "discount_amount": "0.00",
    "taxable_amount": "22500.00",
    "tax_rate": "5.00",
    "tax_amount": "1125.00",
    "line_total": "23625.00",
    "created_at": "2026-08-15T04:00:00Z",
    "updated_at": "2026-08-15T04:00:00Z",
}
_ITEM_LIST_RESPONSE_EXAMPLE: list[dict[str, object]] = [_PURCHASE_ORDER_ITEM_EXAMPLE]


@router.post(
    "",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft purchase order",
    description=(
        "Always created in `draft` status with `po_number`/`confirmed_at` NULL and no "
        "items, so every financial field (subtotal/discount_amount/taxable_amount/"
        "tax_amount/transport_charge/other_charge/round_off/total_amount) starts at 0 - "
        "none of those is accepted in the request body, the server always owns them. "
        "Add line items afterwards via `POST /{purchase_order_id}/items`. `supplier_id` "
        "must reference an existing, active, non-deleted supplier for the caller's "
        "tenant (404 if not found, 422 if inactive). Creating a purchase order never "
        "affects supplier outstanding, ledger, or any financial report - it is a "
        "procurement commitment, not a bill."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_SUPPLIER_NOT_FOUND_RESPONSE,
        **_SUPPLIER_INACTIVE_RESPONSE,
        201: {"content": {"application/json": {"example": _EMPTY_PURCHASE_ORDER_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(PURCHASE_ORDER_CREATE))],
)
async def create_purchase_order(
    payload: PurchaseOrderCreateRequest,
    current_user: User = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service),
) -> PurchaseOrderResponse:
    return await service.create(payload, tenant_id=current_user.tenant_id, actor_id=current_user.id)


@router.get(
    "",
    response_model=PaginatedResponse[PurchaseOrderResponse],
    summary="Search, filter, sort and paginate purchase orders",
    description=(
        "Every non-deleted purchase order for the caller's tenant. `q` searches "
        "po_number and the ordering supplier's name (case-insensitive substring). "
        "Combine with status/supplier_id/billable/order_date_from/order_date_to "
        "filters, `sort` (one of `order_date`, `po_number`, `created_at`; prefix "
        "with `-` for descending, e.g. `-order_date`) and page/page_size. "
        "`billable=true` restricts to CONFIRMED/FULFILLED orders - the set "
        "eligible for Purchase Bill linkage - for pickers like the Purchase Bill "
        "form's PO selector."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        200: {"content": {"application/json": {"example": _LIST_RESPONSE_EXAMPLE}}},
        422: {
            "model": ErrorResponse,
            "description": "Invalid sort field, or page/page_size out of range",
        },
    },
    dependencies=[Depends(require_permission(PURCHASE_ORDER_VIEW))],
)
async def list_purchase_orders(
    params: Annotated[PurchaseOrderListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service),
) -> PaginatedResponse[PurchaseOrderResponse]:
    return await service.list_purchase_orders(tenant_id=current_user.tenant_id, params=params)


@router.get(
    "/{purchase_order_id}",
    response_model=PurchaseOrderDetailResponse,
    summary="Get a purchase order by id",
    description=(
        "`status`/`po_number`/`confirmed_at` reflect the lifecycle: `draft` (editable, "
        "no number) -> `confirmed` (number assigned, immutable) -> `fulfilled` "
        "(terminal), with `cancelled` reachable from either `draft` or `confirmed`. "
        "`billed_amount`/`remaining_amount`/`billing_status` (Sprint 12 Session 12) are "
        "derived from linked purchase bill items - never stored, never affecting "
        "supplier outstanding, and never driving the order's own lifecycle."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "draft": {
                            "summary": "Draft - not yet confirmed",
                            "value": _PURCHASE_ORDER_EXAMPLE,
                        },
                        "confirmed": {
                            "summary": "Confirmed - number assigned, immutable",
                            "value": _CONFIRMED_PURCHASE_ORDER_EXAMPLE,
                        },
                        "fulfilled": {
                            "summary": "Fulfilled - terminal",
                            "value": _FULFILLED_PURCHASE_ORDER_EXAMPLE,
                        },
                        "cancelled": {
                            "summary": "Cancelled from draft or confirmed",
                            "value": _CANCELLED_PURCHASE_ORDER_EXAMPLE,
                        },
                    }
                }
            }
        },
    },
    dependencies=[Depends(require_permission(PURCHASE_ORDER_VIEW))],
)
async def get_purchase_order(
    purchase_order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service),
    purchase_service: PurchaseService = Depends(get_purchase_service),
) -> PurchaseOrderDetailResponse:
    order = await service.get(purchase_order_id, tenant_id=current_user.tenant_id)
    items = await service.list_items(
        purchase_order_id, tenant_id=current_user.tenant_id, q=None, sort="line_number"
    )
    billed_by_item = await purchase_service.get_billed_quantities_for_po_items(
        [item.id for item in items], tenant_id=current_user.tenant_id
    )
    summary = derive_billing_summary(
        [OrderedItem(id=item.id, quantity=item.quantity) for item in items],
        billed_by_item,
        total_amount=order.total_amount,
    )
    return PurchaseOrderDetailResponse(
        **order.model_dump(),
        billed_amount=summary.billed_amount,
        remaining_amount=summary.remaining_amount,
        billing_status=summary.billing_status,
    )


@router.put(
    "/{purchase_order_id}",
    response_model=PurchaseOrderResponse,
    summary="Update a draft purchase order",
    description=(
        "Partial update: only fields present in the request body are changed. Only "
        "`draft` purchase orders may be updated (409 otherwise). A soft-deleted "
        "purchase order is treated as not found. If `supplier_id` is included and "
        "differs from the current supplier, the new supplier must exist and be active "
        "(404/422). Financial fields/`po_number`/`status`/`confirmed_at` are not "
        "accepted here either."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_SUPPLIER_NOT_FOUND_RESPONSE,
        **_SUPPLIER_INACTIVE_RESPONSE,
        **_NOT_DRAFT_RESPONSE,
        200: {
            "content": {
                "application/json": {
                    "example": {**_PURCHASE_ORDER_EXAMPLE, "remarks": "Delivery pushed a week"}
                }
            }
        },
    },
    dependencies=[Depends(require_permission(PURCHASE_ORDER_EDIT))],
)
async def update_purchase_order(
    purchase_order_id: uuid.UUID,
    payload: PurchaseOrderUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service),
) -> PurchaseOrderResponse:
    return await service.update(
        purchase_order_id, payload, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.delete(
    "/{purchase_order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a draft purchase order",
    description=(
        "Sets deleted_at/deleted_by rather than removing the row (ARCHITECTURE.md §38). "
        "Only `draft` purchase orders may be deleted (409 otherwise)."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE, **_NOT_DRAFT_RESPONSE},
    dependencies=[Depends(require_permission(PURCHASE_ORDER_DELETE))],
)
async def delete_purchase_order(
    purchase_order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service),
) -> None:
    await service.delete(
        purchase_order_id, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.post(
    "/{purchase_order_id}/items",
    response_model=PurchaseOrderItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a line item to a draft purchase order",
    description=(
        "Only `draft` purchase orders may receive new items (409 otherwise). "
        "`line_number` is assigned server-side - sequential, starting at 1, never "
        "reused even if a later item is deleted. `discount_amount`/`taxable_amount`/"
        "`tax_amount`/`line_total` are computed server-side "
        "(app.modules.purchase_orders.domain.totals) from `quantity`/`rate`/"
        "`discount_percent`/`tax_rate` - any such field in the request body is ignored - "
        "and the purchase order's own totals are recalculated from every item in the "
        "same transaction."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_ITEM_NOT_FOUND_RESPONSE,
        **_NOT_DRAFT_RESPONSE,
        **_CALCULATION_ERROR_RESPONSE,
        201: {"content": {"application/json": {"example": _PURCHASE_ORDER_ITEM_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(PURCHASE_ORDER_CREATE))],
)
async def add_purchase_order_item(
    purchase_order_id: uuid.UUID,
    payload: PurchaseOrderItemCreateRequest,
    current_user: User = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service),
) -> PurchaseOrderItemResponse:
    return await service.add_item(purchase_order_id, payload, tenant_id=current_user.tenant_id)


@router.get(
    "/{purchase_order_id}/items",
    response_model=list[PurchaseOrderItemBillingResponse],
    summary="List the line items on a purchase order",
    description=(
        "Every item on this purchase order - allowed regardless of order status (only "
        "add/edit/delete are draft-only). `q` searches description (case-insensitive "
        "substring). `sort` is one of `line_number`, `description`, `created_at` "
        "(default `line_number`); prefix with `-` for descending. No pagination - an "
        "order's line count is small and bounded. `billed_quantity`/`remaining_quantity` "
        "(Sprint 12 Session 12) are derived from linked purchase bill items in one "
        "additional aggregation query, regardless of item count - never per-item."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        200: {"content": {"application/json": {"example": _ITEM_LIST_RESPONSE_EXAMPLE}}},
        422: {"model": ErrorResponse, "description": "Invalid sort field"},
    },
    dependencies=[Depends(require_permission(PURCHASE_ORDER_VIEW))],
)
async def list_purchase_order_items(
    purchase_order_id: uuid.UUID,
    params: Annotated[PurchaseOrderItemListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service),
    purchase_service: PurchaseService = Depends(get_purchase_service),
) -> list[PurchaseOrderItemBillingResponse]:
    items = await service.list_items(
        purchase_order_id, tenant_id=current_user.tenant_id, q=params.q, sort=params.sort
    )
    billed_by_item = await purchase_service.get_billed_quantities_for_po_items(
        [item.id for item in items], tenant_id=current_user.tenant_id
    )
    summary = derive_billing_summary(
        [OrderedItem(id=item.id, quantity=item.quantity) for item in items],
        billed_by_item,
        total_amount=Decimal("0"),
    )
    return [
        PurchaseOrderItemBillingResponse(
            **item.model_dump(),
            billed_quantity=summary.items[item.id].billed_quantity,
            remaining_quantity=summary.items[item.id].remaining_quantity,
        )
        for item in items
    ]


@router.get(
    "/{purchase_order_id}/purchase-bills",
    response_model=list[PurchaseOrderLinkedBillResponse],
    summary="List the purchase bills linked to this purchase order",
    description=(
        "Every non-deleted Purchase Bill whose purchase_order_id references this "
        "order (Sprint 12 Session 13), most recent bill_date first. Empty if none "
        "are linked yet - a purchase order need not have any bills at all. One "
        "aggregated query, not one request per bill."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c20",
                            "bill_number": "PUR/2026-27/00001",
                            "bill_date": "2026-08-10",
                            "status": "posted",
                            "total_amount": "40000.00",
                            "balance_amount": "0.00",
                        }
                    ]
                }
            }
        },
    },
    dependencies=[Depends(require_permission(PURCHASE_ORDER_VIEW))],
)
async def list_purchase_order_purchase_bills(
    purchase_order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service),
    purchase_service: PurchaseService = Depends(get_purchase_service),
) -> list[PurchaseOrderLinkedBillResponse]:
    await service.get(purchase_order_id, tenant_id=current_user.tenant_id)
    bills = await purchase_service.list_bills_for_purchase_order(
        purchase_order_id, tenant_id=current_user.tenant_id
    )
    return [PurchaseOrderLinkedBillResponse.model_validate(bill) for bill in bills]


@router.put(
    "/{purchase_order_id}/items/{item_id}",
    response_model=PurchaseOrderItemResponse,
    summary="Update a line item on a draft purchase order",
    description=(
        "Partial update: only fields present in the request body are changed. Only "
        "items on `draft` purchase orders may be updated (409 otherwise). "
        "`discount_amount`/`taxable_amount`/`tax_amount`/`line_total` are recomputed "
        "server-side from the resulting quantity/rate/discount_percent/tax_rate, and "
        "the purchase order's own totals are recalculated from every item in the same "
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
                        **_PURCHASE_ORDER_ITEM_EXAMPLE,
                        "quantity": "40.000",
                        "taxable_amount": "18000.00",
                        "tax_amount": "900.00",
                        "line_total": "18900.00",
                    }
                }
            }
        },
    },
    dependencies=[Depends(require_permission(PURCHASE_ORDER_EDIT))],
)
async def update_purchase_order_item(
    purchase_order_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: PurchaseOrderItemUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service),
) -> PurchaseOrderItemResponse:
    return await service.update_item(
        purchase_order_id, item_id, payload, tenant_id=current_user.tenant_id
    )


@router.delete(
    "/{purchase_order_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a line item from a draft purchase order",
    description=(
        "Hard delete - PurchaseOrderItem carries no soft-delete columns. Only items on "
        "`draft` purchase orders may be deleted (409 otherwise). The deleted item's "
        "line_number is never reused. The purchase order's own totals are recalculated "
        "from the remaining items in the same transaction."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_ITEM_NOT_FOUND_RESPONSE, **_NOT_DRAFT_RESPONSE},
    dependencies=[Depends(require_permission(PURCHASE_ORDER_DELETE))],
)
async def delete_purchase_order_item(
    purchase_order_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service),
) -> None:
    await service.delete_item(purchase_order_id, item_id, tenant_id=current_user.tenant_id)


@router.post(
    "/{purchase_order_id}/confirm",
    response_model=PurchaseOrderResponse,
    summary="Confirm a draft purchase order",
    description=(
        "Irreversibly transitions `draft` to `confirmed`, inside one database "
        "transaction: the purchase order row is locked (`SELECT ... FOR UPDATE`), all "
        "totals are recalculated server-side from its current items, a sequential "
        "`po_number` is assigned (`PO/{fiscal_year}/{seq}`, concurrency-safe via a "
        "locked per-tenant counter row). Requires the `draft` status (409 if already "
        "confirmed/fulfilled/cancelled) and at least one item (422 if empty). "
        "Confirming a purchase order never touches supplier outstanding, ledger, or "
        "any financial report - it is a procurement commitment, not a bill. Once "
        "confirmed, no further edit, delete, or item CRUD is possible (409 "
        "PURCHASE_ORDER_NOT_DRAFT on any attempt)."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        **_EMPTY_ORDER_RESPONSE,
        **_NOT_CONFIRMABLE_RESPONSE,
        200: {"content": {"application/json": {"example": _CONFIRMED_PURCHASE_ORDER_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(PURCHASE_ORDER_CONFIRM))],
)
async def confirm_purchase_order(
    purchase_order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service),
) -> PurchaseOrderResponse:
    return await service.confirm(
        purchase_order_id, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.post(
    "/{purchase_order_id}/cancel",
    response_model=PurchaseOrderResponse,
    summary="Cancel a draft or confirmed purchase order",
    description=(
        "`draft`|`confirmed` -> `cancelled` (409 if already fulfilled or cancelled). "
        "No side effects on any other module - a cancelled purchase order never "
        "affected supplier outstanding/ledger, so there is nothing to reverse."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        **_NOT_CANCELLABLE_RESPONSE,
        200: {"content": {"application/json": {"example": _CANCELLED_PURCHASE_ORDER_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(PURCHASE_ORDER_CANCEL))],
)
async def cancel_purchase_order(
    purchase_order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service),
) -> PurchaseOrderResponse:
    return await service.cancel(
        purchase_order_id, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.post(
    "/{purchase_order_id}/fulfill",
    response_model=PurchaseOrderResponse,
    summary="Mark a confirmed purchase order as fulfilled",
    description=(
        "`confirmed` -> `fulfilled` (409 otherwise). This is simply the PO lifecycle "
        "foundation - it does not create Purchase Bills, does not create payment "
        "records, and does not modify supplier outstanding. Partial fulfillment and "
        "the Purchase Bill linkage are deferred to a future integration session."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        **_NOT_FULFILLABLE_RESPONSE,
        200: {"content": {"application/json": {"example": _FULFILLED_PURCHASE_ORDER_EXAMPLE}}},
    },
    dependencies=[Depends(require_permission(PURCHASE_ORDER_FULFILL))],
)
async def fulfill_purchase_order(
    purchase_order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service),
) -> PurchaseOrderResponse:
    return await service.fulfill(
        purchase_order_id, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.get(
    "/{purchase_order_id}/document",
    summary="Download the purchase order as a PDF document",
    description=(
        "Renders the purchase order as a PDF, stores it, and records it in the Document "
        "Center in one operation. Only available once the order has been confirmed (has "
        "a po_number) - a still-draft order, or one cancelled directly from draft, has "
        "nothing to print (422). A confirmed, fulfilled, or confirmed-then-cancelled "
        "order can always be downloaded. Generating this document never affects "
        "supplier outstanding, ledger, or any financial report - it carries no paid/"
        "balance/outstanding figures at all."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        **_DOCUMENT_NOT_AVAILABLE_RESPONSE,
        200: {
            "description": "The rendered PDF",
            "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
        },
    },
    dependencies=[Depends(require_permission(PURCHASE_ORDER_VIEW))],
)
async def get_purchase_order_document(
    purchase_order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service),
    document_record_service: DocumentRecordService = Depends(get_document_record_service),
) -> Response:
    context = await service.get_document_context(
        purchase_order_id, tenant_id=current_user.tenant_id
    )
    document_data = build_purchase_order_document_data(
        context.purchase_order,
        context.items,
        context.supplier,
        tenant_name=context.tenant_name,
        tenant_details=context.tenant_details,
        tenant_logo_bytes=context.tenant_logo_bytes,
        generated_by=current_user.full_name,
    )

    generated = await document_record_service.generate_store_and_record(
        document_data,
        tenant_id=current_user.tenant_id,
        party_type=PartyType.SUPPLIER,
        party_id=context.supplier.id,
        party_name=context.supplier.name,
        generated_by=current_user.id,
        source_type=SourceType.PURCHASE_ORDER,
        source_id=purchase_order_id,
    )
    return Response(
        content=generated.content,
        media_type=generated.content_type,
        headers={"Content-Disposition": f'attachment; filename="{generated.file_name}"'},
    )
