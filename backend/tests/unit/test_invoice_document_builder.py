"""Unit tests for app.modules.invoices.document_builder (Sprint 12
Session 2) - pure DTO -> DocumentData mapping. No database, no HTTP -
every InvoiceResponse/InvoiceItemResponse/CompanyResponse/FishResponse
below is hand-built, the same way test_report_export_models.py's own
`_make_data()` helper hand-builds its DTOs."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.core.document_engine.document_types import DocumentType
from app.modules.companies.constants import CompanyStatus, CompanyType
from app.modules.companies.schemas import CompanyResponse
from app.modules.fish.constants import FishUnit
from app.modules.fish.schemas import FishResponse
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.document_builder import build_invoice_document_data
from app.modules.invoices.schemas import InvoiceItemResponse, InvoiceResponse

_TENANT_ID = uuid.uuid4()
_COMPANY_ID = uuid.uuid4()
_INVOICE_ID = uuid.uuid4()
_FISH_ID_A = uuid.uuid4()
_FISH_ID_B = uuid.uuid4()
_NOW = datetime(2026, 8, 15, 10, 30, tzinfo=UTC)


def _make_invoice(**overrides: object) -> InvoiceResponse:
    defaults: dict[str, object] = {
        "id": _INVOICE_ID,
        "tenant_id": _TENANT_ID,
        "company_id": _COMPANY_ID,
        "invoice_number": "INV/2026-27/00001",
        "invoice_date": date(2026, 8, 15),
        "due_date": date(2026, 8, 30),
        "status": InvoiceStatus.ISSUED,
        "subtotal": Decimal("22500.00"),
        "discount_amount": Decimal("0.00"),
        "taxable_amount": Decimal("22500.00"),
        "tax_amount": Decimal("1125.00"),
        "transport_charge": Decimal("0.00"),
        "other_charge": Decimal("0.00"),
        "round_off": Decimal("0.00"),
        "total_amount": Decimal("23625.00"),
        "paid_amount": Decimal("0.00"),
        "balance_amount": Decimal("23625.00"),
        "remarks": None,
        "issued_at": _NOW,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    defaults.update(overrides)
    return InvoiceResponse(**defaults)


def _make_item(**overrides: object) -> InvoiceItemResponse:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "tenant_id": _TENANT_ID,
        "invoice_id": _INVOICE_ID,
        "line_number": 1,
        "fish_id": _FISH_ID_A,
        "trip_catch_id": uuid.uuid4(),
        "description": None,
        "quantity": Decimal("50.000"),
        "unit": "kg",
        "rate": Decimal("450.0000"),
        "discount_percent": Decimal("0.00"),
        "discount_amount": Decimal("0.00"),
        "taxable_amount": Decimal("22500.00"),
        "tax_rate": Decimal("5.00"),
        "tax_amount": Decimal("1125.00"),
        "line_total": Decimal("23625.00"),
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    defaults.update(overrides)
    return InvoiceItemResponse(**defaults)


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


def _make_fish(fish_id: uuid.UUID, name: str, **overrides: object) -> FishResponse:
    defaults: dict[str, object] = {
        "id": fish_id,
        "tenant_id": _TENANT_ID,
        "code": "FISH-001",
        "name": name,
        "local_name": "Paplet",
        "scientific_name": "Pampus argenteus",
        "category": "Whitefish",
        "unit": FishUnit.KG,
        "default_purchase_rate": Decimal("450.0000"),
        "default_sale_rate": Decimal("550.0000"),
        "hsn_code": "0302",
        "description": None,
        "is_active": True,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    defaults.update(overrides)
    return FishResponse(**defaults)


class TestBuildInvoiceDocumentData:
    def test_document_type_is_invoice(self) -> None:
        data = build_invoice_document_data(
            _make_invoice(),
            [_make_item()],
            _make_company(),
            {_FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret")},
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.document_type == DocumentType.INVOICE

    def test_document_number_is_the_actual_invoice_number(self) -> None:
        data = build_invoice_document_data(
            _make_invoice(invoice_number="INV/2026-27/00042"),
            [_make_item()],
            _make_company(),
            {_FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret")},
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.document_number == "INV/2026-27/00042"

    def test_document_date_is_the_actual_invoice_date(self) -> None:
        data = build_invoice_document_data(
            _make_invoice(invoice_date=date(2026, 1, 5)),
            [_make_item()],
            _make_company(),
            {_FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret")},
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.document_date == date(2026, 1, 5)

    def test_customer_mapping(self) -> None:
        data = build_invoice_document_data(
            _make_invoice(),
            [_make_item()],
            _make_company(),
            {_FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret")},
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
        data = build_invoice_document_data(
            _make_invoice(),
            [_make_item()],
            company,
            {_FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret")},
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.party is not None
        assert data.party.phone is None
        assert data.party.email is None
        assert data.party.tax_id is None
        assert data.party.address is None

    def test_single_line_item_mapping(self) -> None:
        item = _make_item(
            quantity=Decimal("50.000"),
            unit="kg",
            rate=Decimal("450.0000"),
            tax_rate=Decimal("5.00"),
            tax_amount=Decimal("1125.00"),
            line_total=Decimal("23625.00"),
        )
        data = build_invoice_document_data(
            _make_invoice(),
            [item],
            _make_company(),
            {_FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret")},
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert len(data.line_items) == 1
        line = data.line_items[0]
        assert line.description == "Pomfret"
        assert line.quantity == Decimal("50.000")
        assert line.unit == "kg"
        assert line.unit_price == Decimal("450.0000")
        assert line.tax_amount == Decimal("1125.00")
        assert line.line_total == Decimal("23625.00")

    def test_line_item_description_combines_fish_name_and_free_text(self) -> None:
        item = _make_item(description="Grade A")
        data = build_invoice_document_data(
            _make_invoice(),
            [item],
            _make_company(),
            {_FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret")},
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.line_items[0].description == "Pomfret - Grade A"

    def test_multi_line_item_mapping_preserves_order(self) -> None:
        item_a = _make_item(line_number=1, fish_id=_FISH_ID_A, line_total=Decimal("100.00"))
        item_b = _make_item(line_number=2, fish_id=_FISH_ID_B, line_total=Decimal("200.00"))
        data = build_invoice_document_data(
            _make_invoice(),
            [item_a, item_b],
            _make_company(),
            {
                _FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret"),
                _FISH_ID_B: _make_fish(_FISH_ID_B, "Surmai"),
            },
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert len(data.line_items) == 2
        assert data.line_items[0].description == "Pomfret"
        assert data.line_items[0].line_total == Decimal("100.00")
        assert data.line_items[1].description == "Surmai"
        assert data.line_items[1].line_total == Decimal("200.00")

    def test_totals_mapping_uses_authoritative_backend_values(self) -> None:
        invoice = _make_invoice(
            subtotal=Decimal("22500.00"),
            discount_amount=Decimal("500.00"),
            tax_amount=Decimal("1100.00"),
            round_off=Decimal("0.25"),
            total_amount=Decimal("23100.25"),
            paid_amount=Decimal("10000.00"),
            balance_amount=Decimal("13100.25"),
        )
        data = build_invoice_document_data(
            invoice,
            [_make_item()],
            _make_company(),
            {_FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret")},
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.totals is not None
        assert data.totals.subtotal == Decimal("22500.00")
        assert data.totals.discount == Decimal("500.00")
        assert data.totals.tax == Decimal("1100.00")
        assert data.totals.rounding == Decimal("0.25")
        assert data.totals.total == Decimal("23100.25")
        assert data.totals.paid == Decimal("10000.00")
        assert data.totals.balance == Decimal("13100.25")

    def test_no_calculation_inside_builder(self) -> None:
        """Passing internally-inconsistent totals must round-trip
        unchanged - the builder must never recompute subtotal/tax/total
        from the line items, only copy whatever the backend already
        computed."""
        invoice = _make_invoice(
            subtotal=Decimal("999.99"),
            tax_amount=Decimal("111.11"),
            total_amount=Decimal("500.00"),
        )
        item = _make_item(line_total=Decimal("23625.00"))
        data = build_invoice_document_data(
            invoice,
            [item],
            _make_company(),
            {_FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret")},
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.totals is not None
        assert data.totals.subtotal == Decimal("999.99")
        assert data.totals.total == Decimal("500.00")
        assert data.line_items[0].line_total == Decimal("23625.00")

    def test_additional_charges_section_present_when_nonzero(self) -> None:
        invoice = _make_invoice(transport_charge=Decimal("250.00"), other_charge=Decimal("50.00"))
        data = build_invoice_document_data(
            invoice,
            [_make_item()],
            _make_company(),
            {_FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret")},
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert len(data.sections) == 1
        section = data.sections[0]
        assert section.title == "Additional Charges"
        descriptions = {line.description: line.line_total for line in section.lines}
        assert descriptions == {
            "Transport Charge": Decimal("250.00"),
            "Other Charge": Decimal("50.00"),
        }

    def test_additional_charges_section_omitted_when_zero(self) -> None:
        invoice = _make_invoice(transport_charge=Decimal("0.00"), other_charge=Decimal("0.00"))
        data = build_invoice_document_data(
            invoice,
            [_make_item()],
            _make_company(),
            {_FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret")},
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.sections == []

    def test_notes_maps_from_remarks_when_present(self) -> None:
        data = build_invoice_document_data(
            _make_invoice(remarks="Weekly settlement"),
            [_make_item()],
            _make_company(),
            {_FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret")},
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.notes == "Weekly settlement"

    def test_notes_omitted_when_no_remarks(self) -> None:
        data = build_invoice_document_data(
            _make_invoice(remarks=None),
            [_make_item()],
            _make_company(),
            {_FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret")},
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.notes is None

    def test_terms_are_never_set_since_invoice_model_has_no_terms_field(self) -> None:
        data = build_invoice_document_data(
            _make_invoice(),
            [_make_item()],
            _make_company(),
            {_FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret")},
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.terms is None

    def test_tenant_name_and_generated_by_are_passed_through(self) -> None:
        data = build_invoice_document_data(
            _make_invoice(),
            [_make_item()],
            _make_company(),
            {_FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret")},
            tenant_name="Konkan Traders",
            generated_by="Ravi Kumar",
        )
        assert data.tenant_name == "Konkan Traders"
        assert data.generated_by == "Ravi Kumar"

    def test_tenant_details_is_never_set_since_tenant_has_no_address_fields(self) -> None:
        data = build_invoice_document_data(
            _make_invoice(),
            [_make_item()],
            _make_company(),
            {_FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret")},
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.tenant_details is None

    def test_status_is_carried_in_metadata(self) -> None:
        data = build_invoice_document_data(
            _make_invoice(status=InvoiceStatus.PARTIALLY_PAID),
            [_make_item()],
            _make_company(),
            {_FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret")},
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.metadata["status"] == "partially_paid"

    def test_raises_when_invoice_number_is_missing(self) -> None:
        with pytest.raises(ValueError, match="invoice_number"):
            build_invoice_document_data(
                _make_invoice(invoice_number=None),
                [_make_item()],
                _make_company(),
                {_FISH_ID_A: _make_fish(_FISH_ID_A, "Pomfret")},
                tenant_name="Konkan Traders",
                generated_by="admin@fisherp.test",
            )
