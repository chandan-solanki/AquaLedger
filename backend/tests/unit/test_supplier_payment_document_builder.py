"""Unit tests for app.modules.supplier_payments.document_builder
(Sprint 12 Session 4) - pure DTO -> DocumentData mapping. No database,
no HTTP - every SupplierPaymentResponse/SupplierResponse/
SupplierPaymentAllocationDisplay below is hand-built, mirroring
test_customer_payment_document_builder.py's own style."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.core.document_engine.document_types import DocumentType
from app.modules.supplier_payments.constants import PaymentMethod, SupplierPaymentStatus
from app.modules.supplier_payments.document_builder import (
    build_supplier_payment_receipt_document_data,
)
from app.modules.supplier_payments.schemas import SupplierPaymentResponse
from app.modules.supplier_payments.service import SupplierPaymentAllocationDisplay
from app.modules.suppliers.constants import SupplierStatus
from app.modules.suppliers.schemas import SupplierResponse

_TENANT_ID = uuid.uuid4()
_SUPPLIER_ID = uuid.uuid4()
_PAYMENT_ID = uuid.uuid4()
_NOW = datetime(2026, 8, 15, 10, 30, tzinfo=UTC)


def _make_payment(**overrides: object) -> SupplierPaymentResponse:
    defaults: dict[str, object] = {
        "id": _PAYMENT_ID,
        "tenant_id": _TENANT_ID,
        "supplier_id": _SUPPLIER_ID,
        "payment_number": "SPAY/2026-27/00001",
        "payment_date": date(2026, 8, 15),
        "payment_method": PaymentMethod.CHEQUE,
        "reference_number": "778821",
        "bank_name": "State Bank",
        "amount": Decimal("150000.00"),
        "allocated_amount": Decimal("90000.00"),
        "unallocated_amount": Decimal("60000.00"),
        "remarks": "Against pending purchase bills",
        "status": SupplierPaymentStatus.POSTED,
        "posted_at": _NOW,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    defaults.update(overrides)
    return SupplierPaymentResponse(**defaults)


def _make_supplier(**overrides: object) -> SupplierResponse:
    defaults: dict[str, object] = {
        "id": _SUPPLIER_ID,
        "tenant_id": _TENANT_ID,
        "code": "SUP-001",
        "name": "Coastal Fish Suppliers",
        "legal_name": "Coastal Fish Suppliers Pvt Ltd",
        "gstin": "27ABCDE1234F1Z5",
        "phone": "9876543210",
        "email": "contact@coastalfish.example",
        "address": "12 Harbour Road",
        "city": "Mumbai",
        "state": "Maharashtra",
        "country": "India",
        "contact_person": "Ravi Kumar",
        "credit_days": 30,
        "opening_balance": Decimal("0.00"),
        "outstanding_amount": Decimal("0.00"),
        "status": SupplierStatus.ACTIVE,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    defaults.update(overrides)
    return SupplierResponse(**defaults)


class TestBuildSupplierPaymentReceiptDocumentData:
    def test_document_type_is_supplier_payment_receipt(self) -> None:
        data = build_supplier_payment_receipt_document_data(
            _make_payment(),
            _make_supplier(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.document_type == DocumentType.SUPPLIER_PAYMENT_RECEIPT

    def test_title_is_supplier_payment_receipt(self) -> None:
        data = build_supplier_payment_receipt_document_data(
            _make_payment(),
            _make_supplier(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.title == "Supplier Payment Receipt"

    def test_document_number_is_the_actual_payment_number(self) -> None:
        data = build_supplier_payment_receipt_document_data(
            _make_payment(payment_number="SPAY/2026-27/00042"),
            _make_supplier(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.document_number == "SPAY/2026-27/00042"

    def test_document_date_is_the_actual_payment_date(self) -> None:
        data = build_supplier_payment_receipt_document_data(
            _make_payment(payment_date=date(2026, 1, 5)),
            _make_supplier(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.document_date == date(2026, 1, 5)

    def test_supplier_mapping(self) -> None:
        data = build_supplier_payment_receipt_document_data(
            _make_payment(),
            _make_supplier(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.party is not None
        assert data.party.name == "Coastal Fish Suppliers"
        assert data.party.code == "SUP-001"
        assert data.party.phone == "9876543210"
        assert data.party.email == "contact@coastalfish.example"
        assert data.party.tax_id == "27ABCDE1234F1Z5"
        assert data.party.address == "12 Harbour Road, Mumbai, Maharashtra, India"

    def test_supplier_optional_fields_omitted_when_unavailable(self) -> None:
        supplier = _make_supplier(
            phone=None, email=None, gstin=None, address=None, city=None, state=None, country=None
        )
        data = build_supplier_payment_receipt_document_data(
            _make_payment(),
            supplier,
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.party is not None
        assert data.party.phone is None
        assert data.party.email is None
        assert data.party.tax_id is None
        assert data.party.address is None

    def test_amount_mapping_uses_authoritative_backend_amount(self) -> None:
        data = build_supplier_payment_receipt_document_data(
            _make_payment(amount=Decimal("175000.50")),
            _make_supplier(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.totals is not None
        assert data.totals.subtotal == Decimal("175000.50")
        assert data.totals.total == Decimal("175000.50")

    def test_allocated_and_unallocated_map_to_paid_and_balance(self) -> None:
        data = build_supplier_payment_receipt_document_data(
            _make_payment(
                allocated_amount=Decimal("90000.00"), unallocated_amount=Decimal("60000.00")
            ),
            _make_supplier(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.totals is not None
        assert data.totals.paid == Decimal("90000.00")
        assert data.totals.balance == Decimal("60000.00")

    def test_payment_method_is_carried_in_metadata(self) -> None:
        data = build_supplier_payment_receipt_document_data(
            _make_payment(payment_method=PaymentMethod.BANK_TRANSFER),
            _make_supplier(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.metadata["payment_method"] == "bank_transfer"

    def test_reference_number_is_carried_in_metadata_when_present(self) -> None:
        data = build_supplier_payment_receipt_document_data(
            _make_payment(reference_number="778821"),
            _make_supplier(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.metadata["reference_number"] == "778821"

    def test_reference_number_omitted_from_metadata_when_absent(self) -> None:
        data = build_supplier_payment_receipt_document_data(
            _make_payment(reference_number=None),
            _make_supplier(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert "reference_number" not in data.metadata

    def test_bank_name_is_carried_in_metadata_when_present(self) -> None:
        data = build_supplier_payment_receipt_document_data(
            _make_payment(bank_name="State Bank"),
            _make_supplier(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.metadata["bank_name"] == "State Bank"

    def test_bank_name_omitted_from_metadata_when_absent(self) -> None:
        data = build_supplier_payment_receipt_document_data(
            _make_payment(bank_name=None),
            _make_supplier(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert "bank_name" not in data.metadata

    def test_status_is_carried_in_metadata(self) -> None:
        data = build_supplier_payment_receipt_document_data(
            _make_payment(status=SupplierPaymentStatus.POSTED),
            _make_supplier(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.metadata["status"] == "posted"

    def test_remarks_maps_to_notes_when_present(self) -> None:
        data = build_supplier_payment_receipt_document_data(
            _make_payment(remarks="Against pending purchase bills"),
            _make_supplier(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.notes == "Against pending purchase bills"

    def test_notes_omitted_when_no_remarks(self) -> None:
        data = build_supplier_payment_receipt_document_data(
            _make_payment(remarks=None),
            _make_supplier(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.notes is None

    def test_zero_allocations_omits_the_allocations_section(self) -> None:
        data = build_supplier_payment_receipt_document_data(
            _make_payment(),
            _make_supplier(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.sections == []

    def test_single_allocation_maps_into_a_section(self) -> None:
        allocations = [
            SupplierPaymentAllocationDisplay(
                purchase_bill_number="PUR/2026-27/00001", allocated_amount=Decimal("90000.00")
            )
        ]
        data = build_supplier_payment_receipt_document_data(
            _make_payment(),
            _make_supplier(),
            allocations,
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert len(data.sections) == 1
        section = data.sections[0]
        assert section.title == "Applied Payments"
        assert len(section.lines) == 1
        assert section.lines[0].description == "PUR/2026-27/00001"
        assert section.lines[0].line_total == Decimal("90000.00")

    def test_multiple_allocations_map_in_order(self) -> None:
        allocations = [
            SupplierPaymentAllocationDisplay(
                purchase_bill_number="PUR/2026-27/00001", allocated_amount=Decimal("5000.00")
            ),
            SupplierPaymentAllocationDisplay(
                purchase_bill_number="PUR/2026-27/00002", allocated_amount=Decimal("2000.00")
            ),
        ]
        data = build_supplier_payment_receipt_document_data(
            _make_payment(),
            _make_supplier(),
            allocations,
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert len(data.sections) == 1
        lines = data.sections[0].lines
        assert len(lines) == 2
        assert lines[0].description == "PUR/2026-27/00001"
        assert lines[0].line_total == Decimal("5000.00")
        assert lines[1].description == "PUR/2026-27/00002"
        assert lines[1].line_total == Decimal("2000.00")

    def test_no_calculation_inside_builder(self) -> None:
        """Passing internally-inconsistent totals must round-trip
        unchanged - the builder must never recompute allocated/
        unallocated/amount from the allocations, only copy whatever the
        backend already computed."""
        payment = _make_payment(
            amount=Decimal("999.99"),
            allocated_amount=Decimal("1.00"),
            unallocated_amount=Decimal("998.99"),
        )
        allocations = [
            SupplierPaymentAllocationDisplay(
                purchase_bill_number="PUR/2026-27/00001", allocated_amount=Decimal("500000.00")
            )
        ]
        data = build_supplier_payment_receipt_document_data(
            payment,
            _make_supplier(),
            allocations,
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.totals is not None
        assert data.totals.total == Decimal("999.99")
        assert data.totals.paid == Decimal("1.00")
        assert data.totals.balance == Decimal("998.99")
        assert data.sections[0].lines[0].line_total == Decimal("500000.00")

    def test_tenant_name_and_generated_by_are_passed_through(self) -> None:
        data = build_supplier_payment_receipt_document_data(
            _make_payment(),
            _make_supplier(),
            [],
            tenant_name="Konkan Traders",
            generated_by="Ravi Kumar",
        )
        assert data.tenant_name == "Konkan Traders"
        assert data.generated_by == "Ravi Kumar"

    def test_tenant_details_is_never_set_since_tenant_has_no_address_fields(self) -> None:
        data = build_supplier_payment_receipt_document_data(
            _make_payment(),
            _make_supplier(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.tenant_details is None

    def test_raises_when_payment_number_is_missing(self) -> None:
        with pytest.raises(ValueError, match="payment_number"):
            build_supplier_payment_receipt_document_data(
                _make_payment(payment_number=None),
                _make_supplier(),
                [],
                tenant_name="Konkan Traders",
                generated_by="admin@fisherp.test",
            )
