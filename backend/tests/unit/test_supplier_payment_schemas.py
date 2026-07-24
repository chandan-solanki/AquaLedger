import uuid
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.supplier_payments.constants import PaymentMethod, SupplierPaymentStatus
from app.modules.supplier_payments.schemas import (
    SupplierPaymentCreateRequest,
    SupplierPaymentListParams,
    SupplierPaymentUpdateRequest,
)

_MINIMAL: dict[str, object] = {
    "supplier_id": uuid.uuid4(),
    "payment_date": date(2026, 7, 23),
    "payment_method": "cheque",
    "amount": "150000.00",
}


class TestSupplierPaymentCreateRequest:
    def test_minimal_payload_gets_sane_defaults(self) -> None:
        request = SupplierPaymentCreateRequest(**_MINIMAL)
        assert request.reference_number is None
        assert request.bank_name is None
        assert request.remarks is None

    @pytest.mark.parametrize("field", ["supplier_id", "payment_date", "payment_method", "amount"])
    def test_rejects_missing_required_field(self, field: str) -> None:
        payload = {k: v for k, v in _MINIMAL.items() if k != field}
        with pytest.raises(ValidationError):
            SupplierPaymentCreateRequest(**payload)

    def test_rejects_invalid_supplier_id(self) -> None:
        with pytest.raises(ValidationError):
            SupplierPaymentCreateRequest(**{**_MINIMAL, "supplier_id": "not-a-uuid"})

    def test_rejects_invalid_payment_method(self) -> None:
        with pytest.raises(ValidationError):
            SupplierPaymentCreateRequest(**{**_MINIMAL, "payment_method": "not-a-real-method"})

    def test_rejects_zero_amount(self) -> None:
        with pytest.raises(ValidationError):
            SupplierPaymentCreateRequest(**{**_MINIMAL, "amount": "0"})

    def test_rejects_negative_amount(self) -> None:
        with pytest.raises(ValidationError):
            SupplierPaymentCreateRequest(**{**_MINIMAL, "amount": "-1"})

    def test_accepts_small_positive_amount(self) -> None:
        request = SupplierPaymentCreateRequest(**{**_MINIMAL, "amount": "0.01"})
        assert request.amount == Decimal("0.01")

    def test_accepts_optional_fields(self) -> None:
        request = SupplierPaymentCreateRequest(
            **_MINIMAL,
            reference_number="778821",
            bank_name="State Bank",
            remarks="Against pending purchase bills",
        )
        assert request.reference_number == "778821"
        assert request.bank_name == "State Bank"
        assert request.remarks == "Against pending purchase bills"

    def test_does_not_accept_server_owned_fields(self) -> None:
        """payment_number/allocated_amount/unallocated_amount/status/
        posted_at must never be client-supplied - the server owns them
        entirely (SupplierPaymentService.create). Extra/unknown keys are
        simply ignored by pydantic's default config, not rejected, but they
        must not end up on the model."""
        request = SupplierPaymentCreateRequest(
            **_MINIMAL,
            payment_number="SPAY-0001",
            allocated_amount="50000.00",
            unallocated_amount="100000.00",
            status="posted",
            posted_at="2026-07-23T04:00:00Z",
        )
        assert not hasattr(request, "payment_number")
        assert not hasattr(request, "allocated_amount")
        assert not hasattr(request, "unallocated_amount")
        assert not hasattr(request, "status")
        assert not hasattr(request, "posted_at")


