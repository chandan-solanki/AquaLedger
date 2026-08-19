import pytest
from pydantic import ValidationError

from app.modules.company_profile.schemas import CompanyProfileUpsertRequest


class TestLegalName:
    def test_none_is_allowed_on_a_partial_update(self) -> None:
        request = CompanyProfileUpsertRequest()
        assert request.legal_name is None

    def test_rejects_blank_legal_name(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileUpsertRequest(legal_name="")

    def test_accepts_a_normal_legal_name(self) -> None:
        request = CompanyProfileUpsertRequest(legal_name="Ocean Fresh Seafoods Pvt Ltd")
        assert request.legal_name == "Ocean Fresh Seafoods Pvt Ltd"


class TestEmailValidation:
    def test_accepts_and_lowercases_a_normal_email(self) -> None:
        request = CompanyProfileUpsertRequest(email="Info@Example.COM")
        assert request.email == "info@example.com"

    def test_none_is_allowed(self) -> None:
        request = CompanyProfileUpsertRequest(email=None)
        assert request.email is None

    @pytest.mark.parametrize(
        "value", ["not-an-email", "missing-domain@", "@missing-local.com", "no-at-sign"]
    )
    def test_rejects_malformed_addresses(self, value: str) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileUpsertRequest(email=value)


class TestPhoneValidation:
    @pytest.mark.parametrize("value", ["9876543210", "+919876543210", "1234567"])
    def test_accepts_valid_phone_numbers(self, value: str) -> None:
        request = CompanyProfileUpsertRequest(phone=value)
        assert request.phone == value

    @pytest.mark.parametrize("value", ["123", "abcdefghij", "12345678901234567"])
    def test_rejects_invalid_phone_numbers(self, value: str) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileUpsertRequest(phone=value)

    def test_alt_phone_uses_the_same_validator(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileUpsertRequest(alt_phone="123")


class TestGstinValidation:
    def test_accepts_and_uppercases_a_valid_gstin(self) -> None:
        request = CompanyProfileUpsertRequest(gstin="27abcde1234f1z5")
        assert request.gstin == "27ABCDE1234F1Z5"

    @pytest.mark.parametrize("value", ["BADGSTIN", "27ABCDE1234F1Z", "27abcde1234f1z5z"])
    def test_rejects_invalid_gstin(self, value: str) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileUpsertRequest(gstin=value)


class TestPanValidation:
    def test_accepts_and_uppercases_a_valid_pan(self) -> None:
        request = CompanyProfileUpsertRequest(pan="abcde1234f")
        assert request.pan == "ABCDE1234F"

    @pytest.mark.parametrize("value", ["ABCDE1234", "12345ABCDE", "ABCDE12345", "abcdefghij"])
    def test_rejects_invalid_pan(self, value: str) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileUpsertRequest(pan=value)


class TestFieldLengthLimits:
    def test_display_name_over_255_chars_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileUpsertRequest(display_name="x" * 256)

    def test_state_code_over_2_chars_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileUpsertRequest(state_code="ABC")

    def test_pincode_over_10_chars_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileUpsertRequest(pincode="12345678901")
