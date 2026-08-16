import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.purchase_orders.constants import PurchaseOrderBillingStatus, PurchaseOrderStatus

_SORTABLE_FIELDS = frozenset({"order_date", "po_number", "created_at"})
_ITEM_SORTABLE_FIELDS = frozenset({"line_number", "description", "created_at"})


class PurchaseOrderItemResponse(BaseModel):
    """discount_amount/taxable_amount/tax_amount/line_total are computed
    server-side by app.modules.purchase_orders.domain.totals and
    recalculated on every item mutation - never client-supplied."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
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
                "created_at": "2026-07-23T04:00:00Z",
                "updated_at": "2026-07-23T04:00:00Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    purchase_order_id: uuid.UUID
    line_number: int
    description: str | None
    quantity: Decimal
    unit: str
    rate: Decimal
    discount_percent: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    line_total: Decimal
    created_at: datetime
    updated_at: datetime


class PurchaseOrderItemCreateRequest(BaseModel):
    """tenant_id, purchase_order_id and line_number are never
    client-supplied - line_number is assigned server-side
    (PurchaseOrderRepository.allocate_next_line_number). Financial fields
    (discount_amount/taxable_amount/tax_amount/line_total) are not accepted
    here at all: the server always owns them, computed by
    app.modules.purchase_orders.domain.totals from quantity/rate/
    discount_percent/tax_rate. There is no fish_id - a purchase order line
    has no link to a fish master, mirroring PurchaseBillItemCreateRequest."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Pomfret - Grade A",
                "quantity": "50.000",
                "unit": "KG",
                "rate": "450.0000",
                "discount_percent": "0.00",
                "tax_rate": "5.00",
            }
        }
    )

    description: str = Field(min_length=1, examples=["Pomfret - Grade A"])
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit: str = Field(min_length=1, max_length=20, examples=["KG"])
    rate: Decimal = Field(ge=0, max_digits=12, decimal_places=4)
    discount_percent: Decimal = Field(
        default=Decimal("0"), ge=0, le=100, max_digits=5, decimal_places=2
    )
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=5, decimal_places=2)


class PurchaseOrderItemUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are changed.
    Only items on DRAFT purchase orders may be updated (see
    PurchaseOrderService.update_item). Financial fields/line_number are not
    accepted here either, for the same reason as
    PurchaseOrderItemCreateRequest."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "quantity": "40.000",
                "rate": "460.0000",
            }
        }
    )

    description: str | None = Field(default=None, min_length=1)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    rate: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=4)
    discount_percent: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=5, decimal_places=2
    )
    tax_rate: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)


class PurchaseOrderItemListParams(BaseModel):
    """Query params for GET /purchase-orders/{purchase_order_id}/items. No
    pagination - a purchase order's line count is small and bounded."""

    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across description.",
        examples=["Pomfret"],
    )
    sort: str = Field(
        default="line_number",
        description="One of line_number, description, created_at; prefix with '-' for descending.",
        examples=["line_number", "-created_at"],
    )

    @field_validator("sort")
    @classmethod
    def _check_sort(cls, value: str) -> str:
        field = value[1:] if value.startswith("-") else value
        if field not in _ITEM_SORTABLE_FIELDS:
            raise ValueError(
                f"Invalid sort field '{field}'. Allowed: {', '.join(sorted(_ITEM_SORTABLE_FIELDS))}"
            )
        return value


class PurchaseOrderResponse(BaseModel):
    """subtotal/discount_amount/taxable_amount/tax_amount/total_amount are
    computed server-side by app.modules.purchase_orders.domain.totals and
    recalculated on every item mutation. There is no paid_amount/
    balance_amount - a purchase order is never paid; those columns belong
    to PurchaseBill."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c15",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "supplier_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
                "po_number": None,
                "order_date": "2026-07-23",
                "expected_delivery_date": "2026-08-05",
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
                "created_at": "2026-07-23T04:00:00Z",
                "updated_at": "2026-07-23T04:00:00Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    supplier_id: uuid.UUID
    po_number: str | None
    order_date: date
    expected_delivery_date: date | None
    status: PurchaseOrderStatus
    subtotal: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    transport_charge: Decimal
    other_charge: Decimal
    round_off: Decimal
    total_amount: Decimal
    remarks: str | None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PurchaseOrderCreateRequest(BaseModel):
    """tenant_id, created_by and updated_by are never client-supplied - the
    router populates them from the authenticated user. Every financial
    field, `po_number`, `status` and `confirmed_at` are not accepted here
    at all: the server always owns them (PurchaseOrderService.create) -
    every financial field starts at 0 (no items exist yet), `status` is
    always DRAFT, `po_number`/`confirmed_at` always NULL until confirm()
    assigns them."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "supplier_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
                "order_date": "2026-07-23",
                "expected_delivery_date": "2026-08-05",
                "remarks": "Weekly restock",
            }
        }
    )

    supplier_id: uuid.UUID = Field(
        description="Ordering supplier - must exist for this tenant and be active."
    )
    order_date: date
    expected_delivery_date: date | None = None
    remarks: str | None = None


class PurchaseOrderUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are changed.
    Only DRAFT purchase orders may be updated (see
    PurchaseOrderService.update). Financial fields/`po_number`/`status`/
    `confirmed_at` are not accepted here either, for the same reason as
    PurchaseOrderCreateRequest."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "expected_delivery_date": "2026-08-12",
                "remarks": "Delivery pushed a week",
            }
        }
    )

    supplier_id: uuid.UUID | None = Field(
        default=None,
        description="Reassign the ordering supplier - must exist for this tenant and be active.",
    )
    order_date: date | None = None
    expected_delivery_date: date | None = None
    remarks: str | None = None


class PurchaseOrderListParams(BaseModel):
    """Query params for GET /purchase-orders - bound via FastAPI's
    Depends() model support."""

    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across po_number and the ordering supplier's name.",
        examples=["PO-2026"],
    )
    status: PurchaseOrderStatus | None = Field(default=None, examples=[PurchaseOrderStatus.DRAFT])
    supplier_id: uuid.UUID | None = Field(default=None, description="Filter by ordering supplier.")
    billable: bool | None = Field(
        default=None,
        description=(
            "If true, restrict to CONFIRMED or FULFILLED orders only - the set "
            "eligible for Purchase Bill linkage. Combinable with supplier_id/q; "
            "lets pickers like the Purchase Bill form's PO selector filter "
            "server-side instead of fetching a page and filtering in the browser."
        ),
    )
    order_date_from: date | None = Field(
        default=None, description="Inclusive lower bound on order_date."
    )
    order_date_to: date | None = Field(
        default=None, description="Inclusive upper bound on order_date."
    )
    sort: str = Field(
        default="-created_at",
        description="One of order_date, po_number, created_at; prefix with '-' for descending.",
        examples=["order_date", "-po_number"],
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("sort")
    @classmethod
    def _check_sort(cls, value: str) -> str:
        field = value[1:] if value.startswith("-") else value
        if field not in _SORTABLE_FIELDS:
            raise ValueError(
                f"Invalid sort field '{field}'. Allowed: {', '.join(sorted(_SORTABLE_FIELDS))}"
            )
        return value


class PurchaseOrderDetailResponse(PurchaseOrderResponse):
    """PurchaseOrderResponse plus the derived billing summary (Sprint 12
    Session 12) - used ONLY by GET /purchase-orders/{id}, never by list/
    create/update/confirm/cancel/fulfill, so those endpoints never pay for
    the extra aggregation query this requires. billed_amount/
    remaining_amount are informational only (see
    app.modules.purchase_orders.domain.billing.PurchaseOrderBillingSummary's
    own docstring for why they can differ from a naive "total minus
    billed"); billing_status is the authoritative, quantity-derived
    rollup."""

    model_config = ConfigDict(from_attributes=True)

    billed_amount: Decimal
    remaining_amount: Decimal
    billing_status: PurchaseOrderBillingStatus


class PurchaseOrderLinkedBillResponse(BaseModel):
    """One Purchase Bill linked to this purchase order (Sprint 12 Session
    13) - used by GET /purchase-orders/{id}/purchase-bills. `status` is the
    bill's own PurchaseStatus value as a plain string (not the enum type
    itself) - purchase_orders never imports app.modules.purchase's enum, to
    keep the one-directional module dependency clean (see
    app.modules.purchase_orders.domain.billing.PurchaseOrderLinkedBill)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c20",
                "bill_number": "PUR/2026-27/00001",
                "bill_date": "2026-08-10",
                "status": "posted",
                "total_amount": "40000.00",
                "balance_amount": "0.00",
            }
        },
    )

    id: uuid.UUID
    bill_number: str | None
    bill_date: date
    status: str
    total_amount: Decimal
    balance_amount: Decimal


class PurchaseOrderItemBillingResponse(PurchaseOrderItemResponse):
    """PurchaseOrderItemResponse plus its own derived billed_quantity/
    remaining_quantity (Sprint 12 Session 12) - used ONLY by GET
    /purchase-orders/{id}/items. add_item/update_item continue returning
    plain PurchaseOrderItemResponse: both are only ever reachable while the
    parent order is DRAFT, a state in which no bill can possibly have
    billed against any of its items yet (billing requires CONFIRMED/
    FULFILLED), so computing billing there would always be a wasted, if
    harmless, extra query."""

    model_config = ConfigDict(from_attributes=True)

    billed_quantity: Decimal
    remaining_quantity: Decimal