class TestSupplierPaymentUpdateRequest:
    def test_untouched_fields_are_excluded_from_dump(self) -> None:
        request = SupplierPaymentUpdateRequest(remarks="Revised")
        dumped = request.model_dump(exclude_unset=True)
        assert dumped == {"remarks": "Revised"}

    def test_all_fields_optional(self) -> None:
        request = SupplierPaymentUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_explicit_none_is_still_included(self) -> None:
        request = SupplierPaymentUpdateRequest(reference_number=None)
        dumped = request.model_dump(exclude_unset=True)
        assert "reference_number" in dumped
        assert dumped["reference_number"] is None

    def test_supplier_id_and_amount_can_be_reassigned(self) -> None:
        new_supplier_id = uuid.uuid4()
        request = SupplierPaymentUpdateRequest(supplier_id=new_supplier_id, amount="200000.00")
        assert request.model_dump(exclude_unset=True) == {
            "supplier_id": new_supplier_id,
            "amount": Decimal("200000.00"),
        }

    def test_rejects_invalid_supplier_id(self) -> None:
        with pytest.raises(ValidationError):
            SupplierPaymentUpdateRequest(supplier_id="not-a-uuid")

    def test_rejects_zero_amount(self) -> None:
        with pytest.raises(ValidationError):
            SupplierPaymentUpdateRequest(amount="0")

    def test_rejects_negative_amount(self) -> None:
        with pytest.raises(ValidationError):
            SupplierPaymentUpdateRequest(amount="-1")

    def test_does_not_accept_server_owned_fields(self) -> None:
        request = SupplierPaymentUpdateRequest(status="posted", payment_number="SPAY-0001")
        assert not hasattr(request, "status")
        assert not hasattr(request, "payment_number")


_SORTABLE_FIELDS = ("payment_date", "payment_number", "created_at")


class TestSupplierPaymentListParams:
    def test_defaults(self) -> None:
        params = SupplierPaymentListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort == "-created_at"
        assert params.q is None
        assert params.status is None
        assert params.supplier_id is None
        assert params.payment_method is None
        assert params.payment_date_from is None
        assert params.payment_date_to is None

    @pytest.mark.parametrize(
        "value",
        [f"{prefix}{field}" for field in _SORTABLE_FIELDS for prefix in ("", "-")],
    )
    def test_accepts_every_sortable_field_ascending_and_descending(self, value: str) -> None:
        params = SupplierPaymentListParams(sort=value)
        assert params.sort == value

    def test_rejects_unknown_sort_field(self) -> None:
        with pytest.raises(ValidationError):
            SupplierPaymentListParams(sort="unknown_field")

    def test_rejects_unsortable_field_even_with_dash(self) -> None:
        with pytest.raises(ValidationError):
            SupplierPaymentListParams(sort="-supplier_id")

    def test_rejects_amount_as_a_sort_field(self) -> None:
        """Unlike PaymentListParams, amount is not sortable here - TASKS.md
        Sprint 12 Session 2's SORT section lists only payment_date/
        payment_number/created_at."""
        with pytest.raises(ValidationError):
            SupplierPaymentListParams(sort="amount")

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            SupplierPaymentListParams(page=0)

    def test_rejects_page_size_above_cap(self) -> None:
        with pytest.raises(ValidationError):
            SupplierPaymentListParams(page_size=101)

    def test_rejects_page_size_below_one(self) -> None:
        with pytest.raises(ValidationError):
            SupplierPaymentListParams(page_size=0)

    def test_accepts_status_supplier_and_method_filters(self) -> None:
        supplier_id = uuid.uuid4()
        params = SupplierPaymentListParams(
            status="draft", supplier_id=supplier_id, payment_method="upi"
        )
        assert params.status == SupplierPaymentStatus.DRAFT
        assert params.supplier_id == supplier_id
        assert params.payment_method == PaymentMethod.UPI

    def test_rejects_invalid_status_filter(self) -> None:
        with pytest.raises(ValidationError):
            SupplierPaymentListParams(status="not-a-real-status")

    def test_accepts_payment_date_range_filters(self) -> None:
        params = SupplierPaymentListParams(
            payment_date_from="2026-07-01",
            payment_date_to="2026-07-31",
        )
        assert params.payment_date_from is not None
        assert params.payment_date_to is not None
        assert params.payment_date_from.isoformat() == "2026-07-01"
        assert params.payment_date_to.isoformat() == "2026-07-31"
