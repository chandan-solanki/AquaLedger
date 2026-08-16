import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.delivery_challans.constants import DeliveryChallanStatus
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

_MINIMAL = {"invoice_id": uuid.uuid4(), "challan_date": date(2026, 8, 16)}
_MINIMAL_ITEM = {"invoice_item_id": uuid.uuid4(), "quantity": Decimal("40.000")}


@dataclass
class _FakeDeliveryChallanRow:
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


@dataclass
class _FakeDeliveryChallanItemRow:
    id: uuid.UUID
    tenant_id: uuid.UUID
    delivery_challan_id: uuid.UUID
    invoice_item_id: uuid.UUID
    line_number: int
    quantity: Decimal
    unit: str
    created_at: datetime
    updated_at: datetime


def _make_challan_row(**overrides: object) -> _FakeDeliveryChallanRow:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "invoice_id": uuid.uuid4(),
        "challan_number": None,
        "challan_date": date(2026, 8, 16),
        "status": DeliveryChallanStatus.DRAFT,
        "remarks": None,
        "dispatched_at": None,
        "delivered_at": None,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return _FakeDeliveryChallanRow(**defaults)  # type: ignore[arg-type]


def _make_item_row(**overrides: object) -> _FakeDeliveryChallanItemRow:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "delivery_challan_id": uuid.uuid4(),
        "invoice_item_id": uuid.uuid4(),
        "line_number": 1,
        "quantity": Decimal("40.000"),
        "unit": "KG",
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return _FakeDeliveryChallanItemRow(**defaults)  # type: ignore[arg-type]


class TestDeliveryChallanResponse:
    def test_builds_from_orm_like_object(self) -> None:
        row = _make_challan_row(status=DeliveryChallanStatus.DRAFT)
        response = DeliveryChallanResponse.model_validate(row)
        assert response.status == DeliveryChallanStatus.DRAFT
        assert response.challan_number is None

    def test_dispatched_challan_carries_a_number_and_dispatched_at(self) -> None:
        now = datetime.now(UTC)
        row = _make_challan_row(
            status=DeliveryChallanStatus.DISPATCHED,
            challan_number="DC/2026-27/00001",
            dispatched_at=now,
        )
        response = DeliveryChallanResponse.model_validate(row)
        assert response.status == DeliveryChallanStatus.DISPATCHED
        assert response.challan_number == "DC/2026-27/00001"
        assert response.dispatched_at == now

    def test_has_no_financial_fields(self) -> None:
        """A delivery challan is never a financial document - no
        subtotal/tax/total_amount, no company_id (customer is always read
        via the linked invoice)."""
        forbidden = {
            "subtotal",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "paid_amount",
            "balance_amount",
            "company_id",
        }
        assert forbidden.isdisjoint(DeliveryChallanResponse.model_fields)


class TestDeliveryChallanItemResponse:
    def test_builds_from_orm_like_object(self) -> None:
        row = _make_item_row(line_number=2, unit="BOX")
        response = DeliveryChallanItemResponse.model_validate(row)
        assert response.line_number == 2
        assert response.unit == "BOX"

    def test_serializes_decimal_fields_as_strings(self) -> None:
        row = _make_item_row(quantity=Decimal("12.500"))
        response = DeliveryChallanItemResponse.model_validate(row)
        dumped = response.model_dump(mode="json")
        assert dumped["quantity"] == "12.500"

    def test_has_no_financial_fields(self) -> None:
        forbidden = {"rate", "discount_amount", "tax_amount", "line_total", "description"}
        assert forbidden.isdisjoint(DeliveryChallanItemResponse.model_fields)


class TestDeliveryChallanCreateRequestDefaults:
    def test_minimal_payload_is_accepted(self) -> None:
        request = DeliveryChallanCreateRequest(**_MINIMAL)
        assert request.remarks is None

    def test_requires_invoice_id(self) -> None:
        with pytest.raises(ValidationError):
            DeliveryChallanCreateRequest(challan_date=date(2026, 8, 16))  # type: ignore[call-arg]

    def test_requires_challan_date(self) -> None:
        with pytest.raises(ValidationError):
            DeliveryChallanCreateRequest(invoice_id=uuid.uuid4())  # type: ignore[call-arg]

    def test_does_not_accept_any_server_owned_field(self) -> None:
        server_owned = {"challan_number", "status", "dispatched_at", "delivered_at"}
        assert server_owned.isdisjoint(DeliveryChallanCreateRequest.model_fields)


class TestDeliveryChallanUpdateRequestPartialSemantics:
    def test_untouched_fields_are_excluded_from_dump(self) -> None:
        request = DeliveryChallanUpdateRequest(remarks="New remark")
        dumped = request.model_dump(exclude_unset=True)
        assert dumped == {"remarks": "New remark"}

    def test_all_fields_optional(self) -> None:
        request = DeliveryChallanUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_does_not_accept_invoice_id(self) -> None:
        """invoice_id is immutable after creation - set-once, mirroring
        PurchaseBillUpdateRequest's own purchase_order_id omission."""
        assert "invoice_id" not in DeliveryChallanUpdateRequest.model_fields


