import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.suppliers.constants import SupplierStatus
from app.modules.suppliers.schemas import (
    SupplierCreateRequest,
    SupplierListParams,
    SupplierResponse,
    SupplierUpdateRequest,
)

_MINIMAL = {"code": "SUP-1", "name": "Test Supplier"}


@dataclass
class _FakeSupplierRow:
    """A plain object standing in for a Supplier ORM instance - exercises
    SupplierResponse's `from_attributes=True` config without needing a real
    database session."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    legal_name: str | None
    gstin: str | None
    phone: str | None
    email: str | None
    address: str | None
    city: str | None
    state: str | None
    country: str | None
    contact_person: str | None
    credit_days: int
    opening_balance: Decimal
    outstanding_amount: Decimal
    status: SupplierStatus
    created_at: datetime
    updated_at: datetime


def _make_row(**overrides: object) -> _FakeSupplierRow:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "code": "SUP-001",
        "name": "Coastal Fish Suppliers",
        "legal_name": None,
        "gstin": None,
        "phone": None,
        "email": None,
        "address": None,
        "city": None,
        "state": None,
        "country": None,
        "contact_person": None,
        "credit_days": 0,
        "opening_balance": Decimal("0"),
        "outstanding_amount": Decimal("0"),
        "status": SupplierStatus.ACTIVE,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return _FakeSupplierRow(**defaults)  # type: ignore[arg-type]


class TestSupplierResponse:
    def test_builds_from_orm_like_object(self) -> None:
        row = _make_row(code="SUP-042", name="Ocean Traders")
        response = SupplierResponse.model_validate(row)
        assert response.code == "SUP-042"
        assert response.name == "Ocean Traders"
        assert response.status == SupplierStatus.ACTIVE
        assert response.outstanding_amount == Decimal("0")

    def test_round_trips_optional_fields_as_none(self) -> None:
        row = _make_row()
        response = SupplierResponse.model_validate(row)
        assert response.legal_name is None
        assert response.gstin is None
        assert response.phone is None
        assert response.email is None
        assert response.address is None

    def test_serializes_decimal_fields_as_strings(self) -> None:
        row = _make_row(opening_balance=Decimal("1000.50"), outstanding_amount=Decimal("250.25"))
        response = SupplierResponse.model_validate(row)
        dumped = response.model_dump(mode="json")
        assert dumped["opening_balance"] == "1000.50"
        assert dumped["outstanding_amount"] == "250.25"


class TestSupplierCreateRequestDefaults:
    def test_minimal_payload_gets_sane_defaults(self) -> None:
        request = SupplierCreateRequest(**_MINIMAL)
        assert request.credit_days == 0
        assert request.opening_balance == Decimal("0")
        assert request.legal_name is None

    def test_rejects_blank_code(self) -> None:
        with pytest.raises(ValidationError):
            SupplierCreateRequest(**{**_MINIMAL, "code": ""})

    def test_rejects_blank_name(self) -> None:
        with pytest.raises(ValidationError):
            SupplierCreateRequest(**{**_MINIMAL, "name": ""})

    def test_does_not_accept_status_or_outstanding_amount(self) -> None:
        # SupplierCreateRequest has no `status`/`outstanding_amount` fields
        # at all - the server always owns them (TASKS.md Sprint 11 Session
        # 2). Extra fields are silently ignored by pydantic's default
        # config, so this just documents they aren't part of the schema.
        assert "status" not in SupplierCreateRequest.model_fields
        assert "outstanding_amount" not in SupplierCreateRequest.model_fields


class TestSupplierEmailValidation:
    def test_accepts_and_lowercases_a_normal_email(self) -> None:
        request = SupplierCreateRequest(**_MINIMAL, email="Contact@Example.COM")
        assert request.email == "contact@example.com"

    def test_none_is_allowed(self) -> None:
        request = SupplierCreateRequest(**_MINIMAL, email=None)
        assert request.email is None

    @pytest.mark.parametrize(
        "value", ["not-an-email", "missing-domain@", "@missing-local.com", "no-at-sign"]
    )
    def test_rejects_malformed_addresses(self, value: str) -> None:
        with pytest.raises(ValidationError):
            SupplierCreateRequest(**_MINIMAL, email=value)


class TestSupplierPhoneValidation:
    @pytest.mark.parametrize("value", ["9876543210", "+919876543210", "1234567"])
    def test_accepts_valid_numbers(self, value: str) -> None:
        request = SupplierCreateRequest(**_MINIMAL, phone=value)
        assert request.phone == value

    @pytest.mark.parametrize("value", ["123", "abcdefghij", "98765-43210", "12345678901234567"])
    def test_rejects_invalid_numbers(self, value: str) -> None:
        with pytest.raises(ValidationError):
            SupplierCreateRequest(**_MINIMAL, phone=value)


class TestSupplierGstinValidation:
    def test_accepts_and_uppercases_a_valid_gstin(self) -> None:
        request = SupplierCreateRequest(**_MINIMAL, gstin="27abcde1234f1z5")
        assert request.gstin == "27ABCDE1234F1Z5"

    @pytest.mark.parametrize("value", ["INVALIDGSTIN", "27ABCDE1234F1Z", "1234567890ABCDE", ""])
    def test_rejects_invalid_gstin(self, value: str) -> None:
        with pytest.raises(ValidationError):
            SupplierCreateRequest(**_MINIMAL, gstin=value)


class TestSupplierMoneyValidation:
    def test_rejects_negative_opening_balance(self) -> None:
        with pytest.raises(ValidationError):
            SupplierCreateRequest(**_MINIMAL, opening_balance=Decimal("-1"))

    def test_rejects_more_than_two_decimal_places(self) -> None:
        with pytest.raises(ValidationError):
            SupplierCreateRequest(**_MINIMAL, opening_balance=Decimal("100.123"))

    def test_rejects_negative_credit_days(self) -> None:
        with pytest.raises(ValidationError):
            SupplierCreateRequest(**_MINIMAL, credit_days=-1)


class TestSupplierUpdateRequestPartialSemantics:
    def test_untouched_fields_are_excluded_from_dump(self) -> None:
        request = SupplierUpdateRequest(name="New Name")
        dumped = request.model_dump(exclude_unset=True)
        assert dumped == {"name": "New Name"}

    def test_explicit_none_is_still_included(self) -> None:
        request = SupplierUpdateRequest(legal_name=None)
        dumped = request.model_dump(exclude_unset=True)
        assert "legal_name" in dumped
        assert dumped["legal_name"] is None

    def test_all_fields_optional(self) -> None:
        request = SupplierUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_validators_still_apply_on_update(self) -> None:
        with pytest.raises(ValidationError):
            SupplierUpdateRequest(email="not-an-email")


class TestSupplierListParams:
    def test_defaults(self) -> None:
        params = SupplierListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort == "-created_at"
        assert params.q is None

    @pytest.mark.parametrize("value", ["name", "-name", "code", "-code", "created_at"])
    def test_accepts_every_sortable_field(self, value: str) -> None:
        params = SupplierListParams(sort=value)
        assert params.sort == value

    def test_rejects_unknown_sort_field(self) -> None:
        with pytest.raises(ValidationError):
            SupplierListParams(sort="unknown_field")

    def test_rejects_unsortable_field_even_with_dash(self) -> None:
        with pytest.raises(ValidationError):
            SupplierListParams(sort="-gstin")

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            SupplierListParams(page=0)

    def test_rejects_page_size_above_cap(self) -> None:
        with pytest.raises(ValidationError):
            SupplierListParams(page_size=101)
