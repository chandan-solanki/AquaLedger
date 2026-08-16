import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.delivery_challans.constants import DeliveryChallanStatus

_SORTABLE_FIELDS = frozenset({"challan_date", "challan_number", "created_at"})
_ITEM_SORTABLE_FIELDS = frozenset({"line_number", "created_at"})


class DeliveryChallanItemResponse(BaseModel):
    """No financial fields at all - a delivery challan item is a pure
    quantity record (quantity/unit against a specific invoice_item_id),
    never a priced line. `unit` is a server-derived snapshot of the linked
    invoice item's own unit at creation time (see
    DeliveryChallanItemCreateRequest's own docstring for why it is never
    client-supplied)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c30",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "delivery_challan_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c29",
                "invoice_item_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c02",
                "line_number": 1,
                "quantity": "40.000",
                "unit": "kg",
                "created_at": "2026-08-16T04:00:00Z",
                "updated_at": "2026-08-16T04:00:00Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    delivery_challan_id: uuid.UUID
    invoice_item_id: uuid.UUID
    line_number: int
    quantity: Decimal
    unit: str
    created_at: datetime
    updated_at: datetime


class DeliveryChallanItemCreateRequest(BaseModel):
    """tenant_id, delivery_challan_id, line_number and unit are never
    client-supplied. `line_number` is assigned server-side (next available
    for the challan, DeliveryChallanRepository.allocate_next_line_number).
    `unit` is derived server-side from the linked invoice item's own unit -
    unlike PurchaseBillItemCreateRequest (which accepts an independently
    client-supplied unit/rate because a bill's price can legitimately differ
    from its originating PO item's), a delivery challan item delivers the
    exact same invoiced good, so there is no legitimate reason for its unit
    to ever differ from the invoice item it references, and deriving it
    removes an entire class of client/server mismatch instead of merely
    validating against it."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "invoice_item_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c02",
                "quantity": "40.000",
            }
        }
    )

    invoice_item_id: uuid.UUID = Field(
        description=(
            "The invoice item this line delivers against - must belong to this "
            "challan's own linked invoice."
        )
    )
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)


class DeliveryChallanItemUpdateRequest(BaseModel):
    """Partial update - only `quantity` may change. `invoice_item_id` is
    immutable after creation (no field for it here) - re-linking would also
    require re-deriving the denormalized `unit` snapshot, and a challan item
    is cheap to delete and re-add while the parent challan is still DRAFT,
    so this session deliberately does not support in-place re-linking.
    Only items on DRAFT delivery challans may be updated (see
    DeliveryChallanService.update_item)."""

    model_config = ConfigDict(json_schema_extra={"example": {"quantity": "35.000"}})

    quantity: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3)


class DeliveryChallanItemListParams(BaseModel):
    """Query params for GET /delivery-challans/{delivery_challan_id}/items.
    No pagination - a delivery challan's line count is small and bounded,
    the same posture PurchaseOrderItemListParams takes. No `q` - unlike
    purchase order/bill items, a delivery challan item has no free-text
    field (no description) to search."""

    sort: str = Field(
        default="line_number",
        description="One of line_number, created_at; prefix with '-' for descending.",
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


class DeliveryChallanResponse(BaseModel):
    """No financial fields at all (no subtotal/tax/total_amount) - a
    delivery challan is a logistics document, never a financial one. There
    is deliberately no `company_id` here either - the customer is always
    read via the linked invoice (`invoice_id`), never duplicated."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c29",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "invoice_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c03",
                "challan_number": None,
                "challan_date": "2026-08-16",
                "status": "draft",
                "remarks": None,
                "dispatched_at": None,
                "delivered_at": None,
                "created_at": "2026-08-16T04:00:00Z",
                "updated_at": "2026-08-16T04:00:00Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    invoice_id: uuid.UUID
    challan_number: str | None
    challan_date: date
    status: DeliveryChallanStatus
    remarks: str | None
    dispatched_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DeliveryChallanCreateRequest(BaseModel):
    """tenant_id, created_by and updated_by are never client-supplied - the
    router populates them from the authenticated user. `challan_number`,
    `status`, `dispatched_at`/`delivered_at` are not accepted here at all:
    the server always owns them - `status` is always DRAFT, the timestamps
    and number stay NULL until dispatch()/deliver() assign them.
    `invoice_id` is required and set-once: there is no equivalent field on
    DeliveryChallanUpdateRequest, so once a challan is created it can never
    be re-linked to a different invoice."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "invoice_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c03",
                "challan_date": "2026-08-16",
                "remarks": "First partial delivery",
            }
        }
    )

    invoice_id: uuid.UUID = Field(
        description=(
            "Originating invoice - must belong to the caller's tenant and be "
            "ISSUED, PARTIALLY_PAID, or PAID (not draft or cancelled)."
        )
    )
    challan_date: date
    remarks: str | None = None


class DeliveryChallanUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are changed.
    Only DRAFT delivery challans may be updated (see
    DeliveryChallanService.update). `invoice_id`/`challan_number`/`status`/
    `dispatched_at`/`delivered_at` are not accepted here either, for the same
    reason as DeliveryChallanCreateRequest."""

    model_config = ConfigDict(json_schema_extra={"example": {"remarks": "Revised delivery note"}})

    challan_date: date | None = None
    remarks: str | None = None


class DeliveryChallanListParams(BaseModel):
    """Query params for GET /delivery-challans - bound via FastAPI's
    Depends() model support."""

    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across challan_number.",
        examples=["DC-2026"],
    )
    status: DeliveryChallanStatus | None = Field(
        default=None, examples=[DeliveryChallanStatus.DRAFT]
    )
    invoice_id: uuid.UUID | None = Field(default=None, description="Filter by originating invoice.")
    challan_date_from: date | None = Field(
        default=None, description="Inclusive lower bound on challan_date."
    )
    challan_date_to: date | None = Field(
        default=None, description="Inclusive upper bound on challan_date."
    )
    sort: str = Field(
        default="-created_at",
        description=(
            "One of challan_date, challan_number, created_at; prefix with '-' for descending."
        ),
        examples=["challan_date", "-challan_number"],
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
