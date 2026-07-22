import uuid
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.trip_catches.constants import CatchGrade
from app.modules.trip_catches.schemas import (
    TripCatchCreateRequest,
    TripCatchListParams,
    TripCatchUpdateRequest,
)

_MINIMAL: dict[str, object] = {
    "trip_id": uuid.uuid4(),
    "fish_id": uuid.uuid4(),
    "quantity_caught": "100.500",
    "landing_date": date(2026, 7, 22),
}


class TestTripCatchCreateRequest:
    def test_minimal_payload_gets_sane_defaults(self) -> None:
        request = TripCatchCreateRequest(**_MINIMAL)
        assert request.grade is None
        assert request.landing_port is None
        assert request.remarks is None
        assert request.quantity_caught == Decimal("100.500")

    def test_rejects_missing_trip_id(self) -> None:
        payload = {k: v for k, v in _MINIMAL.items() if k != "trip_id"}
        with pytest.raises(ValidationError):
            TripCatchCreateRequest(**payload)

    def test_rejects_missing_fish_id(self) -> None:
        payload = {k: v for k, v in _MINIMAL.items() if k != "fish_id"}
        with pytest.raises(ValidationError):
            TripCatchCreateRequest(**payload)

    def test_rejects_missing_quantity_caught(self) -> None:
        payload = {k: v for k, v in _MINIMAL.items() if k != "quantity_caught"}
        with pytest.raises(ValidationError):
            TripCatchCreateRequest(**payload)

    def test_rejects_missing_landing_date(self) -> None:
        payload = {k: v for k, v in _MINIMAL.items() if k != "landing_date"}
        with pytest.raises(ValidationError):
            TripCatchCreateRequest(**payload)

    def test_rejects_zero_quantity_caught(self) -> None:
        with pytest.raises(ValidationError):
            TripCatchCreateRequest(**{**_MINIMAL, "quantity_caught": "0"})

    def test_rejects_negative_quantity_caught(self) -> None:
        with pytest.raises(ValidationError):
            TripCatchCreateRequest(**{**_MINIMAL, "quantity_caught": "-1"})

    def test_accepts_positive_quantity_caught(self) -> None:
        request = TripCatchCreateRequest(**{**_MINIMAL, "quantity_caught": "0.001"})
        assert request.quantity_caught == Decimal("0.001")

    @pytest.mark.parametrize("grade", ["A", "B", "C"])
    def test_accepts_every_grade(self, grade: str) -> None:
        request = TripCatchCreateRequest(**{**_MINIMAL, "grade": grade})
        assert request.grade == CatchGrade(grade)

    def test_rejects_invalid_grade(self) -> None:
        with pytest.raises(ValidationError):
            TripCatchCreateRequest(**{**_MINIMAL, "grade": "Z"})

    def test_rejects_invalid_trip_id(self) -> None:
        with pytest.raises(ValidationError):
            TripCatchCreateRequest(**{**_MINIMAL, "trip_id": "not-a-uuid"})

    def test_available_sold_waste_quantity_are_not_settable_fields(self) -> None:
        """Session 3's business rule fixes these at creation time - the
        schema doesn't expose them as inputs at all, so unknown-but-present
        keys are silently dropped by pydantic's default `extra="ignore"`."""
        request = TripCatchCreateRequest(
            **_MINIMAL,
            available_quantity="999",
            sold_quantity="999",
            waste_quantity="999",
        )
        assert not hasattr(request, "available_quantity")
        assert not hasattr(request, "sold_quantity")
        assert not hasattr(request, "waste_quantity")


