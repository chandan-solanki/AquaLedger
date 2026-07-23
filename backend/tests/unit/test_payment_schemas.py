import uuid
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.payments.constants import PaymentMethod, PaymentStatus
from app.modules.payments.schemas import (
    PaymentAllocationCreateRequest,
    PaymentAllocationUpdateRequest,
    PaymentCreateRequest,
    PaymentListParams,
    PaymentUpdateRequest,
)

_MINIMAL: dict[str, object] = {
    "company_id": uuid.uuid4(),
    "payment_date": date(2026, 7, 23),
    "payment_method": "cheque",
    "amount": "1000.00",
}

_MINIMAL_ALLOCATION: dict[str, object] = {
    "invoice_id": uuid.uuid4(),
    "allocated_amount": "500.00",
}


class TestPaymentCreateRequest:
    def test_minimal_payload_gets_sane_defaults(self) -> None:
        request = PaymentCreateRequest(**_MINIMAL)
        assert request.reference_number is None
        assert request.bank_name is None
        assert request.remarks is None

    @pytest.mark.parametrize("field", ["company_id", "payment_date", "payment_method", "amount"])
    def test_rejects_missing_required_field(self, field: str) -> None:
        payload = {k: v for k, v in _MINIMAL.items() if k != field}
        with pytest.raises(ValidationError):
            PaymentCreateRequest(**payload)

    def test_rejects_invalid_company_id(self) -> None:
        with pytest.raises(ValidationError):
            PaymentCreateRequest(**{**_MINIMAL, "company_id": "not-a-uuid"})

    def test_rejects_invalid_payment_method(self) -> None:
        with pytest.raises(ValidationError):
            PaymentCreateRequest(**{**_MINIMAL, "payment_method": "not-a-real-method"})

    def test_rejects_zero_amount(self) -> None:
        with pytest.raises(ValidationError):
            PaymentCreateRequest(**{**_MINIMAL, "amount": "0"})

    def test_rejects_negative_amount(self) -> None:
        with pytest.raises(ValidationError):
            PaymentCreateRequest(**{**_MINIMAL, "amount": "-1"})

    def test_accepts_small_positive_amount(self) -> None:
        request = PaymentCreateRequest(**{**_MINIMAL, "amount": "0.01"})
        assert request.amount == Decimal("0.01")

    def test_accepts_optional_fields(self) -> None:
        request = PaymentCreateRequest(
            **_MINIMAL,
            reference_number="445512",
            bank_name="State Bank",
            remarks="Against pending invoices",
        )
        assert request.reference_number == "445512"
        assert request.bank_name == "State Bank"
        assert request.remarks == "Against pending invoices"

    def test_does_not_accept_server_owned_fields(self) -> None:
        """payment_number/allocated_amount/unallocated_amount/status must
        never be client-supplied - the server owns them entirely
        (PaymentService.create). Extra/unknown keys are simply ignored by
        pydantic's default config, not rejected, but they must not end up
        on the model."""
        request = PaymentCreateRequest(
            **_MINIMAL,
            payment_number="PAY-0001",
            allocated_amount="500.00",
            unallocated_amount="500.00",
            status="posted",
        )
        assert not hasattr(request, "payment_number")
        assert not hasattr(request, "allocated_amount")
        assert not hasattr(request, "unallocated_amount")
        assert not hasattr(request, "status")


class TestPaymentUpdateRequest:
    def test_untouched_fields_are_excluded_from_dump(self) -> None:
        request = PaymentUpdateRequest(remarks="Revised")
        dumped = request.model_dump(exclude_unset=True)
        assert dumped == {"remarks": "Revised"}

    def test_all_fields_optional(self) -> None:
        request = PaymentUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_explicit_none_is_still_included(self) -> None:
        request = PaymentUpdateRequest(reference_number=None)
        dumped = request.model_dump(exclude_unset=True)
        assert "reference_number" in dumped
        assert dumped["reference_number"] is None

    def test_company_id_and_amount_can_be_reassigned(self) -> None:
        new_company_id = uuid.uuid4()
        request = PaymentUpdateRequest(company_id=new_company_id, amount="2000.00")
        assert request.model_dump(exclude_unset=True) == {
            "company_id": new_company_id,
            "amount": Decimal("2000.00"),
        }

    def test_rejects_invalid_company_id(self) -> None:
        with pytest.raises(ValidationError):
            PaymentUpdateRequest(company_id="not-a-uuid")

    def test_rejects_zero_amount(self) -> None:
        with pytest.raises(ValidationError):
            PaymentUpdateRequest(amount="0")

    def test_rejects_negative_amount(self) -> None:
        with pytest.raises(ValidationError):
            PaymentUpdateRequest(amount="-1")

    def test_does_not_accept_server_owned_fields(self) -> None:
        request = PaymentUpdateRequest(status="posted", payment_number="PAY-0001")
        assert not hasattr(request, "status")
        assert not hasattr(request, "payment_number")


