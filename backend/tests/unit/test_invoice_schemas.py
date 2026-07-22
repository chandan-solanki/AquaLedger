import uuid
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.schemas import (
    InvoiceCreateRequest,
    InvoiceItemCreateRequest,
    InvoiceItemUpdateRequest,
    InvoiceListParams,
    InvoiceUpdateRequest,
)

_MINIMAL: dict[str, object] = {
    "company_id": uuid.uuid4(),
    "invoice_date": date(2026, 7, 22),
}

_MINIMAL_ITEM: dict[str, object] = {
    "trip_catch_id": uuid.uuid4(),
    "fish_id": uuid.uuid4(),
    "quantity": "50.000",
    "unit": "kg",
    "rate": "450.0000",
}


class TestInvoiceCreateRequest:
    def test_minimal_payload_gets_sane_defaults(self) -> None:
        request = InvoiceCreateRequest(**_MINIMAL)
        assert request.due_date is None
        assert request.remarks is None
        assert request.transport_charge == Decimal("0")
        assert request.other_charge == Decimal("0")

    def test_rejects_missing_company_id(self) -> None:
        payload = {k: v for k, v in _MINIMAL.items() if k != "company_id"}
        with pytest.raises(ValidationError):
            InvoiceCreateRequest(**payload)

    def test_rejects_missing_invoice_date(self) -> None:
        payload = {k: v for k, v in _MINIMAL.items() if k != "invoice_date"}
        with pytest.raises(ValidationError):
            InvoiceCreateRequest(**payload)

    def test_rejects_invalid_company_id(self) -> None:
        with pytest.raises(ValidationError):
            InvoiceCreateRequest(**{**_MINIMAL, "company_id": "not-a-uuid"})

    def test_accepts_optional_fields(self) -> None:
        request = InvoiceCreateRequest(
            **_MINIMAL,
            due_date=date(2026, 8, 6),
            transport_charge="250.00",
            other_charge="15.00",
            remarks="Weekly settlement",
        )
        assert request.due_date == date(2026, 8, 6)
        assert request.transport_charge == Decimal("250.00")
        assert request.other_charge == Decimal("15.00")
        assert request.remarks == "Weekly settlement"

    @pytest.mark.parametrize("field", ["transport_charge", "other_charge"])
    def test_rejects_negative_charges(self, field: str) -> None:
        with pytest.raises(ValidationError):
            InvoiceCreateRequest(**{**_MINIMAL, field: "-0.01"})

    @pytest.mark.parametrize("field", ["transport_charge", "other_charge"])
    def test_accepts_zero_charge(self, field: str) -> None:
        request = InvoiceCreateRequest(**{**_MINIMAL, field: "0"})
        assert getattr(request, field) == Decimal("0")

    def test_does_not_accept_calculated_financial_fields(self) -> None:
        """Calculated financial fields must never be client-supplied - the
        server owns them (Session 4's financial engine). transport_charge/
        other_charge are the exception (direct inputs, not calculated) and
        are covered separately above. Extra/unknown keys are simply ignored
        by pydantic's default config, not rejected, but they must not end
        up on the model."""
        request = InvoiceCreateRequest(
            **_MINIMAL,
            subtotal="500.00",
            discount_amount="10.00",
            taxable_amount="490.00",
            tax_amount="24.50",
            round_off="0.50",
            total_amount="99999.00",
            paid_amount="50.00",
            balance_amount="49949.00",
            status="issued",
            invoice_number="INV-0001",
        )
        assert not hasattr(request, "subtotal")
        assert not hasattr(request, "discount_amount")
        assert not hasattr(request, "taxable_amount")
        assert not hasattr(request, "tax_amount")
        assert not hasattr(request, "round_off")
        assert not hasattr(request, "total_amount")
        assert not hasattr(request, "paid_amount")
        assert not hasattr(request, "balance_amount")
        assert not hasattr(request, "status")
        assert not hasattr(request, "invoice_number")


