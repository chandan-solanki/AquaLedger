import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

# Registers DeliveryChallanDocumentRenderer for DocumentType.DELIVERY_CHALLAN into the
# shared DocumentRegistry singleton, mirroring app.modules.purchase_orders.router's own
# registration import.
import app.modules.delivery_challans.document_renderer as _delivery_challan_document_renderer  # noqa: F401
from app.common.schemas import ErrorResponse, PaginatedResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.delivery_challans.dependencies import get_delivery_challan_service
from app.modules.delivery_challans.document_builder import build_delivery_challan_document_data
from app.modules.delivery_challans.permissions import (
    DELIVERY_CHALLAN_CANCEL,
    DELIVERY_CHALLAN_CREATE,
    DELIVERY_CHALLAN_DELETE,
    DELIVERY_CHALLAN_DELIVER,
    DELIVERY_CHALLAN_DISPATCH,
    DELIVERY_CHALLAN_EDIT,
    DELIVERY_CHALLAN_VIEW,
)
from app.modules.delivery_challans.schemas import (
    DeliveryChallanCreateRequest,
    DeliveryChallanItemCreateRequest,
    DeliveryChallanItemListParams,
    DeliveryChallanItemResponse,
    DeliveryChallanItemUpdateRequest,
    DeliveryChallanListParams,
    DeliveryChallanResponse,
    DeliveryChallanUpdateRequest,
)
from app.modules.delivery_challans.service import DeliveryChallanService
from app.modules.documents.constants import PartyType, SourceType
from app.modules.documents.dependencies import get_document_record_service
from app.modules.documents.service import DocumentRecordService

router = APIRouter(prefix="/delivery-challans", tags=["delivery-challans"])


def _error_example(code: str, message: str) -> dict[str, object]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": None,
            "field_errors": None,
            "request_id": "e9fefc78-4d47-4788-8d33-427f5b7852c8",
            "timestamp": "2026-08-16T04:00:00Z",
        }
    }


_COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Missing required permission"},
}
_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Delivery challan not found",
        "content": {
            "application/json": {
                "example": _error_example(
                    "DELIVERY_CHALLAN_NOT_FOUND", "Delivery challan not found"
                )
            }
        },
    },
}
_INVOICE_LINK_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "The specified invoice does not exist (or belongs to another tenant)",
        "content": {
            "application/json": {
                "example": _error_example(
                    "DELIVERY_CHALLAN_INVOICE_NOT_FOUND", "The specified invoice does not exist"
                )
            }
        },
    },
    422: {
        "model": ErrorResponse,
        "description": "The invoice exists but is not ISSUED/PARTIALLY_PAID/PAID",
        "content": {
            "application/json": {
                "example": _error_example(
                    "DELIVERY_CHALLAN_INVOICE_NOT_DELIVERABLE",
                    "Only issued, partially paid, or paid invoices can be linked to a "
                    "delivery challan",
                )
            }
        },
    },
}
_NOT_DRAFT_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "The delivery challan is no longer DRAFT and cannot be edited or deleted",
        "content": {
            "application/json": {
                "example": _error_example(
                    "DELIVERY_CHALLAN_NOT_DRAFT",
                    "Only draft delivery challans can be edited, deleted, or mutated",
                )
            }
        },
    },
}
_ITEM_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Delivery challan not found, or item not found, or invoice item mismatch",
        "content": {
            "application/json": {
                "examples": {
                    "delivery_challan_not_found": {
                        "summary": "delivery_challan_id does not exist for this tenant",
                        "value": _error_example(
                            "DELIVERY_CHALLAN_NOT_FOUND", "Delivery challan not found"
                        ),
                    },
                    "item_not_found": {
                        "summary": (
                            "item_id does not exist on this delivery challan for this tenant"
                        ),
                        "value": _error_example(
                            "DELIVERY_CHALLAN_ITEM_NOT_FOUND", "Delivery challan item not found"
                        ),
                    },
                    "invoice_item_not_found": {
                        "summary": "invoice_item_id does not belong to the linked invoice",
                        "value": _error_example(
                            "DELIVERY_CHALLAN_INVOICE_ITEM_NOT_FOUND",
                            "The specified invoice item does not belong to this delivery "
                            "challan's linked invoice",
                        ),
                    },
                }
            }
        },
    },
}
_OVER_DELIVERY_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": (
            "The requested quantity exceeds what remains deliverable on the invoice item"
        ),
        "content": {
            "application/json": {
                "example": _error_example(
                    "DELIVERY_CHALLAN_OVER_DELIVERY",
                    "Delivery quantity 31.000 exceeds the remaining 30.000 KG on this invoice item",
                )
            }
        },
    },
}
_NOT_DISPATCHABLE_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "The delivery challan is not DRAFT",
        "content": {
            "application/json": {
                "example": _error_example(
                    "DELIVERY_CHALLAN_INVALID_TRANSITION",
                    "Only draft delivery challans can be dispatched",
                )
            }
        },
    },
}
_NOT_DELIVERABLE_TRANSITION_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "The delivery challan is not DISPATCHED",
        "content": {
            "application/json": {
                "example": _error_example(
                    "DELIVERY_CHALLAN_INVALID_TRANSITION",
                    "Only dispatched delivery challans can be delivered",
                )
            }
        },
    },
}
_NOT_CANCELLABLE_RESPONSE: dict[int | str, dict[str, object]] = {
    409: {
        "model": ErrorResponse,
        "description": "The delivery challan is already delivered or cancelled",
        "content": {
            "application/json": {
                "example": _error_example(
                    "DELIVERY_CHALLAN_INVALID_TRANSITION",
                    "Only draft or dispatched delivery challans can be cancelled",
                )
            }
        },
    },
}
_EMPTY_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": "The delivery challan has no items",
        "content": {
            "application/json": {
                "example": _error_example(
                    "DELIVERY_CHALLAN_EMPTY",
                    "A delivery challan must have at least one item to be dispatched",
                )
            }
        },
    },
}
_DOCUMENT_NOT_AVAILABLE_RESPONSE: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": "The delivery challan has not been dispatched (no challan_number yet)",
        "content": {
            "application/json": {
                "example": _error_example(
                    "DELIVERY_CHALLAN_DOCUMENT_NOT_AVAILABLE",
                    "The delivery challan must be dispatched before its document can be generated",
                )
            }
        },
    },
}


@router.post(
    "",
    response_model=DeliveryChallanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft delivery challan",
    description=(
        "Always created in `draft` status with `challan_number`/`dispatched_at`/"
        "`delivered_at` all NULL - none is accepted in the request body, the server "
        "always owns them. Add line items afterwards via `POST /{delivery_challan_id}/"
        "items`. `invoice_id` is required and set-once: must reference an existing "
        "invoice for the caller's tenant that is `issued`, `partially_paid`, or `paid` "
        "(404/422 otherwise). Creating a delivery challan never affects customer "
        "outstanding, invoice balance, ledger, or any financial report - it is a "
        "logistics record, not a financial event."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_INVOICE_LINK_ERROR_RESPONSES,
        201: {"description": "The created draft delivery challan"},
    },
    dependencies=[Depends(require_permission(DELIVERY_CHALLAN_CREATE))],
)
async def create_delivery_challan(
    payload: DeliveryChallanCreateRequest,
    current_user: User = Depends(get_current_user),
    service: DeliveryChallanService = Depends(get_delivery_challan_service),
) -> DeliveryChallanResponse:
    return await service.create(payload, tenant_id=current_user.tenant_id, actor_id=current_user.id)


