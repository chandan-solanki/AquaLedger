"""Unit tests for app.modules.payments.document_builder (Sprint 12
Session 4) - pure DTO -> DocumentData mapping. No database, no HTTP -
every PaymentResponse/CompanyResponse/PaymentAllocationDisplay below is
hand-built, mirroring test_invoice_document_builder.py's own style."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.core.document_engine.document_types import DocumentType
from app.modules.companies.constants import CompanyStatus, CompanyType
from app.modules.companies.schemas import CompanyResponse
from app.modules.payments.constants import PaymentMethod, PaymentStatus
from app.modules.payments.document_builder import build_customer_payment_receipt_document_data
from app.modules.payments.schemas import PaymentResponse
from app.modules.payments.service import PaymentAllocationDisplay

_TENANT_ID = uuid.uuid4()
_COMPANY_ID = uuid.uuid4()
_PAYMENT_ID = uuid.uuid4()
_NOW = datetime(2026, 8, 15, 10, 30, tzinfo=UTC)


def _make_payment(**overrides: object) -> PaymentResponse:
    defaults: dict[str, object] = {
        "id": _PAYMENT_ID,
        "tenant_id": _TENANT_ID,
        "company_id": _COMPANY_ID,
        "payment_number": "PAY/2026-27/00001",
        "payment_date": date(2026, 8, 15),
        "payment_method": PaymentMethod.CHEQUE,
        "reference_number": "445512",
        "bank_name": "State Bank",
        "amount": Decimal("200000.00"),
        "allocated_amount": Decimal("120000.00"),
        "unallocated_amount": Decimal("80000.00"),
        "remarks": "Against pending invoices",
        "status": PaymentStatus.POSTED,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    defaults.update(overrides)
    return PaymentResponse(**defaults)


def _make_company(**overrides: object) -> CompanyResponse:
    defaults: dict[str, object] = {
        "id": _COMPANY_ID,
        "tenant_id": _TENANT_ID,
        "code": "CUST-001",
        "name": "Ocean Fresh Traders",
        "legal_name": "Ocean Fresh Traders Pvt Ltd",
        "gstin": "27ABCDE1234F1Z5",
        "pan": "ABCDE1234F",
        "address_line1": "12 Harbour Road",
        "address_line2": None,
        "city": "Mumbai",
        "state": "Maharashtra",
        "state_code": "27",
        "pincode": "400001",
        "country": "India",
        "phone": "9876543210",
        "alt_phone": None,
        "email": "contact@oceanfresh.example",
        "contact_person": "Ravi Kumar",
        "company_type": CompanyType.CUSTOMER,
        "credit_limit": Decimal("500000.00"),
        "credit_days": 30,
        "opening_balance": Decimal("0.00"),
        "opening_balance_date": None,
        "opening_balance_type": None,
        "outstanding_amount": Decimal("0.00"),
        "status": CompanyStatus.ACTIVE,
        "notes": None,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    defaults.update(overrides)
    return CompanyResponse(**defaults)


class TestBuildCustomerPaymentReceiptDocumentData:
    def test_document_type_is_customer_payment_receipt(self) -> None:
        data = build_customer_payment_receipt_document_data(
            _make_payment(),
            _make_company(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.document_type == DocumentType.CUSTOMER_PAYMENT_RECEIPT

    def test_title_is_customer_payment_receipt(self) -> None:
        data = build_customer_payment_receipt_document_data(
            _make_payment(),
            _make_company(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.title == "Customer Payment Receipt"

    def test_document_number_is_the_actual_payment_number(self) -> None:
        data = build_customer_payment_receipt_document_data(
            _make_payment(payment_number="PAY/2026-27/00042"),
            _make_company(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.document_number == "PAY/2026-27/00042"

    def test_document_date_is_the_actual_payment_date(self) -> None:
        data = build_customer_payment_receipt_document_data(
            _make_payment(payment_date=date(2026, 1, 5)),
            _make_company(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.document_date == date(2026, 1, 5)

    def test_customer_mapping(self) -> None:
        data = build_customer_payment_receipt_document_data(
            _make_payment(),
            _make_company(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.party is not None
        assert data.party.name == "Ocean Fresh Traders"
        assert data.party.code == "CUST-001"
        assert data.party.phone == "9876543210"
        assert data.party.email == "contact@oceanfresh.example"
        assert data.party.tax_id == "27ABCDE1234F1Z5"
        assert data.party.address == "12 Harbour Road, Mumbai, Maharashtra 400001, India"

    def test_customer_optional_fields_omitted_when_unavailable(self) -> None:
        company = _make_company(
            phone=None,
            email=None,
            gstin=None,
            address_line1=None,
            address_line2=None,
            city=None,
            state=None,
            pincode=None,
            country=None,
        )
        data = build_customer_payment_receipt_document_data(
            _make_payment(),
            company,
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
        data = build_customer_payment_receipt_document_data(
            _make_payment(amount=Decimal("350000.50")),
            _make_company(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.totals is not None
        assert data.totals.subtotal == Decimal("350000.50")
        assert data.totals.total == Decimal("350000.50")

    def test_allocated_and_unallocated_map_to_paid_and_balance(self) -> None:
        data = build_customer_payment_receipt_document_data(
            _make_payment(
                allocated_amount=Decimal("120000.00"), unallocated_amount=Decimal("80000.00")
            ),
            _make_company(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.totals is not None
        assert data.totals.paid == Decimal("120000.00")
        assert data.totals.balance == Decimal("80000.00")

    def test_payment_method_is_carried_in_metadata(self) -> None:
        data = build_customer_payment_receipt_document_data(
            _make_payment(payment_method=PaymentMethod.BANK_TRANSFER),
            _make_company(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.metadata["payment_method"] == "bank_transfer"

    def test_reference_number_is_carried_in_metadata_when_present(self) -> None:
        data = build_customer_payment_receipt_document_data(
            _make_payment(reference_number="445512"),
            _make_company(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.metadata["reference_number"] == "445512"

    def test_reference_number_omitted_from_metadata_when_absent(self) -> None:
        data = build_customer_payment_receipt_document_data(
            _make_payment(reference_number=None),
            _make_company(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert "reference_number" not in data.metadata

    def test_bank_name_is_carried_in_metadata_when_present(self) -> None:
        data = build_customer_payment_receipt_document_data(
            _make_payment(bank_name="State Bank"),
            _make_company(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.metadata["bank_name"] == "State Bank"

    def test_bank_name_omitted_from_metadata_when_absent(self) -> None:
        data = build_customer_payment_receipt_document_data(
            _make_payment(bank_name=None),
            _make_company(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert "bank_name" not in data.metadata

    def test_status_is_carried_in_metadata(self) -> None:
        data = build_customer_payment_receipt_document_data(
            _make_payment(status=PaymentStatus.POSTED),
            _make_company(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.metadata["status"] == "posted"

    def test_remarks_maps_to_notes_when_present(self) -> None:
        data = build_customer_payment_receipt_document_data(
            _make_payment(remarks="Against pending invoices"),
            _make_company(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.notes == "Against pending invoices"

    def test_notes_omitted_when_no_remarks(self) -> None:
        data = build_customer_payment_receipt_document_data(
            _make_payment(remarks=None),
            _make_company(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.notes is None

    def test_zero_allocations_omits_the_allocations_section(self) -> None:
        data = build_customer_payment_receipt_document_data(
            _make_payment(),
            _make_company(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.sections == []

    def test_single_allocation_maps_into_a_section(self) -> None:
        allocations = [
            PaymentAllocationDisplay(
                invoice_number="INV/2026-27/00001", allocated_amount=Decimal("120000.00")
            )
        ]
        data = build_customer_payment_receipt_document_data(
            _make_payment(),
            _make_company(),
            allocations,
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert len(data.sections) == 1
        section = data.sections[0]
        assert section.title == "Applied Payments"
        assert len(section.lines) == 1
        assert section.lines[0].description == "INV/2026-27/00001"
        assert section.lines[0].line_total == Decimal("120000.00")

    def test_multiple_allocations_map_in_order(self) -> None:
        allocations = [
            PaymentAllocationDisplay(
                invoice_number="INV/2026-27/00001", allocated_amount=Decimal("5000.00")
            ),
            PaymentAllocationDisplay(
                invoice_number="INV/2026-27/00002", allocated_amount=Decimal("2000.00")
            ),
        ]
        data = build_customer_payment_receipt_document_data(
            _make_payment(),
            _make_company(),
            allocations,
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert len(data.sections) == 1
        lines = data.sections[0].lines
        assert len(lines) == 2
        assert lines[0].description == "INV/2026-27/00001"
        assert lines[0].line_total == Decimal("5000.00")
        assert lines[1].description == "INV/2026-27/00002"
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
            PaymentAllocationDisplay(
                invoice_number="INV/2026-27/00001", allocated_amount=Decimal("500000.00")
            )
        ]
        data = build_customer_payment_receipt_document_data(
            payment,
            _make_company(),
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
        data = build_customer_payment_receipt_document_data(
            _make_payment(),
            _make_company(),
            [],
            tenant_name="Konkan Traders",
            generated_by="Ravi Kumar",
        )
        assert data.tenant_name == "Konkan Traders"
        assert data.generated_by == "Ravi Kumar"

    def test_tenant_details_is_never_set_since_tenant_has_no_address_fields(self) -> None:
        data = build_customer_payment_receipt_document_data(
            _make_payment(),
            _make_company(),
            [],
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.tenant_details is None

    def test_raises_when_payment_number_is_missing(self) -> None:
        with pytest.raises(ValueError, match="payment_number"):
            build_customer_payment_receipt_document_data(
                _make_payment(payment_number=None),
                _make_company(),
                [],
                tenant_name="Konkan Traders",
                generated_by="admin@fisherp.test",
            )
