import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.boats.schemas import BoatCreateRequest, BoatListParams, BoatUpdateRequest

_MINIMAL: dict[str, object] = {
    "company_id": uuid.uuid4(),
    "code": "B-1",
    "name": "Sea Falcon",
    "registration_number": "REG-1",
}


class TestBoatCreateRequestDefaults:
    def test_minimal_payload_gets_sane_defaults(self) -> None:
        request = BoatCreateRequest(**_MINIMAL)
        assert request.is_active is True
        assert request.license_number is None
        assert request.boat_type is None
        assert request.capacity_kg is None
        assert request.captain_phone is None

    def test_rejects_blank_code(self) -> None:
        with pytest.raises(ValidationError):
            BoatCreateRequest(**{**_MINIMAL, "code": ""})

    def test_rejects_blank_name(self) -> None:
        with pytest.raises(ValidationError):
            BoatCreateRequest(**{**_MINIMAL, "name": ""})

    def test_rejects_blank_registration_number(self) -> None:
        with pytest.raises(ValidationError):
            BoatCreateRequest(**{**_MINIMAL, "registration_number": ""})

    def test_rejects_missing_company_id(self) -> None:
        payload = {k: v for k, v in _MINIMAL.items() if k != "company_id"}
        with pytest.raises(ValidationError):
            BoatCreateRequest(**payload)

    def test_rejects_invalid_company_id(self) -> None:
        with pytest.raises(ValidationError):
            BoatCreateRequest(**{**_MINIMAL, "company_id": "not-a-uuid"})


class TestCaptainPhoneValidation:
    @pytest.mark.parametrize("value", ["9876543210", "+919876543210", "1234567"])
    def test_accepts_valid_phone_numbers(self, value: str) -> None:
        request = BoatCreateRequest(**_MINIMAL, captain_phone=value)
        assert request.captain_phone == value

    def test_none_is_allowed(self) -> None:
        request = BoatCreateRequest(**_MINIMAL, captain_phone=None)
        assert request.captain_phone is None

    @pytest.mark.parametrize("value", ["abc", "123", "1" * 16, ""])
    def test_rejects_invalid_phone_numbers(self, value: str) -> None:
        with pytest.raises(ValidationError):
            BoatCreateRequest(**_MINIMAL, captain_phone=value)


class TestNumericValidation:
    def test_rejects_negative_capacity(self) -> None:
        with pytest.raises(ValidationError):
            BoatCreateRequest(**_MINIMAL, capacity_kg=Decimal("-1"))

    def test_rejects_more_than_three_decimal_places_on_capacity(self) -> None:
        with pytest.raises(ValidationError):
            BoatCreateRequest(**_MINIMAL, capacity_kg=Decimal("100.1234"))

    def test_accepts_a_valid_capacity(self) -> None:
        request = BoatCreateRequest(**_MINIMAL, capacity_kg=Decimal("12000.000"))
        assert request.capacity_kg == Decimal("12000.000")

    def test_rejects_negative_engine_hp(self) -> None:
        with pytest.raises(ValidationError):
            BoatCreateRequest(**_MINIMAL, engine_hp=-1)

    def test_accepts_zero_engine_hp(self) -> None:
        request = BoatCreateRequest(**_MINIMAL, engine_hp=0)
        assert request.engine_hp == 0


class TestBoatUpdateRequestPartialSemantics:
    def test_untouched_fields_are_excluded_from_dump(self) -> None:
        request = BoatUpdateRequest(name="New Name")
        dumped = request.model_dump(exclude_unset=True)
        assert dumped == {"name": "New Name"}

    def test_explicit_none_is_still_included(self) -> None:
        request = BoatUpdateRequest(license_number=None)
        dumped = request.model_dump(exclude_unset=True)
        assert "license_number" in dumped
        assert dumped["license_number"] is None

    def test_all_fields_optional(self) -> None:
        request = BoatUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_validators_still_apply_on_update(self) -> None:
        with pytest.raises(ValidationError):
            BoatUpdateRequest(captain_phone="bad-phone")

    def test_company_id_can_be_reassigned(self) -> None:
        new_company_id = uuid.uuid4()
        request = BoatUpdateRequest(company_id=new_company_id)
        assert request.model_dump(exclude_unset=True) == {"company_id": new_company_id}


class TestBoatListParams:
    def test_defaults(self) -> None:
        params = BoatListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort == "-created_at"
        assert params.q is None
        assert params.boat_type is None
        assert params.company_id is None
        assert params.is_active is None
        assert params.insurance_expired is None
        assert params.license_expired is None

    @pytest.mark.parametrize(
        "value", ["name", "-name", "code", "-code", "created_at", "-updated_at"]
    )
    def test_accepts_every_sortable_field_ascending_and_descending(self, value: str) -> None:
        params = BoatListParams(sort=value)
        assert params.sort == value

    def test_rejects_unknown_sort_field(self) -> None:
        with pytest.raises(ValidationError):
            BoatListParams(sort="unknown_field")

    def test_rejects_unsortable_field_even_with_dash(self) -> None:
        with pytest.raises(ValidationError):
            BoatListParams(sort="-captain_name")

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            BoatListParams(page=0)

    def test_rejects_page_size_above_cap(self) -> None:
        with pytest.raises(ValidationError):
            BoatListParams(page_size=101)

    def test_rejects_page_size_below_one(self) -> None:
        with pytest.raises(ValidationError):
            BoatListParams(page_size=0)

    def test_accepts_boolean_filters(self) -> None:
        params = BoatListParams(is_active=True, insurance_expired=False, license_expired=True)
        assert params.is_active is True
        assert params.insurance_expired is False
        assert params.license_expired is True