@router.get(
    "",
    response_model=PaginatedResponse[DeliveryChallanResponse],
    summary="Search, filter, sort and paginate delivery challans",
    description=(
        "Every non-deleted delivery challan for the caller's tenant. `q` searches "
        "challan_number (case-insensitive substring). Combine with status/invoice_id/"
        "challan_date_from/challan_date_to filters, `sort` (one of `challan_date`, "
        "`challan_number`, `created_at`; prefix with `-` for descending) and "
        "page/page_size."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        422: {
            "model": ErrorResponse,
            "description": "Invalid sort field, or page/page_size out of range",
        },
    },
    dependencies=[Depends(require_permission(DELIVERY_CHALLAN_VIEW))],
)
async def list_delivery_challans(
    params: Annotated[DeliveryChallanListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: DeliveryChallanService = Depends(get_delivery_challan_service),
) -> PaginatedResponse[DeliveryChallanResponse]:
    return await service.list_delivery_challans(tenant_id=current_user.tenant_id, params=params)


@router.get(
    "/{delivery_challan_id}",
    response_model=DeliveryChallanResponse,
    summary="Get a delivery challan by id",
    description=(
        "`status`/`challan_number`/`dispatched_at`/`delivered_at` reflect the "
        "lifecycle: `draft` (editable, no number) -> `dispatched` (number assigned, "
        "immutable, physical dispatch recorded) -> `delivered` (terminal), with "
        "`cancelled` reachable from either `draft` or `dispatched`."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission(DELIVERY_CHALLAN_VIEW))],
)
async def get_delivery_challan(
    delivery_challan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DeliveryChallanService = Depends(get_delivery_challan_service),
) -> DeliveryChallanResponse:
    return await service.get(delivery_challan_id, tenant_id=current_user.tenant_id)