class TestDeliveryChallanListParams:
    def test_defaults(self) -> None:
        params = DeliveryChallanListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort == "-created_at"
        assert params.q is None

    @pytest.mark.parametrize(
        "value", ["challan_date", "-challan_date", "challan_number", "created_at"]
    )
    def test_accepts_every_sortable_field(self, value: str) -> None:
        params = DeliveryChallanListParams(sort=value)
        assert params.sort == value

    def test_rejects_unknown_sort_field(self) -> None:
        with pytest.raises(ValidationError):
            DeliveryChallanListParams(sort="unknown_field")

    def test_rejects_unsortable_field_even_with_dash(self) -> None:
        with pytest.raises(ValidationError):
            DeliveryChallanListParams(sort="-remarks")

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            DeliveryChallanListParams(page=0)

    def test_rejects_page_size_above_cap(self) -> None:
        with pytest.raises(ValidationError):
            DeliveryChallanListParams(page_size=101)

    def test_filters_bind(self) -> None:
        invoice_id = uuid.uuid4()
        params = DeliveryChallanListParams(
            status=DeliveryChallanStatus.DRAFT,
            invoice_id=invoice_id,
            challan_date_from=date(2026, 1, 1),
            challan_date_to=date(2026, 12, 31),
        )
        assert params.status == DeliveryChallanStatus.DRAFT
        assert params.invoice_id == invoice_id
        assert params.challan_date_from == date(2026, 1, 1)
        assert params.challan_date_to == date(2026, 12, 31)

    def test_has_no_supplier_id_field(self) -> None:
        """Unlike PurchaseOrderListParams, there is no stored customer
        column on DeliveryChallan to filter on directly - invoice_id is the
        only relational filter."""
        assert "supplier_id" not in DeliveryChallanListParams.model_fields
        assert "company_id" not in DeliveryChallanListParams.model_fields


class TestDeliveryChallanItemCreateRequestValidation:
    def test_minimal_payload_is_accepted(self) -> None:
        request = DeliveryChallanItemCreateRequest(**_MINIMAL_ITEM)
        assert request.quantity == Decimal("40.000")

    def test_requires_invoice_item_id(self) -> None:
        with pytest.raises(ValidationError):
            DeliveryChallanItemCreateRequest(quantity=Decimal("1"))  # type: ignore[call-arg]

    def test_requires_quantity_greater_than_zero(self) -> None:
        payload = {**_MINIMAL_ITEM, "quantity": Decimal("0")}
        with pytest.raises(ValidationError):
            DeliveryChallanItemCreateRequest(**payload)

    def test_negative_quantity_is_rejected(self) -> None:
        payload = {**_MINIMAL_ITEM, "quantity": Decimal("-1")}
        with pytest.raises(ValidationError):
            DeliveryChallanItemCreateRequest(**payload)

    def test_does_not_accept_unit_field(self) -> None:
        """unit is derived server-side from the linked invoice item, never
        client-supplied."""
        assert "unit" not in DeliveryChallanItemCreateRequest.model_fields

    def test_does_not_accept_any_financial_field(self) -> None:
        financial = {"rate", "discount_percent", "tax_rate", "description"}
        assert financial.isdisjoint(DeliveryChallanItemCreateRequest.model_fields)


class TestDeliveryChallanItemUpdateRequestPartialSemantics:
    def test_all_fields_optional(self) -> None:
        request = DeliveryChallanItemUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_untouched_fields_are_excluded_from_dump(self) -> None:
        request = DeliveryChallanItemUpdateRequest(quantity=Decimal("35.000"))
        dumped = request.model_dump(exclude_unset=True)
        assert dumped == {"quantity": Decimal("35.000")}

    def test_rejects_zero_quantity(self) -> None:
        with pytest.raises(ValidationError):
            DeliveryChallanItemUpdateRequest(quantity=Decimal("0"))

    def test_does_not_accept_invoice_item_id(self) -> None:
        """Re-linking to a different invoice item in place is not
        supported this session - delete and re-add instead."""
        assert "invoice_item_id" not in DeliveryChallanItemUpdateRequest.model_fields


class TestDeliveryChallanItemListParams:
    def test_defaults(self) -> None:
        params = DeliveryChallanItemListParams()
        assert params.sort == "line_number"

    @pytest.mark.parametrize("value", ["line_number", "-line_number", "created_at", "-created_at"])
    def test_accepts_every_sortable_field(self, value: str) -> None:
        params = DeliveryChallanItemListParams(sort=value)
        assert params.sort == value

    def test_rejects_unknown_sort_field(self) -> None:
        with pytest.raises(ValidationError):
            DeliveryChallanItemListParams(sort="unknown_field")

    def test_has_no_q_field(self) -> None:
        """A delivery challan item has no free-text field to search."""
        assert "q" not in DeliveryChallanItemListParams.model_fields