_SORTABLE_FIELDS = ("payment_date", "payment_number", "amount", "created_at")


class TestPaymentListParams:
    def test_defaults(self) -> None:
        params = PaymentListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort == "-created_at"
        assert params.q is None
        assert params.status is None
        assert params.company_id is None
        assert params.payment_method is None
        assert params.payment_date_from is None
        assert params.payment_date_to is None

    @pytest.mark.parametrize(
        "value",
        [f"{prefix}{field}" for field in _SORTABLE_FIELDS for prefix in ("", "-")],
    )
    def test_accepts_every_sortable_field_ascending_and_descending(self, value: str) -> None:
        params = PaymentListParams(sort=value)
        assert params.sort == value

    def test_rejects_unknown_sort_field(self) -> None:
        with pytest.raises(ValidationError):
            PaymentListParams(sort="unknown_field")

    def test_rejects_unsortable_field_even_with_dash(self) -> None:
        with pytest.raises(ValidationError):
            PaymentListParams(sort="-company_id")

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            PaymentListParams(page=0)

    def test_rejects_page_size_above_cap(self) -> None:
        with pytest.raises(ValidationError):
            PaymentListParams(page_size=101)

    def test_rejects_page_size_below_one(self) -> None:
        with pytest.raises(ValidationError):
            PaymentListParams(page_size=0)

    def test_accepts_status_company_and_method_filters(self) -> None:
        company_id = uuid.uuid4()
        params = PaymentListParams(status="draft", company_id=company_id, payment_method="upi")
        assert params.status == PaymentStatus.DRAFT
        assert params.company_id == company_id
        assert params.payment_method == PaymentMethod.UPI

    def test_rejects_invalid_status_filter(self) -> None:
        with pytest.raises(ValidationError):
            PaymentListParams(status="not-a-real-status")

    def test_accepts_payment_date_range_filters(self) -> None:
        params = PaymentListParams(
            payment_date_from="2026-07-01",
            payment_date_to="2026-07-31",
        )
        assert params.payment_date_from is not None
        assert params.payment_date_to is not None
        assert params.payment_date_from.isoformat() == "2026-07-01"
        assert params.payment_date_to.isoformat() == "2026-07-31"


class TestPaymentAllocationCreateRequest:
    def test_minimal_payload(self) -> None:
        request = PaymentAllocationCreateRequest(**_MINIMAL_ALLOCATION)
        assert request.allocated_amount == Decimal("500.00")

    @pytest.mark.parametrize("field", ["invoice_id", "allocated_amount"])
    def test_rejects_missing_required_field(self, field: str) -> None:
        payload = {k: v for k, v in _MINIMAL_ALLOCATION.items() if k != field}
        with pytest.raises(ValidationError):
            PaymentAllocationCreateRequest(**payload)

    def test_rejects_invalid_invoice_id(self) -> None:
        with pytest.raises(ValidationError):
            PaymentAllocationCreateRequest(**{**_MINIMAL_ALLOCATION, "invoice_id": "not-a-uuid"})

    def test_rejects_zero_allocated_amount(self) -> None:
        with pytest.raises(ValidationError):
            PaymentAllocationCreateRequest(**{**_MINIMAL_ALLOCATION, "allocated_amount": "0"})

    def test_rejects_negative_allocated_amount(self) -> None:
        with pytest.raises(ValidationError):
            PaymentAllocationCreateRequest(**{**_MINIMAL_ALLOCATION, "allocated_amount": "-1"})

    def test_accepts_small_positive_allocated_amount(self) -> None:
        request = PaymentAllocationCreateRequest(
            **{**_MINIMAL_ALLOCATION, "allocated_amount": "0.01"}
        )
        assert request.allocated_amount == Decimal("0.01")


class TestPaymentAllocationUpdateRequest:
    def test_untouched_fields_are_excluded_from_dump(self) -> None:
        request = PaymentAllocationUpdateRequest(allocated_amount=Decimal("250.00"))
        dumped = request.model_dump(exclude_unset=True)
        assert dumped == {"allocated_amount": Decimal("250.00")}

    def test_all_fields_optional(self) -> None:
        request = PaymentAllocationUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_invoice_id_can_be_reassigned(self) -> None:
        new_invoice_id = uuid.uuid4()
        request = PaymentAllocationUpdateRequest(invoice_id=new_invoice_id)
        assert request.model_dump(exclude_unset=True) == {"invoice_id": new_invoice_id}

    def test_rejects_zero_allocated_amount(self) -> None:
        with pytest.raises(ValidationError):
            PaymentAllocationUpdateRequest(allocated_amount="0")

    def test_rejects_negative_allocated_amount(self) -> None:
        with pytest.raises(ValidationError):
            PaymentAllocationUpdateRequest(allocated_amount="-1")

    def test_rejects_invalid_invoice_id(self) -> None:
        with pytest.raises(ValidationError):
            PaymentAllocationUpdateRequest(invoice_id="not-a-uuid")
