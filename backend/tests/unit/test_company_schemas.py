from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.companies.constants import CompanyStatus, CompanyType, OpeningBalanceType
from app.modules.companies.schemas import (
    CompanyCreateRequest,
    CompanyListParams,
    CompanyUpdateRequest,
)

_MINIMAL = {"code": "C-1", "name": "Test Co", "company_type": CompanyType.CUSTOMER}


class TestCompanyCreateRequestDefaults:
    def test_minimal_payload_gets_sane_defaults(self) -> None:
        request = CompanyCreateRequest(**_MINIMAL)
        assert request.status == CompanyStatus.ACTIVE
        assert request.credit_limit == Decimal("0")
        assert request.credit_days == 0
        assert request.opening_balance == Decimal("0")
        assert request.opening_balance_type is None
        assert request.legal_name is None

    def test_rejects_blank_code(self) -> None:
        with pytest.raises(ValidationError):
            CompanyCreateRequest(**{**_MINIMAL, "code": ""})

    def test_rejects_blank_name(self) -> None:
        with pytest.raises(ValidationError):
            CompanyCreateRequest(**{**_MINIMAL, "name": ""})

    def test_rejects_invalid_company_type(self) -> None:
        with pytest.raises(ValidationError):
            CompanyCreateRequest(**{**_MINIMAL, "company_type": "not-a-type"})

    def test_accepts_every_company_type(self) -> None:
        for value in CompanyType:
            request = CompanyCreateRequest(**{**_MINIMAL, "company_type": value})
            assert request.company_type == value

    def test_accepts_opening_balance_type(self) -> None:
        request = CompanyCreateRequest(
            **_MINIMAL, opening_balance_type=OpeningBalanceType.DEBIT
        )
        assert request.opening_balance_type == OpeningBalanceType.DEBIT


class TestEmailValidation:
    def test_accepts_and_lowercases_a_normal_email(self) -> None:
        request = CompanyCreateRequest(**_MINIMAL, email="Contact@Example.COM")
        assert request.email == "contact@example.com"

    def test_none_is_allowed(self) -> None:
        request = CompanyCreateRequest(**_MINIMAL, email=None)
        assert request.email is None

    @pytest.mark.parametrize(
        "value", ["not-an-email", "missing-domain@", "@missing-local.com", "no-at-sign"]
    )
    def test_rejects_malformed_addresses(self, value: str) -> None:
        with pytest.raises(ValidationError):
            CompanyCreateRequest(**_MINIMAL, email=value)


class TestPhoneValidation:
    @pytest.mark.parametrize("value", ["9876543210", "+919876543210", "1234567"])
    def test_accepts_valid_numbers(self, value: str) -> None:
        request = CompanyCreateRequest(**_MINIMAL, phone=value)
        assert request.phone == value

    @pytest.mark.parametrize("value", ["123", "abcdefghij", "98765-43210", "12345678901234567"])
    def test_rejects_invalid_numbers(self, value: str) -> None:
        with pytest.raises(ValidationError):
            CompanyCreateRequest(**_MINIMAL, phone=value)

    def test_alt_phone_uses_the_same_validator(self) -> None:
        with pytest.raises(ValidationError):
            CompanyCreateRequest(**_MINIMAL, alt_phone="bad")


class TestGstinValidation:
    def test_accepts_and_uppercases_a_valid_gstin(self) -> None:
        request = CompanyCreateRequest(**_MINIMAL, gstin="27abcde1234f1z5")
        assert request.gstin == "27ABCDE1234F1Z5"

    @pytest.mark.parametrize(
        "value", ["INVALIDGSTIN", "27ABCDE1234F1Z", "1234567890ABCDE", ""]
    )
    def test_rejects_invalid_gstin(self, value: str) -> None:
        with pytest.raises(ValidationError):
            CompanyCreateRequest(**_MINIMAL, gstin=value)


class TestMoneyValidation:
    def test_rejects_negative_credit_limit(self) -> None:
        with pytest.raises(ValidationError):
            CompanyCreateRequest(**_MINIMAL, credit_limit=Decimal("-1"))

    def test_rejects_negative_opening_balance(self) -> None:
        with pytest.raises(ValidationError):
            CompanyCreateRequest(**_MINIMAL, opening_balance=Decimal("-1"))

    def test_rejects_more_than_two_decimal_places(self) -> None:
        with pytest.raises(ValidationError):
            CompanyCreateRequest(**_MINIMAL, credit_limit=Decimal("100.123"))

    def test_rejects_more_than_fourteen_significant_digits(self) -> None:
        with pytest.raises(ValidationError):
            CompanyCreateRequest(**_MINIMAL, credit_limit=Decimal("1234567890123.45"))

    def test_rejects_negative_credit_days(self) -> None:
        with pytest.raises(ValidationError):
            CompanyCreateRequest(**_MINIMAL, credit_days=-1)


class TestCompanyUpdateRequestPartialSemantics:
    def test_untouched_fields_are_excluded_from_dump(self) -> None:
        request = CompanyUpdateRequest(name="New Name")
        dumped = request.model_dump(exclude_unset=True)
        assert dumped == {"name": "New Name"}

    def test_explicit_none_is_still_included(self) -> None:
        request = CompanyUpdateRequest(legal_name=None)
        dumped = request.model_dump(exclude_unset=True)
        assert "legal_name" in dumped
        assert dumped["legal_name"] is None

    def test_all_fields_optional(self) -> None:
        request = CompanyUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_validators_still_apply_on_update(self) -> None:
        with pytest.raises(ValidationError):
            CompanyUpdateRequest(email="not-an-email")


class TestCompanyListParams:
    def test_defaults(self) -> None:
        params = CompanyListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort == "-created_at"
        assert params.q is None

    @pytest.mark.parametrize(
        "value", ["name", "-name", "code", "-code", "created_at", "-updated_at"]
    )
    def test_accepts_every_sortable_field_ascending_and_descending(self, value: str) -> None:
        params = CompanyListParams(sort=value)
        assert params.sort == value

    def test_rejects_unknown_sort_field(self) -> None:
        with pytest.raises(ValidationError):
            CompanyListParams(sort="unknown_field")

    def test_rejects_unsortable_field_even_with_dash(self) -> None:
        with pytest.raises(ValidationError):
            CompanyListParams(sort="-legal_name")

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            CompanyListParams(page=0)

    def test_rejects_page_size_above_cap(self) -> None:
        with pytest.raises(ValidationError):
            CompanyListParams(page_size=101)

    def test_rejects_page_size_below_one(self) -> None:
        with pytest.raises(ValidationError):
            CompanyListParams(page_size=0)