@router.put(
    "/{delivery_challan_id}",
    response_model=DeliveryChallanResponse,
    summary="Update a draft delivery challan",
    description=(
        "Partial update: only fields present in the request body are changed. Only "
        "`draft` delivery challans may be updated (409 otherwise). `invoice_id` is "
        "immutable after creation - not accepted here."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE, **_NOT_DRAFT_RESPONSE},
    dependencies=[Depends(require_permission(DELIVERY_CHALLAN_EDIT))],
)
async def update_delivery_challan(
    delivery_challan_id: uuid.UUID,
    payload: DeliveryChallanUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: DeliveryChallanService = Depends(get_delivery_challan_service),
) -> DeliveryChallanResponse:
    return await service.update(
        delivery_challan_id, payload, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.delete(
    "/{delivery_challan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a draft delivery challan",
    description=(
        "Sets deleted_at/deleted_by rather than removing the row (ARCHITECTURE.md §38). "
        "Only `draft` delivery challans may be deleted (409 otherwise)."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_FOUND_RESPONSE, **_NOT_DRAFT_RESPONSE},
    dependencies=[Depends(require_permission(DELIVERY_CHALLAN_DELETE))],
)
async def delete_delivery_challan(
    delivery_challan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DeliveryChallanService = Depends(get_delivery_challan_service),
) -> None:
    await service.delete(
        delivery_challan_id, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.post(
    "/{delivery_challan_id}/items",
    response_model=DeliveryChallanItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a line item to a draft delivery challan",
    description=(
        "Only `draft` delivery challans may receive new items (409 otherwise). "
        "`line_number` is assigned server-side. `unit` is derived server-side from "
        "the referenced invoice item - never client-supplied. `invoice_item_id` must "
        "belong to this challan's own linked invoice (404 otherwise), and the "
        "combined quantity already delivered against that invoice item (across every "
        "non-cancelled delivery challan, including other drafts) plus this item's own "
        "quantity must not exceed the invoice item's own invoiced quantity (422 "
        "`DELIVERY_CHALLAN_OVER_DELIVERY` otherwise)."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_DRAFT_RESPONSE,
        **_ITEM_NOT_FOUND_RESPONSE,
        **_OVER_DELIVERY_RESPONSE,
        201: {"description": "The created delivery challan item"},
    },
    dependencies=[Depends(require_permission(DELIVERY_CHALLAN_CREATE))],
)
async def add_delivery_challan_item(
    delivery_challan_id: uuid.UUID,
    payload: DeliveryChallanItemCreateRequest,
    current_user: User = Depends(get_current_user),
    service: DeliveryChallanService = Depends(get_delivery_challan_service),
) -> DeliveryChallanItemResponse:
    return await service.add_item(delivery_challan_id, payload, tenant_id=current_user.tenant_id)


@router.get(
    "/{delivery_challan_id}/items",
    response_model=list[DeliveryChallanItemResponse],
    summary="List the line items on a delivery challan",
    description=(
        "Every item on this delivery challan - allowed regardless of challan status "
        "(only add/edit/delete are draft-only). `sort` is one of `line_number`, "
        "`created_at` (default `line_number`); prefix with `-` for descending. No "
        "pagination - a challan's line count is small and bounded."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        422: {"model": ErrorResponse, "description": "Invalid sort field"},
    },
    dependencies=[Depends(require_permission(DELIVERY_CHALLAN_VIEW))],
)
async def list_delivery_challan_items(
    delivery_challan_id: uuid.UUID,
    params: Annotated[DeliveryChallanItemListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: DeliveryChallanService = Depends(get_delivery_challan_service),
) -> list[DeliveryChallanItemResponse]:
    return await service.list_items(
        delivery_challan_id, tenant_id=current_user.tenant_id, sort=params.sort
    )


@router.put(
    "/{delivery_challan_id}/items/{item_id}",
    response_model=DeliveryChallanItemResponse,
    summary="Update a line item on a draft delivery challan",
    description=(
        "Partial update: only `quantity` may change (`invoice_item_id` is immutable "
        "after creation). Only items on `draft` delivery challans may be updated (409 "
        "otherwise). The over-delivery check is re-run against the item's own prior "
        "contribution excluded, so raising the quantity up to (but not beyond) the "
        "invoice item's remaining balance always succeeds."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_DRAFT_RESPONSE,
        **_ITEM_NOT_FOUND_RESPONSE,
        **_OVER_DELIVERY_RESPONSE,
    },
    dependencies=[Depends(require_permission(DELIVERY_CHALLAN_EDIT))],
)
async def update_delivery_challan_item(
    delivery_challan_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: DeliveryChallanItemUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: DeliveryChallanService = Depends(get_delivery_challan_service),
) -> DeliveryChallanItemResponse:
    return await service.update_item(
        delivery_challan_id, item_id, payload, tenant_id=current_user.tenant_id
    )


@router.delete(
    "/{delivery_challan_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a line item from a draft delivery challan",
    description=(
        "Hard delete - DeliveryChallanItem carries no soft-delete columns. Only items "
        "on `draft` delivery challans may be deleted (409 otherwise). Deleting an item "
        "immediately frees its reserved quantity for other delivery challans against "
        "the same invoice item."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_NOT_DRAFT_RESPONSE, **_ITEM_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission(DELIVERY_CHALLAN_DELETE))],
)
async def delete_delivery_challan_item(
    delivery_challan_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DeliveryChallanService = Depends(get_delivery_challan_service),
) -> None:
    await service.delete_item(delivery_challan_id, item_id, tenant_id=current_user.tenant_id)


@router.post(
    "/{delivery_challan_id}/dispatch",
    response_model=DeliveryChallanResponse,
    summary="Dispatch a draft delivery challan",
    description=(
        "Irreversibly transitions `draft` to `dispatched`, inside one database "
        "transaction: the delivery challan row is locked (`SELECT ... FOR UPDATE`), a "
        "sequential `challan_number` is assigned (`DC/{fiscal_year}/{seq}`, "
        "concurrency-safe via a locked per-tenant counter row), and `dispatched_at` is "
        "stamped. Requires the `draft` status (409 otherwise) and at least one item "
        "(422 if empty). Dispatching a delivery challan never touches customer "
        "outstanding, invoice balance, ledger, or any financial report. Once "
        "dispatched, no further edit, delete, or item CRUD is possible (409 "
        "`DELIVERY_CHALLAN_NOT_DRAFT` on any attempt)."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        **_EMPTY_RESPONSE,
        **_NOT_DISPATCHABLE_RESPONSE,
    },
    dependencies=[Depends(require_permission(DELIVERY_CHALLAN_DISPATCH))],
)
async def dispatch_delivery_challan(
    delivery_challan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DeliveryChallanService = Depends(get_delivery_challan_service),
) -> DeliveryChallanResponse:
    return await service.dispatch(
        delivery_challan_id, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.post(
    "/{delivery_challan_id}/deliver",
    response_model=DeliveryChallanResponse,
    summary="Mark a dispatched delivery challan as delivered",
    description=(
        "`dispatched` -> `delivered` (terminal, 409 otherwise). Stamps `delivered_at`. "
        "This never touches customer outstanding, invoice balance, ledger, or any "
        "financial report - a delivery challan is a logistics record, not a payable "
        "or a receivable."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        **_NOT_DELIVERABLE_TRANSITION_RESPONSE,
    },
    dependencies=[Depends(require_permission(DELIVERY_CHALLAN_DELIVER))],
)
async def deliver_delivery_challan(
    delivery_challan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DeliveryChallanService = Depends(get_delivery_challan_service),
) -> DeliveryChallanResponse:
    return await service.deliver(
        delivery_challan_id, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.post(
    "/{delivery_challan_id}/cancel",
    response_model=DeliveryChallanResponse,
    summary="Cancel a draft or dispatched delivery challan",
    description=(
        "`draft`|`dispatched` -> `cancelled` (409 if already delivered or cancelled). "
        "No side effects on any other module - a cancelled delivery challan never "
        "affected customer outstanding/invoice balance/ledger, so there is nothing to "
        "reverse. Its items stop counting toward any invoice item's delivered "
        "quantity, immediately freeing that quantity for other delivery challans."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        **_NOT_CANCELLABLE_RESPONSE,
    },
    dependencies=[Depends(require_permission(DELIVERY_CHALLAN_CANCEL))],
)
async def cancel_delivery_challan(
    delivery_challan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DeliveryChallanService = Depends(get_delivery_challan_service),
) -> DeliveryChallanResponse:
    return await service.cancel(
        delivery_challan_id, tenant_id=current_user.tenant_id, actor_id=current_user.id
    )


@router.get(
    "/{delivery_challan_id}/document",
    summary="Download the delivery challan as a PDF document",
    description=(
        "Renders the delivery challan as a PDF, stores it, and records it in the Document "
        "Center in one operation. Only available once the challan has been dispatched (has "
        "a challan_number) - a still-draft challan, or one cancelled directly from draft, has "
        "nothing to print (422). A dispatched, delivered, or dispatched-then-cancelled "
        "challan can always be downloaded. Generating this document never affects customer "
        "outstanding, invoice balance, or any financial report - it carries no paid/balance/"
        "outstanding figures at all, since a delivery challan is a physical delivery record, "
        "never a financial document."
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
    dependencies=[Depends(require_permission(DELIVERY_CHALLAN_VIEW))],
)
async def get_delivery_challan_document(
    delivery_challan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DeliveryChallanService = Depends(get_delivery_challan_service),
    document_record_service: DocumentRecordService = Depends(get_document_record_service),
) -> Response:
    context = await service.get_document_context(
        delivery_challan_id, tenant_id=current_user.tenant_id
    )
    document_data = build_delivery_challan_document_data(
        context.delivery_challan,
        context.items,
        context.invoice,
        context.invoice_items_by_id,
        context.fish_by_id,
        context.previously_delivered_by_item_id,
        context.company,
        tenant_name=context.tenant_name,
        tenant_details=context.tenant_details,
        tenant_logo_bytes=context.tenant_logo_bytes,
        generated_by=current_user.full_name,
    )

    generated = await document_record_service.generate_store_and_record(
        document_data,
        tenant_id=current_user.tenant_id,
        party_type=PartyType.CUSTOMER,
        party_id=context.company.id,
        party_name=context.company.name,
        generated_by=current_user.id,
        source_type=SourceType.DELIVERY_CHALLAN,
        source_id=delivery_challan_id,
    )
    return Response(
        content=generated.content,
        media_type=generated.content_type,
        headers={"Content-Disposition": f'attachment; filename="{generated.file_name}"'},
    )
