from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.fish.constants import FishUnit
from app.modules.fish.schemas import FishCreateRequest, FishListParams, FishUpdateRequest

_MINIMAL = {"code": "F-1", "name": "Pomfret"}


class TestFishCreateRequestDefaults:
    def test_minimal_payload_gets_sane_defaults(self) -> None:
        request = FishCreateRequest(**_MINIMAL)
        assert request.unit == FishUnit.KG
        assert request.is_active is True
        assert request.default_purchase_rate is None
        assert request.default_sale_rate is None
        assert request.local_name is None

    def test_rejects_blank_code(self) -> None:
        with pytest.raises(ValidationError):
            FishCreateRequest(**{**_MINIMAL, "code": ""})

    def test_rejects_blank_name(self) -> None:
        with pytest.raises(ValidationError):
            FishCreateRequest(**{**_MINIMAL, "name": ""})

    def test_rejects_invalid_unit(self) -> None:
        with pytest.raises(ValidationError):
            FishCreateRequest(**{**_MINIMAL, "unit": "not-a-unit"})

    def test_accepts_every_unit(self) -> None:
        for value in FishUnit:
            request = FishCreateRequest(**{**_MINIMAL, "unit": value})
            assert request.unit == value


class TestHsnCodeValidation:
    @pytest.mark.parametrize("value", ["0302", "030214", "03021400"])
    def test_accepts_valid_hsn_codes(self, value: str) -> None:
        request = FishCreateRequest(**_MINIMAL, hsn_code=value)
        assert request.hsn_code == value

    def test_none_is_allowed(self) -> None:
        request = FishCreateRequest(**_MINIMAL, hsn_code=None)
        assert request.hsn_code is None

    @pytest.mark.parametrize("value", ["12", "ABCD", "123456789", ""])
    def test_rejects_invalid_hsn_codes(self, value: str) -> None:
        with pytest.raises(ValidationError):
            FishCreateRequest(**_MINIMAL, hsn_code=value)


class TestRateValidation:
    def test_rejects_negative_purchase_rate(self) -> None:
        with pytest.raises(ValidationError):
            FishCreateRequest(**_MINIMAL, default_purchase_rate=Decimal("-1"))

    def test_rejects_negative_sale_rate(self) -> None:
        with pytest.raises(ValidationError):
            FishCreateRequest(**_MINIMAL, default_sale_rate=Decimal("-1"))

    def test_rejects_more_than_four_decimal_places(self) -> None:
        with pytest.raises(ValidationError):
            FishCreateRequest(**_MINIMAL, default_sale_rate=Decimal("100.12345"))

    def test_rejects_more_than_twelve_significant_digits(self) -> None:
        with pytest.raises(ValidationError):
            FishCreateRequest(**_MINIMAL, default_sale_rate=Decimal("123456789.1234"))

    def test_accepts_a_valid_rate(self) -> None:
        request = FishCreateRequest(**_MINIMAL, default_sale_rate=Decimal("550.5000"))
        assert request.default_sale_rate == Decimal("550.5000")


class TestFishUpdateRequestPartialSemantics:
    def test_untouched_fields_are_excluded_from_dump(self) -> None:
        request = FishUpdateRequest(name="New Name")
        dumped = request.model_dump(exclude_unset=True)
        assert dumped == {"name": "New Name"}

    def test_explicit_none_is_still_included(self) -> None:
        request = FishUpdateRequest(local_name=None)
        dumped = request.model_dump(exclude_unset=True)
        assert "local_name" in dumped
        assert dumped["local_name"] is None

    def test_all_fields_optional(self) -> None:
        request = FishUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_validators_still_apply_on_update(self) -> None:
        with pytest.raises(ValidationError):
            FishUpdateRequest(hsn_code="bad")


class TestFishListParams:
    def test_defaults(self) -> None:
        params = FishListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort == "-created_at"
        assert params.q is None
        assert params.category is None
        assert params.unit is None
        assert params.is_active is None

    @pytest.mark.parametrize(
        "value", ["name", "-name", "code", "-code", "created_at", "-updated_at"]
    )
    def test_accepts_every_sortable_field_ascending_and_descending(self, value: str) -> None:
        params = FishListParams(sort=value)
        assert params.sort == value

    def test_rejects_unknown_sort_field(self) -> None:
        with pytest.raises(ValidationError):
            FishListParams(sort="unknown_field")

    def test_rejects_unsortable_field_even_with_dash(self) -> None:
        with pytest.raises(ValidationError):
            FishListParams(sort="-category")

    def test_accepts_every_unit_filter(self) -> None:
        for value in FishUnit:
            params = FishListParams(unit=value)
            assert params.unit == value

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            FishListParams(page=0)

    def test_rejects_page_size_above_cap(self) -> None:
        with pytest.raises(ValidationError):
            FishListParams(page_size=101)

    def test_rejects_page_size_below_one(self) -> None:
        with pytest.raises(ValidationError):
            FishListParams(page_size=0)