class TestTripCatchUpdateRequest:
    def test_untouched_fields_are_excluded_from_dump(self) -> None:
        request = TripCatchUpdateRequest(remarks="Sold half")
        dumped = request.model_dump(exclude_unset=True)
        assert dumped == {"remarks": "Sold half"}

    def test_all_fields_optional(self) -> None:
        request = TripCatchUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_explicit_none_is_still_included(self) -> None:
        request = TripCatchUpdateRequest(grade=None)
        dumped = request.model_dump(exclude_unset=True)
        assert "grade" in dumped
        assert dumped["grade"] is None

    def test_rejects_zero_quantity_caught(self) -> None:
        with pytest.raises(ValidationError):
            TripCatchUpdateRequest(quantity_caught="0")

    def test_rejects_negative_available_quantity(self) -> None:
        with pytest.raises(ValidationError):
            TripCatchUpdateRequest(available_quantity="-1")

    def test_rejects_negative_sold_quantity(self) -> None:
        with pytest.raises(ValidationError):
            TripCatchUpdateRequest(sold_quantity="-1")

    def test_rejects_negative_waste_quantity(self) -> None:
        with pytest.raises(ValidationError):
            TripCatchUpdateRequest(waste_quantity="-1")

    def test_accepts_zero_available_sold_waste_quantity(self) -> None:
        request = TripCatchUpdateRequest(
            available_quantity="0", sold_quantity="0", waste_quantity="0"
        )
        assert request.available_quantity == Decimal("0")
        assert request.sold_quantity == Decimal("0")
        assert request.waste_quantity == Decimal("0")

    def test_trip_id_and_fish_id_can_be_reassigned(self) -> None:
        new_trip_id = uuid.uuid4()
        new_fish_id = uuid.uuid4()
        request = TripCatchUpdateRequest(trip_id=new_trip_id, fish_id=new_fish_id)
        assert request.model_dump(exclude_unset=True) == {
            "trip_id": new_trip_id,
            "fish_id": new_fish_id,
        }

    def test_rejects_invalid_grade(self) -> None:
        with pytest.raises(ValidationError):
            TripCatchUpdateRequest(grade="Z")


_SORTABLE_FIELDS = ("landing_date", "quantity_caught", "created_at")


class TestTripCatchListParams:
    def test_defaults(self) -> None:
        params = TripCatchListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort == "-created_at"
        assert params.q is None
        assert params.trip_id is None
        assert params.fish_id is None
        assert params.grade is None
        assert params.landing_date_from is None
        assert params.landing_date_to is None

    @pytest.mark.parametrize(
        "value",
        [f"{prefix}{field}" for field in _SORTABLE_FIELDS for prefix in ("", "-")],
    )
    def test_accepts_every_sortable_field_ascending_and_descending(self, value: str) -> None:
        params = TripCatchListParams(sort=value)
        assert params.sort == value

    def test_rejects_unknown_sort_field(self) -> None:
        with pytest.raises(ValidationError):
            TripCatchListParams(sort="unknown_field")

    def test_rejects_unsortable_field_even_with_dash(self) -> None:
        with pytest.raises(ValidationError):
            TripCatchListParams(sort="-trip_id")

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            TripCatchListParams(page=0)

    def test_rejects_page_size_above_cap(self) -> None:
        with pytest.raises(ValidationError):
            TripCatchListParams(page_size=101)

    def test_rejects_page_size_below_one(self) -> None:
        with pytest.raises(ValidationError):
            TripCatchListParams(page_size=0)

    def test_accepts_trip_and_fish_and_grade_filters(self) -> None:
        trip_id = uuid.uuid4()
        fish_id = uuid.uuid4()
        params = TripCatchListParams(trip_id=trip_id, fish_id=fish_id, grade="B")
        assert params.trip_id == trip_id
        assert params.fish_id == fish_id
        assert params.grade == CatchGrade.B

    def test_rejects_invalid_grade_filter(self) -> None:
        with pytest.raises(ValidationError):
            TripCatchListParams(grade="not-a-real-grade")

    def test_accepts_landing_date_range_filters(self) -> None:
        params = TripCatchListParams(
            landing_date_from="2026-07-01",
            landing_date_to="2026-07-31",
        )
        assert params.landing_date_from is not None
        assert params.landing_date_to is not None
        assert params.landing_date_from.isoformat() == "2026-07-01"
        assert params.landing_date_to.isoformat() == "2026-07-31"