class TestInvoiceUpdateRequest:
    def test_untouched_fields_are_excluded_from_dump(self) -> None:
        request = InvoiceUpdateRequest(remarks="Revised")
        dumped = request.model_dump(exclude_unset=True)
        assert dumped == {"remarks": "Revised"}

    def test_all_fields_optional(self) -> None:
        request = InvoiceUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_explicit_none_is_still_included(self) -> None:
        request = InvoiceUpdateRequest(due_date=None)
        dumped = request.model_dump(exclude_unset=True)
        assert "due_date" in dumped
        assert dumped["due_date"] is None

    def test_company_id_and_invoice_date_can_be_reassigned(self) -> None:
        new_company_id = uuid.uuid4()
        new_date = date(2026, 8, 1)
        request = InvoiceUpdateRequest(company_id=new_company_id, invoice_date=new_date)
        assert request.model_dump(exclude_unset=True) == {
            "company_id": new_company_id,
            "invoice_date": new_date,
        }

    def test_rejects_invalid_company_id(self) -> None:
        with pytest.raises(ValidationError):
            InvoiceUpdateRequest(company_id="not-a-uuid")

    def test_transport_and_other_charge_can_be_updated(self) -> None:
        request = InvoiceUpdateRequest(transport_charge="300.00", other_charge="5.00")
        assert request.model_dump(exclude_unset=True) == {
            "transport_charge": Decimal("300.00"),
            "other_charge": Decimal("5.00"),
        }

    @pytest.mark.parametrize("field", ["transport_charge", "other_charge"])
    def test_rejects_negative_charges(self, field: str) -> None:
        with pytest.raises(ValidationError):
            InvoiceUpdateRequest(**{field: "-0.01"})

    def test_does_not_accept_calculated_financial_fields(self) -> None:
        request = InvoiceUpdateRequest(total_amount="99999.00", status="issued")
        assert not hasattr(request, "total_amount")
        assert not hasattr(request, "status")


_SORTABLE_FIELDS = ("invoice_date", "invoice_number", "created_at")


class TestInvoiceListParams:
    def test_defaults(self) -> None:
        params = InvoiceListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort == "-created_at"
        assert params.q is None
        assert params.status is None
        assert params.company_id is None
        assert params.invoice_date_from is None
        assert params.invoice_date_to is None

    @pytest.mark.parametrize(
        "value",
        [f"{prefix}{field}" for field in _SORTABLE_FIELDS for prefix in ("", "-")],
    )
    def test_accepts_every_sortable_field_ascending_and_descending(self, value: str) -> None:
        params = InvoiceListParams(sort=value)
        assert params.sort == value

    def test_rejects_unknown_sort_field(self) -> None:
        with pytest.raises(ValidationError):
            InvoiceListParams(sort="unknown_field")

    def test_rejects_unsortable_field_even_with_dash(self) -> None:
        with pytest.raises(ValidationError):
            InvoiceListParams(sort="-company_id")

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            InvoiceListParams(page=0)

    def test_rejects_page_size_above_cap(self) -> None:
        with pytest.raises(ValidationError):
            InvoiceListParams(page_size=101)

    def test_rejects_page_size_below_one(self) -> None:
        with pytest.raises(ValidationError):
            InvoiceListParams(page_size=0)

    def test_accepts_status_and_company_filters(self) -> None:
        company_id = uuid.uuid4()
        params = InvoiceListParams(status="draft", company_id=company_id)
        assert params.status == InvoiceStatus.DRAFT
        assert params.company_id == company_id

    def test_rejects_invalid_status_filter(self) -> None:
        with pytest.raises(ValidationError):
            InvoiceListParams(status="not-a-real-status")

    def test_accepts_invoice_date_range_filters(self) -> None:
        params = InvoiceListParams(
            invoice_date_from="2026-07-01",
            invoice_date_to="2026-07-31",
        )
        assert params.invoice_date_from is not None
        assert params.invoice_date_to is not None
        assert params.invoice_date_from.isoformat() == "2026-07-01"
        assert params.invoice_date_to.isoformat() == "2026-07-31"


