import uuid
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.trip_expenses.constants import ExpenseType
from app.modules.trip_expenses.schemas import (
    TripExpenseCreateRequest,
    TripExpenseListParams,
    TripExpenseUpdateRequest,
)

_MINIMAL: dict[str, object] = {
    "trip_id": uuid.uuid4(),
    "expense_type": "diesel",
    "amount": "4500.00",
    "expense_date": date(2026, 7, 22),
}


class TestTripExpenseCreateRequest:
    def test_minimal_payload_gets_sane_defaults(self) -> None:
        request = TripExpenseCreateRequest(**_MINIMAL)
        assert request.description is None
        assert request.vendor_name is None
        assert request.receipt_number is None
        assert request.amount == Decimal("4500.00")

    def test_rejects_missing_trip_id(self) -> None:
        payload = {k: v for k, v in _MINIMAL.items() if k != "trip_id"}
        with pytest.raises(ValidationError):
            TripExpenseCreateRequest(**payload)

    def test_rejects_missing_expense_type(self) -> None:
        payload = {k: v for k, v in _MINIMAL.items() if k != "expense_type"}
        with pytest.raises(ValidationError):
            TripExpenseCreateRequest(**payload)

    def test_rejects_missing_amount(self) -> None:
        payload = {k: v for k, v in _MINIMAL.items() if k != "amount"}
        with pytest.raises(ValidationError):
            TripExpenseCreateRequest(**payload)

    def test_rejects_missing_expense_date(self) -> None:
        payload = {k: v for k, v in _MINIMAL.items() if k != "expense_date"}
        with pytest.raises(ValidationError):
            TripExpenseCreateRequest(**payload)

    def test_rejects_zero_amount(self) -> None:
        with pytest.raises(ValidationError):
            TripExpenseCreateRequest(**{**_MINIMAL, "amount": "0"})

    def test_rejects_negative_amount(self) -> None:
        with pytest.raises(ValidationError):
            TripExpenseCreateRequest(**{**_MINIMAL, "amount": "-1"})

    def test_accepts_small_positive_amount(self) -> None:
        request = TripExpenseCreateRequest(**{**_MINIMAL, "amount": "0.01"})
        assert request.amount == Decimal("0.01")

    @pytest.mark.parametrize(
        "expense_type",
        ["diesel", "ice", "food", "labour", "harbour", "maintenance", "repair", "permit", "other"],
    )
    def test_accepts_every_expense_type(self, expense_type: str) -> None:
        request = TripExpenseCreateRequest(**{**_MINIMAL, "expense_type": expense_type})
        assert request.expense_type == ExpenseType(expense_type)

    def test_rejects_invalid_expense_type(self) -> None:
        with pytest.raises(ValidationError):
            TripExpenseCreateRequest(**{**_MINIMAL, "expense_type": "not-a-real-type"})

    def test_rejects_invalid_trip_id(self) -> None:
        with pytest.raises(ValidationError):
            TripExpenseCreateRequest(**{**_MINIMAL, "trip_id": "not-a-uuid"})

    def test_rejects_vendor_name_over_max_length(self) -> None:
        with pytest.raises(ValidationError):
            TripExpenseCreateRequest(**{**_MINIMAL, "vendor_name": "x" * 256})

    def test_rejects_receipt_number_over_max_length(self) -> None:
        with pytest.raises(ValidationError):
            TripExpenseCreateRequest(**{**_MINIMAL, "receipt_number": "x" * 101})

    def test_accepts_optional_fields(self) -> None:
        request = TripExpenseCreateRequest(
            **_MINIMAL,
            description="Diesel refill",
            vendor_name="Sassoon Dock Fuel Co",
            receipt_number="RCPT-1042",
        )
        assert request.description == "Diesel refill"
        assert request.vendor_name == "Sassoon Dock Fuel Co"
        assert request.receipt_number == "RCPT-1042"


class TestTripExpenseUpdateRequest:
    def test_untouched_fields_are_excluded_from_dump(self) -> None:
        request = TripExpenseUpdateRequest(receipt_number="RCPT-1042-A")
        dumped = request.model_dump(exclude_unset=True)
        assert dumped == {"receipt_number": "RCPT-1042-A"}

    def test_all_fields_optional(self) -> None:
        request = TripExpenseUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_explicit_none_is_still_included(self) -> None:
        request = TripExpenseUpdateRequest(description=None)
        dumped = request.model_dump(exclude_unset=True)
        assert "description" in dumped
        assert dumped["description"] is None

    def test_rejects_zero_amount(self) -> None:
        with pytest.raises(ValidationError):
            TripExpenseUpdateRequest(amount="0")

    def test_rejects_negative_amount(self) -> None:
        with pytest.raises(ValidationError):
            TripExpenseUpdateRequest(amount="-1")

    def test_accepts_positive_amount(self) -> None:
        request = TripExpenseUpdateRequest(amount="4800.00")
        assert request.amount == Decimal("4800.00")

    def test_trip_id_and_expense_date_can_be_reassigned(self) -> None:
        new_trip_id = uuid.uuid4()
        new_date = date(2026, 8, 1)
        request = TripExpenseUpdateRequest(trip_id=new_trip_id, expense_date=new_date)
        assert request.model_dump(exclude_unset=True) == {
            "trip_id": new_trip_id,
            "expense_date": new_date,
        }

    def test_rejects_invalid_expense_type(self) -> None:
        with pytest.raises(ValidationError):
            TripExpenseUpdateRequest(expense_type="not-a-real-type")


_SORTABLE_FIELDS = ("expense_date", "amount", "created_at")


class TestTripExpenseListParams:
    def test_defaults(self) -> None:
        params = TripExpenseListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort == "-created_at"
        assert params.q is None
        assert params.trip_id is None
        assert params.expense_type is None
        assert params.expense_date_from is None
        assert params.expense_date_to is None

    @pytest.mark.parametrize(
        "value",
        [f"{prefix}{field}" for field in _SORTABLE_FIELDS for prefix in ("", "-")],
    )
    def test_accepts_every_sortable_field_ascending_and_descending(self, value: str) -> None:
        params = TripExpenseListParams(sort=value)
        assert params.sort == value

    def test_rejects_unknown_sort_field(self) -> None:
        with pytest.raises(ValidationError):
            TripExpenseListParams(sort="unknown_field")

    def test_rejects_unsortable_field_even_with_dash(self) -> None:
        with pytest.raises(ValidationError):
            TripExpenseListParams(sort="-trip_id")

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            TripExpenseListParams(page=0)

    def test_rejects_page_size_above_cap(self) -> None:
        with pytest.raises(ValidationError):
            TripExpenseListParams(page_size=101)

    def test_rejects_page_size_below_one(self) -> None:
        with pytest.raises(ValidationError):
            TripExpenseListParams(page_size=0)

    def test_accepts_trip_and_expense_type_filters(self) -> None:
        trip_id = uuid.uuid4()
        params = TripExpenseListParams(trip_id=trip_id, expense_type="ice")
        assert params.trip_id == trip_id
        assert params.expense_type == ExpenseType.ICE

    def test_rejects_invalid_expense_type_filter(self) -> None:
        with pytest.raises(ValidationError):
            TripExpenseListParams(expense_type="not-a-real-type")

    def test_accepts_expense_date_range_filters(self) -> None:
        params = TripExpenseListParams(
            expense_date_from="2026-07-01",
            expense_date_to="2026-07-31",
        )
        assert params.expense_date_from is not None
        assert params.expense_date_to is not None
        assert params.expense_date_from.isoformat() == "2026-07-01"
        assert params.expense_date_to.isoformat() == "2026-07-31"
