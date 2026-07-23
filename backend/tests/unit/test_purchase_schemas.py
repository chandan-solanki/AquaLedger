import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.purchase.constants import PurchaseStatus
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

_MINIMAL_ITEM = {
    "description": "Pomfret - Grade A",
    "quantity": Decimal("50.000"),
    "unit": "KG",
    "rate": Decimal("450.0000"),
}

_MINIMAL = {"supplier_id": uuid.uuid4(), "bill_date": date(2026, 7, 23)}


@dataclass
class _FakePurchaseBillRow:
    id: uuid.UUID
    tenant_id: uuid.UUID
    supplier_id: uuid.UUID
    bill_number: str | None
    bill_date: date
    due_date: date | None
    status: PurchaseStatus
    subtotal: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    transport_charge: Decimal
    other_charge: Decimal
    round_off: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    balance_amount: Decimal
    remarks: str | None
    posted_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass
class _FakePurchaseBillItemRow:
    id: uuid.UUID
    tenant_id: uuid.UUID
    purchase_bill_id: uuid.UUID
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


def _make_bill_row(**overrides: object) -> _FakePurchaseBillRow:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "supplier_id": uuid.uuid4(),
        "bill_number": None,
        "bill_date": date(2026, 7, 23),
        "due_date": None,
        "status": PurchaseStatus.DRAFT,
        "subtotal": Decimal("0"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("0"),
        "tax_amount": Decimal("0"),
        "transport_charge": Decimal("0"),
        "other_charge": Decimal("0"),
        "round_off": Decimal("0"),
        "total_amount": Decimal("0"),
        "paid_amount": Decimal("0"),
        "balance_amount": Decimal("0"),
        "remarks": None,
        "posted_at": None,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return _FakePurchaseBillRow(**defaults)  # type: ignore[arg-type]


def _make_item_row(**overrides: object) -> _FakePurchaseBillItemRow:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "purchase_bill_id": uuid.uuid4(),
        "line_number": 1,
        "description": None,
        "quantity": Decimal("1.000"),
        "unit": "KG",
        "rate": Decimal("1.0000"),
        "discount_percent": Decimal("0"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("0"),
        "tax_rate": Decimal("0"),
        "tax_amount": Decimal("0"),
        "line_total": Decimal("0"),
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return _FakePurchaseBillItemRow(**defaults)  # type: ignore[arg-type]


class TestPurchaseBillResponse:
    def test_builds_from_orm_like_object(self) -> None:
        row = _make_bill_row(status=PurchaseStatus.DRAFT)
        response = PurchaseBillResponse.model_validate(row)
        assert response.status == PurchaseStatus.DRAFT
        assert response.bill_number is None
        assert response.total_amount == Decimal("0")

    def test_posted_bill_carries_a_number_and_posted_at(self) -> None:
        now = datetime.now(UTC)
        row = _make_bill_row(
            status=PurchaseStatus.POSTED, bill_number="PUR/2026-27/00001", posted_at=now
        )
        response = PurchaseBillResponse.model_validate(row)
        assert response.status == PurchaseStatus.POSTED
        assert response.bill_number == "PUR/2026-27/00001"
        assert response.posted_at == now


class TestPurchaseBillItemResponse:
    def test_builds_from_orm_like_object(self) -> None:
        row = _make_item_row(line_number=2, unit="BOX")
        response = PurchaseBillItemResponse.model_validate(row)
        assert response.line_number == 2
        assert response.unit == "BOX"

    def test_serializes_decimal_fields_as_strings(self) -> None:
        row = _make_item_row(quantity=Decimal("12.500"), rate=Decimal("450.0000"))
        response = PurchaseBillItemResponse.model_validate(row)
        dumped = response.model_dump(mode="json")
        assert dumped["quantity"] == "12.500"
        assert dumped["rate"] == "450.0000"


class TestPurchaseBillCreateRequestDefaults:
    def test_minimal_payload_is_accepted(self) -> None:
        request = PurchaseBillCreateRequest(**_MINIMAL)
        assert request.due_date is None
        assert request.remarks is None

    def test_requires_supplier_id(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseBillCreateRequest(bill_date=date(2026, 7, 23))  # type: ignore[call-arg]

    def test_requires_bill_date(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseBillCreateRequest(supplier_id=uuid.uuid4())  # type: ignore[call-arg]

    def test_does_not_accept_any_server_owned_field(self) -> None:
        # None of the financial columns, bill_number, status or posted_at
        # are part of this schema at all - the server always owns them
        # (TASKS.md Sprint 11 Session 2's explicit "Server owns" list).
        server_owned = {
            "bill_number",
            "subtotal",
            "discount_amount",
            "tax_amount",
            "transport_charge",
            "other_charge",
            "round_off",
            "total_amount",
            "paid_amount",
            "balance_amount",
            "status",
            "posted_at",
        }
        assert server_owned.isdisjoint(PurchaseBillCreateRequest.model_fields)


class TestPurchaseBillUpdateRequestPartialSemantics:
    def test_untouched_fields_are_excluded_from_dump(self) -> None:
        request = PurchaseBillUpdateRequest(remarks="New remark")
        dumped = request.model_dump(exclude_unset=True)
        assert dumped == {"remarks": "New remark"}

    def test_explicit_none_is_still_included(self) -> None:
        request = PurchaseBillUpdateRequest(due_date=None)
        dumped = request.model_dump(exclude_unset=True)
        assert "due_date" in dumped
        assert dumped["due_date"] is None

    def test_all_fields_optional(self) -> None:
        request = PurchaseBillUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_does_not_accept_any_server_owned_field(self) -> None:
        server_owned = {
            "bill_number",
            "subtotal",
            "discount_amount",
            "tax_amount",
            "transport_charge",
            "other_charge",
            "round_off",
            "total_amount",
            "paid_amount",
            "balance_amount",
            "status",
            "posted_at",
        }
        assert server_owned.isdisjoint(PurchaseBillUpdateRequest.model_fields)


class TestPurchaseBillListParams:
    def test_defaults(self) -> None:
        params = PurchaseBillListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort == "-created_at"
        assert params.q is None

    @pytest.mark.parametrize("value", ["bill_date", "-bill_date", "bill_number", "created_at"])
    def test_accepts_every_sortable_field(self, value: str) -> None:
        params = PurchaseBillListParams(sort=value)
        assert params.sort == value

    def test_rejects_unknown_sort_field(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseBillListParams(sort="unknown_field")

    def test_rejects_unsortable_field_even_with_dash(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseBillListParams(sort="-remarks")

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseBillListParams(page=0)

    def test_rejects_page_size_above_cap(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseBillListParams(page_size=101)

    def test_filters_bind(self) -> None:
        supplier_id = uuid.uuid4()
        params = PurchaseBillListParams(
            status=PurchaseStatus.DRAFT,
            supplier_id=supplier_id,
            bill_date_from=date(2026, 1, 1),
            bill_date_to=date(2026, 12, 31),
        )
        assert params.status == PurchaseStatus.DRAFT
        assert params.supplier_id == supplier_id
        assert params.bill_date_from == date(2026, 1, 1)
        assert params.bill_date_to == date(2026, 12, 31)


class TestPurchaseBillItemCreateRequestValidation:
    def test_minimal_payload_is_accepted(self) -> None:
        request = PurchaseBillItemCreateRequest(**_MINIMAL_ITEM)  # type: ignore[arg-type]
        assert request.discount_percent == Decimal("0")
        assert request.tax_rate == Decimal("0")

    def test_requires_description(self) -> None:
        payload = {**_MINIMAL_ITEM, "description": ""}
        with pytest.raises(ValidationError):
            PurchaseBillItemCreateRequest(**payload)  # type: ignore[arg-type]

    def test_requires_quantity_greater_than_zero(self) -> None:
        payload = {**_MINIMAL_ITEM, "quantity": Decimal("0")}
        with pytest.raises(ValidationError):
            PurchaseBillItemCreateRequest(**payload)  # type: ignore[arg-type]

    def test_negative_quantity_is_rejected(self) -> None:
        payload = {**_MINIMAL_ITEM, "quantity": Decimal("-1")}
        with pytest.raises(ValidationError):
            PurchaseBillItemCreateRequest(**payload)  # type: ignore[arg-type]

    def test_requires_unit(self) -> None:
        payload = {**_MINIMAL_ITEM, "unit": ""}
        with pytest.raises(ValidationError):
            PurchaseBillItemCreateRequest(**payload)  # type: ignore[arg-type]

    def test_rejects_negative_rate(self) -> None:
        payload = {**_MINIMAL_ITEM, "rate": Decimal("-1")}
        with pytest.raises(ValidationError):
            PurchaseBillItemCreateRequest(**payload)  # type: ignore[arg-type]

    def test_zero_rate_is_accepted(self) -> None:
        payload = {**_MINIMAL_ITEM, "rate": Decimal("0")}
        request = PurchaseBillItemCreateRequest(**payload)  # type: ignore[arg-type]
        assert request.rate == Decimal("0")

    @pytest.mark.parametrize("value", [Decimal("-1"), Decimal("100.01")])
    def test_discount_percent_out_of_range_is_rejected(self, value: Decimal) -> None:
        payload = {**_MINIMAL_ITEM, "discount_percent": value}
        with pytest.raises(ValidationError):
            PurchaseBillItemCreateRequest(**payload)  # type: ignore[arg-type]

    @pytest.mark.parametrize("value", [Decimal("0"), Decimal("100")])
    def test_discount_percent_boundaries_are_accepted(self, value: Decimal) -> None:
        payload = {**_MINIMAL_ITEM, "discount_percent": value}
        request = PurchaseBillItemCreateRequest(**payload)  # type: ignore[arg-type]
        assert request.discount_percent == value

    @pytest.mark.parametrize("value", [Decimal("-1"), Decimal("100.01")])
    def test_tax_rate_out_of_range_is_rejected(self, value: Decimal) -> None:
        payload = {**_MINIMAL_ITEM, "tax_rate": value}
        with pytest.raises(ValidationError):
            PurchaseBillItemCreateRequest(**payload)  # type: ignore[arg-type]

    def test_does_not_accept_any_server_owned_field(self) -> None:
        # line_number and every financial column
        # (discount_amount/taxable_amount/tax_amount/line_total) are not
        # part of this schema at all - the server always owns them.
        server_owned = {
            "line_number",
            "discount_amount",
            "taxable_amount",
            "tax_amount",
            "line_total",
        }
        assert server_owned.isdisjoint(PurchaseBillItemCreateRequest.model_fields)

    def test_does_not_accept_fish_or_trip_catch_fields(self) -> None:
        # Unlike InvoiceItemCreateRequest - a purchase line has no link to a
        # sold-fish master or a trip catch.
        assert "fish_id" not in PurchaseBillItemCreateRequest.model_fields
        assert "trip_catch_id" not in PurchaseBillItemCreateRequest.model_fields


class TestPurchaseBillItemUpdateRequestPartialSemantics:
    def test_all_fields_optional(self) -> None:
        request = PurchaseBillItemUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_untouched_fields_are_excluded_from_dump(self) -> None:
        request = PurchaseBillItemUpdateRequest(quantity=Decimal("40.000"))
        dumped = request.model_dump(exclude_unset=True)
        assert dumped == {"quantity": Decimal("40.000")}

    def test_empty_description_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseBillItemUpdateRequest(description="")

    def test_rejects_negative_rate(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseBillItemUpdateRequest(rate=Decimal("-1"))

    def test_does_not_accept_any_server_owned_field(self) -> None:
        server_owned = {
            "line_number",
            "discount_amount",
            "taxable_amount",
            "tax_amount",
            "line_total",
        }
        assert server_owned.isdisjoint(PurchaseBillItemUpdateRequest.model_fields)


class TestPurchaseBillItemListParams:
    def test_defaults(self) -> None:
        params = PurchaseBillItemListParams()
        assert params.sort == "line_number"
        assert params.q is None

    @pytest.mark.parametrize("value", ["line_number", "-line_number", "description", "-created_at"])
    def test_accepts_every_sortable_field(self, value: str) -> None:
        params = PurchaseBillItemListParams(sort=value)
        assert params.sort == value

    def test_rejects_unknown_sort_field(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseBillItemListParams(sort="unknown_field")

    def test_rejects_unsortable_field_even_with_dash(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseBillItemListParams(sort="-rate")