class TestInvoiceItemCreateRequest:
    def test_minimal_payload_gets_sane_defaults(self) -> None:
        request = InvoiceItemCreateRequest(**_MINIMAL_ITEM)
        assert request.description is None
        assert request.discount_percent == Decimal("0")
        assert request.tax_rate == Decimal("0")

    @pytest.mark.parametrize("field", ["trip_catch_id", "fish_id", "quantity", "unit", "rate"])
    def test_rejects_missing_required_field(self, field: str) -> None:
        payload = {k: v for k, v in _MINIMAL_ITEM.items() if k != field}
        with pytest.raises(ValidationError):
            InvoiceItemCreateRequest(**payload)

    def test_rejects_zero_quantity(self) -> None:
        with pytest.raises(ValidationError):
            InvoiceItemCreateRequest(**{**_MINIMAL_ITEM, "quantity": "0"})

    def test_rejects_negative_quantity(self) -> None:
        with pytest.raises(ValidationError):
            InvoiceItemCreateRequest(**{**_MINIMAL_ITEM, "quantity": "-1"})

    def test_accepts_small_positive_quantity(self) -> None:
        request = InvoiceItemCreateRequest(**{**_MINIMAL_ITEM, "quantity": "0.001"})
        assert request.quantity == Decimal("0.001")

    def test_accepts_zero_rate(self) -> None:
        request = InvoiceItemCreateRequest(**{**_MINIMAL_ITEM, "rate": "0"})
        assert request.rate == Decimal("0")

    def test_rejects_negative_rate(self) -> None:
        with pytest.raises(ValidationError):
            InvoiceItemCreateRequest(**{**_MINIMAL_ITEM, "rate": "-1"})

    @pytest.mark.parametrize("field", ["discount_percent", "tax_rate"])
    def test_rejects_negative_percent_fields(self, field: str) -> None:
        with pytest.raises(ValidationError):
            InvoiceItemCreateRequest(**{**_MINIMAL_ITEM, field: "-0.01"})

    @pytest.mark.parametrize("field", ["discount_percent", "tax_rate"])
    def test_rejects_percent_fields_above_100(self, field: str) -> None:
        with pytest.raises(ValidationError):
            InvoiceItemCreateRequest(**{**_MINIMAL_ITEM, field: "100.01"})

    @pytest.mark.parametrize("field", ["discount_percent", "tax_rate"])
    def test_accepts_percent_fields_at_boundaries(self, field: str) -> None:
        low = InvoiceItemCreateRequest(**{**_MINIMAL_ITEM, field: "0"})
        high = InvoiceItemCreateRequest(**{**_MINIMAL_ITEM, field: "100"})
        assert getattr(low, field) == Decimal("0")
        assert getattr(high, field) == Decimal("100")

    def test_rejects_blank_unit(self) -> None:
        with pytest.raises(ValidationError):
            InvoiceItemCreateRequest(**{**_MINIMAL_ITEM, "unit": ""})

    def test_rejects_invalid_trip_catch_id(self) -> None:
        with pytest.raises(ValidationError):
            InvoiceItemCreateRequest(**{**_MINIMAL_ITEM, "trip_catch_id": "not-a-uuid"})

    def test_accepts_optional_description(self) -> None:
        request = InvoiceItemCreateRequest(**_MINIMAL_ITEM, description="Pomfret - Grade A")
        assert request.description == "Pomfret - Grade A"

    def test_does_not_accept_financial_fields(self) -> None:
        """Financial fields must never be client-supplied - the server owns
        all calculated values (Session 4)."""
        request = InvoiceItemCreateRequest(
            **_MINIMAL_ITEM,
            line_total="99999.00",
            tax_amount="500.00",
            discount_amount="10.00",
            subtotal="1000.00",
        )
        assert not hasattr(request, "line_total")
        assert not hasattr(request, "tax_amount")
        assert not hasattr(request, "discount_amount")
        assert not hasattr(request, "subtotal")


class TestInvoiceItemUpdateRequest:
    def test_untouched_fields_are_excluded_from_dump(self) -> None:
        request = InvoiceItemUpdateRequest(quantity=Decimal("40.000"))
        dumped = request.model_dump(exclude_unset=True)
        assert dumped == {"quantity": Decimal("40.000")}

    def test_all_fields_optional(self) -> None:
        request = InvoiceItemUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_explicit_none_is_still_included(self) -> None:
        request = InvoiceItemUpdateRequest(description=None)
        dumped = request.model_dump(exclude_unset=True)
        assert "description" in dumped
        assert dumped["description"] is None

    def test_rejects_zero_quantity(self) -> None:
        with pytest.raises(ValidationError):
            InvoiceItemUpdateRequest(quantity="0")

    def test_rejects_negative_quantity(self) -> None:
        with pytest.raises(ValidationError):
            InvoiceItemUpdateRequest(quantity="-1")

    def test_trip_catch_id_and_fish_id_can_be_reassigned(self) -> None:
        new_trip_catch_id = uuid.uuid4()
        new_fish_id = uuid.uuid4()
        request = InvoiceItemUpdateRequest(trip_catch_id=new_trip_catch_id, fish_id=new_fish_id)
        assert request.model_dump(exclude_unset=True) == {
            "trip_catch_id": new_trip_catch_id,
            "fish_id": new_fish_id,
        }

    @pytest.mark.parametrize("field", ["discount_percent", "tax_rate"])
    def test_rejects_percent_fields_above_100(self, field: str) -> None:
        with pytest.raises(ValidationError):
            InvoiceItemUpdateRequest(**{field: "100.01"})

    def test_does_not_accept_financial_fields(self) -> None:
        request = InvoiceItemUpdateRequest(line_total="99999.00")
        assert not hasattr(request, "line_total")
