import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.modules.trips.constants import TripStatus, TripType
from app.modules.trips.schemas import TripCreateRequest, TripListParams, TripUpdateRequest

_MINIMAL: dict[str, object] = {
    "boat_id": uuid.uuid4(),
    "trip_number": "TRIP-001",
    "trip_type": "fishing",
    "departure_datetime": datetime(2026, 8, 1, 4, 0, tzinfo=UTC),
}


class TestTripCreateRequestDefaults:
    def test_minimal_payload_gets_sane_defaults(self) -> None:
        request = TripCreateRequest(**_MINIMAL)
        assert request.status == TripStatus.PLANNED
        assert request.is_active is True
        assert request.captain_name is None
        assert request.departure_port is None
        assert request.arrival_port is None
        assert request.expected_return_datetime is None
        assert request.actual_return_datetime is None
        assert request.notes is None

    def test_rejects_blank_trip_number(self) -> None:
        with pytest.raises(ValidationError):
            TripCreateRequest(**{**_MINIMAL, "trip_number": ""})

    def test_rejects_missing_boat_id(self) -> None:
        payload = {k: v for k, v in _MINIMAL.items() if k != "boat_id"}
        with pytest.raises(ValidationError):
            TripCreateRequest(**payload)

    def test_rejects_invalid_boat_id(self) -> None:
        with pytest.raises(ValidationError):
            TripCreateRequest(**{**_MINIMAL, "boat_id": "not-a-uuid"})

    def test_rejects_missing_trip_type(self) -> None:
        payload = {k: v for k, v in _MINIMAL.items() if k != "trip_type"}
        with pytest.raises(ValidationError):
            TripCreateRequest(**payload)

    def test_rejects_invalid_trip_type(self) -> None:
        with pytest.raises(ValidationError):
            TripCreateRequest(**{**_MINIMAL, "trip_type": "not-a-real-type"})

    def test_rejects_missing_departure_datetime(self) -> None:
        payload = {k: v for k, v in _MINIMAL.items() if k != "departure_datetime"}
        with pytest.raises(ValidationError):
            TripCreateRequest(**payload)

    def test_accepts_an_explicit_status(self) -> None:
        request = TripCreateRequest(**_MINIMAL, status="departed")
        assert request.status == TripStatus.DEPARTED

    def test_rejects_invalid_status(self) -> None:
        with pytest.raises(ValidationError):
            TripCreateRequest(**_MINIMAL, status="not-a-real-status")


class TestTripUpdateRequestPartialSemantics:
    def test_untouched_fields_are_excluded_from_dump(self) -> None:
        request = TripUpdateRequest(captain_name="New Captain")
        dumped = request.model_dump(exclude_unset=True)
        assert dumped == {"captain_name": "New Captain"}

    def test_explicit_none_is_still_included(self) -> None:
        request = TripUpdateRequest(actual_return_datetime=None)
        dumped = request.model_dump(exclude_unset=True)
        assert "actual_return_datetime" in dumped
        assert dumped["actual_return_datetime"] is None

    def test_all_fields_optional(self) -> None:
        request = TripUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_boat_id_can_be_reassigned(self) -> None:
        new_boat_id = uuid.uuid4()
        request = TripUpdateRequest(boat_id=new_boat_id)
        assert request.model_dump(exclude_unset=True) == {"boat_id": new_boat_id}

    def test_status_transition_is_a_plain_field_update(self) -> None:
        request = TripUpdateRequest(status="returned")
        assert request.model_dump(exclude_unset=True) == {"status": TripStatus.RETURNED}

    def test_rejects_blank_trip_number(self) -> None:
        with pytest.raises(ValidationError):
            TripUpdateRequest(trip_number="")


_SORTABLE_FIELDS = ("trip_number", "departure_datetime", "created_at", "updated_at")


class TestTripListParams:
    def test_defaults(self) -> None:
        params = TripListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort == "-created_at"
        assert params.q is None
        assert params.boat_id is None
        assert params.status is None
        assert params.trip_type is None
        assert params.departure_date_from is None
        assert params.departure_date_to is None
        assert params.return_date_from is None
        assert params.return_date_to is None

    @pytest.mark.parametrize(
        "value",
        [f"{prefix}{field}" for field in _SORTABLE_FIELDS for prefix in ("", "-")],
    )
    def test_accepts_every_sortable_field_ascending_and_descending(self, value: str) -> None:
        params = TripListParams(sort=value)
        assert params.sort == value

    def test_rejects_unknown_sort_field(self) -> None:
        with pytest.raises(ValidationError):
            TripListParams(sort="unknown_field")

    def test_rejects_unsortable_field_even_with_dash(self) -> None:
        with pytest.raises(ValidationError):
            TripListParams(sort="-captain_name")

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            TripListParams(page=0)

    def test_rejects_page_size_above_cap(self) -> None:
        with pytest.raises(ValidationError):
            TripListParams(page_size=101)

    def test_rejects_page_size_below_one(self) -> None:
        with pytest.raises(ValidationError):
            TripListParams(page_size=0)

    def test_accepts_status_and_trip_type_filters(self) -> None:
        params = TripListParams(status="planned", trip_type="fishing")
        assert params.status == TripStatus.PLANNED
        assert params.trip_type == TripType.FISHING

    def test_rejects_invalid_status_filter(self) -> None:
        with pytest.raises(ValidationError):
            TripListParams(status="not-a-real-status")

    def test_accepts_date_range_filters(self) -> None:
        params = TripListParams(
            departure_date_from="2026-08-01",
            departure_date_to="2026-08-31",
            return_date_from="2026-09-01",
            return_date_to="2026-09-30",
        )
        assert params.departure_date_from is not None
        assert params.return_date_to is not None
        assert params.departure_date_from.isoformat() == "2026-08-01"
        assert params.return_date_to.isoformat() == "2026-09-30"

    def test_accepts_boat_id_filter(self) -> None:
        boat_id = uuid.uuid4()
        params = TripListParams(boat_id=boat_id)
        assert params.boat_id == boat_id
