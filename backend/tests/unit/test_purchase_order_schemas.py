import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.purchase_orders.constants import PurchaseOrderStatus
from app.modules.purchase_orders.schemas import (
    PurchaseOrderCreateRequest,
    PurchaseOrderItemCreateRequest,
    PurchaseOrderItemListParams,
    PurchaseOrderItemResponse,
    PurchaseOrderItemUpdateRequest,
    PurchaseOrderListParams,
    PurchaseOrderResponse,
    PurchaseOrderUpdateRequest,
)

_MINIMAL_ITEM = {
    "description": "Pomfret - Grade A",
    "quantity": Decimal("50.000"),
    "unit": "KG",
    "rate": Decimal("450.0000"),
}

_MINIMAL = {"supplier_id": uuid.uuid4(), "order_date": date(2026, 8, 15)}


@dataclass
class _FakePurchaseOrderRow:
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


@dataclass
class _FakePurchaseOrderItemRow:
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


def _make_order_row(**overrides: object) -> _FakePurchaseOrderRow:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "supplier_id": uuid.uuid4(),
        "po_number": None,
        "order_date": date(2026, 8, 15),
        "expected_delivery_date": None,
        "status": PurchaseOrderStatus.DRAFT,
        "subtotal": Decimal("0"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("0"),
        "tax_amount": Decimal("0"),
        "transport_charge": Decimal("0"),
        "other_charge": Decimal("0"),
        "round_off": Decimal("0"),
        "total_amount": Decimal("0"),
        "remarks": None,
        "confirmed_at": None,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return _FakePurchaseOrderRow(**defaults)  # type: ignore[arg-type]


def _make_item_row(**overrides: object) -> _FakePurchaseOrderItemRow:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "purchase_order_id": uuid.uuid4(),
        "line_number": 1,
        "description": None,
        "quantity": Decimal("1.000"),
        "unit": "KG",
        "rate": Decimal("1.0000"),
        "discount_percent": Decimal("0"),
        "discount_amount": Decimal("0"),
        "tax_rate": Decimal("0"),
        "taxable_amount": Decimal("0"),
        "tax_amount": Decimal("0"),
        "line_total": Decimal("0"),
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return _FakePurchaseOrderItemRow(**defaults)  # type: ignore[arg-type]


class TestPurchaseOrderResponse:
    def test_builds_from_orm_like_object(self) -> None:
        row = _make_order_row(status=PurchaseOrderStatus.DRAFT)
        response = PurchaseOrderResponse.model_validate(row)
        assert response.status == PurchaseOrderStatus.DRAFT
        assert response.po_number is None
        assert response.total_amount == Decimal("0")

    def test_confirmed_order_carries_a_number_and_confirmed_at(self) -> None:
        now = datetime.now(UTC)
        row = _make_order_row(
            status=PurchaseOrderStatus.CONFIRMED, po_number="PO/2026-27/00001", confirmed_at=now
        )
        response = PurchaseOrderResponse.model_validate(row)
        assert response.status == PurchaseOrderStatus.CONFIRMED
        assert response.po_number == "PO/2026-27/00001"
        assert response.confirmed_at == now

    def test_has_no_paid_or_balance_amount_field(self) -> None:
        """A purchase order is never paid - those columns belong to
        PurchaseBill, not here."""
        assert "paid_amount" not in PurchaseOrderResponse.model_fields
        assert "balance_amount" not in PurchaseOrderResponse.model_fields


class TestPurchaseOrderItemResponse:
    def test_builds_from_orm_like_object(self) -> None:
        row = _make_item_row(line_number=2, unit="BOX")
        response = PurchaseOrderItemResponse.model_validate(row)
        assert response.line_number == 2
        assert response.unit == "BOX"

    def test_serializes_decimal_fields_as_strings(self) -> None:
        row = _make_item_row(quantity=Decimal("12.500"), rate=Decimal("450.0000"))
        response = PurchaseOrderItemResponse.model_validate(row)
        dumped = response.model_dump(mode="json")
        assert dumped["quantity"] == "12.500"
        assert dumped["rate"] == "450.0000"


class TestPurchaseOrderCreateRequestDefaults:
    def test_minimal_payload_is_accepted(self) -> None:
        request = PurchaseOrderCreateRequest(**_MINIMAL)
        assert request.expected_delivery_date is None
        assert request.remarks is None

    def test_requires_supplier_id(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseOrderCreateRequest(order_date=date(2026, 8, 15))  # type: ignore[call-arg]

    def test_requires_order_date(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseOrderCreateRequest(supplier_id=uuid.uuid4())  # type: ignore[call-arg]

    def test_does_not_accept_any_server_owned_field(self) -> None:
        # None of the financial columns, po_number, status or confirmed_at
        # are part of this schema at all - the server always owns them.
        server_owned = {
            "po_number",
            "subtotal",
            "discount_amount",
            "tax_amount",
            "transport_charge",
            "other_charge",
            "round_off",
            "total_amount",
            "status",
            "confirmed_at",
        }
        assert server_owned.isdisjoint(PurchaseOrderCreateRequest.model_fields)


class TestPurchaseOrderUpdateRequestPartialSemantics:
    def test_untouched_fields_are_excluded_from_dump(self) -> None:
        request = PurchaseOrderUpdateRequest(remarks="New remark")
        dumped = request.model_dump(exclude_unset=True)
        assert dumped == {"remarks": "New remark"}

    def test_explicit_none_is_still_included(self) -> None:
        request = PurchaseOrderUpdateRequest(expected_delivery_date=None)
        dumped = request.model_dump(exclude_unset=True)
        assert "expected_delivery_date" in dumped
        assert dumped["expected_delivery_date"] is None

    def test_all_fields_optional(self) -> None:
        request = PurchaseOrderUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_does_not_accept_any_server_owned_field(self) -> None:
        server_owned = {
            "po_number",
            "subtotal",
            "discount_amount",
            "tax_amount",
            "transport_charge",
            "other_charge",
            "round_off",
            "total_amount",
            "status",
            "confirmed_at",
        }
        assert server_owned.isdisjoint(PurchaseOrderUpdateRequest.model_fields)


class TestPurchaseOrderListParams:
    def test_defaults(self) -> None:
        params = PurchaseOrderListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort == "-created_at"
        assert params.q is None

    @pytest.mark.parametrize("value", ["order_date", "-order_date", "po_number", "created_at"])
    def test_accepts_every_sortable_field(self, value: str) -> None:
        params = PurchaseOrderListParams(sort=value)
        assert params.sort == value

    def test_rejects_unknown_sort_field(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseOrderListParams(sort="unknown_field")

    def test_rejects_unsortable_field_even_with_dash(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseOrderListParams(sort="-remarks")

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseOrderListParams(page=0)

    def test_rejects_page_size_above_cap(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseOrderListParams(page_size=101)

    def test_filters_bind(self) -> None:
        supplier_id = uuid.uuid4()
        params = PurchaseOrderListParams(
            status=PurchaseOrderStatus.DRAFT,
            supplier_id=supplier_id,
            order_date_from=date(2026, 1, 1),
            order_date_to=date(2026, 12, 31),
        )
        assert params.status == PurchaseOrderStatus.DRAFT
        assert params.supplier_id == supplier_id
        assert params.order_date_from == date(2026, 1, 1)
        assert params.order_date_to == date(2026, 12, 31)


class TestPurchaseOrderItemCreateRequestValidation:
    def test_minimal_payload_is_accepted(self) -> None:
        request = PurchaseOrderItemCreateRequest(**_MINIMAL_ITEM)
        assert request.discount_percent == Decimal("0")
        assert request.tax_rate == Decimal("0")

    def test_requires_description(self) -> None:
        payload = {**_MINIMAL_ITEM, "description": ""}
        with pytest.raises(ValidationError):
            PurchaseOrderItemCreateRequest(**payload)

    def test_requires_quantity_greater_than_zero(self) -> None:
        payload = {**_MINIMAL_ITEM, "quantity": Decimal("0")}
        with pytest.raises(ValidationError):
            PurchaseOrderItemCreateRequest(**payload)

    def test_negative_quantity_is_rejected(self) -> None:
        payload = {**_MINIMAL_ITEM, "quantity": Decimal("-1")}
        with pytest.raises(ValidationError):
            PurchaseOrderItemCreateRequest(**payload)

    def test_requires_unit(self) -> None:
        payload = {**_MINIMAL_ITEM, "unit": ""}
        with pytest.raises(ValidationError):
            PurchaseOrderItemCreateRequest(**payload)

    def test_rejects_negative_rate(self) -> None:
        payload = {**_MINIMAL_ITEM, "rate": Decimal("-1")}
        with pytest.raises(ValidationError):
            PurchaseOrderItemCreateRequest(**payload)

    def test_zero_rate_is_accepted(self) -> None:
        payload = {**_MINIMAL_ITEM, "rate": Decimal("0")}
        request = PurchaseOrderItemCreateRequest(**payload)
        assert request.rate == Decimal("0")

    @pytest.mark.parametrize("value", [Decimal("-1"), Decimal("100.01")])
    def test_discount_percent_out_of_range_is_rejected(self, value: Decimal) -> None:
        payload = {**_MINIMAL_ITEM, "discount_percent": value}
        with pytest.raises(ValidationError):
            PurchaseOrderItemCreateRequest(**payload)

    @pytest.mark.parametrize("value", [Decimal("0"), Decimal("100")])
    def test_discount_percent_boundaries_are_accepted(self, value: Decimal) -> None:
        payload = {**_MINIMAL_ITEM, "discount_percent": value}
        request = PurchaseOrderItemCreateRequest(**payload)
        assert request.discount_percent == value

    @pytest.mark.parametrize("value", [Decimal("-1"), Decimal("100.01")])
    def test_tax_rate_out_of_range_is_rejected(self, value: Decimal) -> None:
        payload = {**_MINIMAL_ITEM, "tax_rate": value}
        with pytest.raises(ValidationError):
            PurchaseOrderItemCreateRequest(**payload)

    def test_does_not_accept_any_server_owned_field(self) -> None:
        server_owned = {
            "line_number",
            "discount_amount",
            "taxable_amount",
            "tax_amount",
            "line_total",
        }
        assert server_owned.isdisjoint(PurchaseOrderItemCreateRequest.model_fields)

    def test_does_not_accept_fish_field(self) -> None:
        # A purchase order line has no link to a sold-fish master, mirroring
        # PurchaseBillItemCreateRequest.
        assert "fish_id" not in PurchaseOrderItemCreateRequest.model_fields


class TestPurchaseOrderItemUpdateRequestPartialSemantics:
    def test_all_fields_optional(self) -> None:
        request = PurchaseOrderItemUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_untouched_fields_are_excluded_from_dump(self) -> None:
        request = PurchaseOrderItemUpdateRequest(quantity=Decimal("40.000"))
        dumped = request.model_dump(exclude_unset=True)
        assert dumped == {"quantity": Decimal("40.000")}

    def test_empty_description_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseOrderItemUpdateRequest(description="")

    def test_rejects_negative_rate(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseOrderItemUpdateRequest(rate=Decimal("-1"))

    def test_does_not_accept_any_server_owned_field(self) -> None:
        server_owned = {
            "line_number",
            "discount_amount",
            "taxable_amount",
            "tax_amount",
            "line_total",
        }
        assert server_owned.isdisjoint(PurchaseOrderItemUpdateRequest.model_fields)


class TestPurchaseOrderItemListParams:
    def test_defaults(self) -> None:
        params = PurchaseOrderItemListParams()
        assert params.sort == "line_number"
        assert params.q is None

    @pytest.mark.parametrize("value", ["line_number", "-line_number", "description", "-created_at"])
    def test_accepts_every_sortable_field(self, value: str) -> None:
        params = PurchaseOrderItemListParams(sort=value)
        assert params.sort == value

    def test_rejects_unknown_sort_field(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseOrderItemListParams(sort="unknown_field")

    def test_rejects_unsortable_field_even_with_dash(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseOrderItemListParams(sort="-rate")
