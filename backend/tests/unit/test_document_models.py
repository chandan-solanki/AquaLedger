from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from app.core.document_engine.document_models import (
    DocumentData,
    DocumentLine,
    DocumentParty,
    DocumentSection,
    DocumentTotals,
    RenderedDocument,
)
from app.core.document_engine.document_types import DocumentType

_NOW = datetime(2026, 8, 15, tzinfo=UTC)
_TODAY = date(2026, 8, 15)


def _make_data(**overrides: object) -> DocumentData:
    defaults: dict[str, object] = {
        "document_type": DocumentType.INVOICE,
        "document_number": "INV-000001",
        "document_date": _TODAY,
        "title": "Tax Invoice",
        "tenant_name": "Konkan Traders",
        "generated_at": _NOW,
        "generated_by": "admin@fisherp.test",
    }
    defaults.update(overrides)
    return DocumentData(**defaults)


class TestDocumentType:
    def test_known_document_type_values(self) -> None:
        assert DocumentType("invoice") is DocumentType.INVOICE
        assert DocumentType("delivery_challan") is DocumentType.DELIVERY_CHALLAN

    def test_unknown_document_type_rejected(self) -> None:
        with pytest.raises(ValueError):
            DocumentType("not_a_real_document")

    def test_all_six_types_are_defined(self) -> None:
        assert {member.value for member in DocumentType} == {
            "invoice",
            "purchase_bill",
            "customer_payment_receipt",
            "supplier_payment_receipt",
            "purchase_order",
            "delivery_challan",
        }


class TestDocumentParty:
    def test_only_name_is_required(self) -> None:
        party = DocumentParty(name="Konkan Seafoods")
        assert party.name == "Konkan Seafoods"
        assert party.id is None
        assert party.address is None
        assert party.tax_id is None

    def test_all_fields_round_trip(self) -> None:
        party = DocumentParty(
            id="co-1",
            name="Konkan Seafoods",
            code="CO-0001",
            address="Sassoon Dock, Mumbai",
            phone="9876543210",
            email="ops@konkanseafoods.test",
            tax_id="27ABCDE1234F1Z5",
        )
        assert party.code == "CO-0001"
        assert party.tax_id == "27ABCDE1234F1Z5"

    def test_is_frozen(self) -> None:
        party = DocumentParty(name="Konkan Seafoods")
        with pytest.raises(ValidationError):
            party.name = "Someone Else"  # type: ignore[misc]


class TestDocumentLine:
    def test_only_description_and_line_total_are_required(self) -> None:
        line = DocumentLine(description="Pomfret", line_total="1500.00")
        assert line.quantity is None
        assert line.metadata == {}

    def test_full_line_round_trips(self) -> None:
        line = DocumentLine(
            description="Pomfret",
            quantity="10.500",
            unit="KG",
            unit_price="150.00",
            tax_rate="5.00",
            tax_amount="78.75",
            line_total="1653.75",
            metadata={"fish_id": "f-1"},
        )
        assert line.metadata == {"fish_id": "f-1"}


class TestDocumentTotals:
    def test_only_subtotal_and_total_are_required(self) -> None:
        totals = DocumentTotals(subtotal="1500.00", total="1575.00")
        assert totals.discount == 0
        assert totals.tax == 0
        assert totals.rounding == 0
        assert totals.paid is None
        assert totals.balance is None


class TestDocumentSection:
    def test_defaults(self) -> None:
        section = DocumentSection()
        assert section.title is None
        assert section.lines == []
        assert section.metadata == {}

    def test_holds_its_own_lines(self) -> None:
        section = DocumentSection(
            title="Vehicle Details",
            lines=[DocumentLine(description="Truck No. MH-04-AB-1234", line_total="0")],
        )
        assert section.title == "Vehicle Details"
        assert len(section.lines) == 1


class TestDocumentData:
    def test_valid_construction(self) -> None:
        data = _make_data()
        assert data.document_type == DocumentType.INVOICE
        assert data.subtitle is None
        assert data.party is None
        assert data.sections == []
        assert data.line_items == []
        assert data.totals is None

    def test_optional_fields_round_trip(self) -> None:
        data = _make_data(
            subtitle="For Konkan Seafoods",
            tenant_details="GSTIN: 27AAAAA0000A1Z5",
            party=DocumentParty(name="Konkan Seafoods", code="CO-0001"),
            line_items=[DocumentLine(description="Pomfret", line_total="1500.00")],
            totals=DocumentTotals(subtotal="1500.00", total="1575.00"),
            notes="Thank you for your business.",
            terms="Payment due within 30 days.",
        )
        assert data.party is not None
        assert data.party.name == "Konkan Seafoods"
        assert data.totals is not None
        assert data.totals.total == 1575

    def test_rejects_blank_document_number(self) -> None:
        with pytest.raises(ValidationError, match="document_number"):
            _make_data(document_number="   ")

    def test_rejects_blank_title(self) -> None:
        with pytest.raises(ValidationError, match="title"):
            _make_data(title="")

    def test_rejects_blank_tenant_name(self) -> None:
        with pytest.raises(ValidationError, match="tenant_name"):
            _make_data(tenant_name=" ")

    def test_rejects_blank_generated_by(self) -> None:
        with pytest.raises(ValidationError, match="generated_by"):
            _make_data(generated_by="")

    def test_rejects_unknown_document_type(self) -> None:
        with pytest.raises(ValidationError):
            _make_data(document_type="not_a_real_document")

    def test_is_frozen(self) -> None:
        data = _make_data()
        with pytest.raises(ValidationError):
            data.title = "Something Else"  # type: ignore[misc]


class TestRenderedDocument:
    def test_construction(self) -> None:
        rendered = RenderedDocument(
            content=b"%PDF-1.4 fake", content_type="application/pdf", file_extension="pdf"
        )
        assert rendered.content == b"%PDF-1.4 fake"
        assert rendered.content_type == "application/pdf"
        assert rendered.file_extension == "pdf"

    def test_is_frozen(self) -> None:
        rendered = RenderedDocument(content=b"x", content_type="text/plain", file_extension="txt")
        with pytest.raises(ValidationError):
            rendered.content = b"y"  # type: ignore[misc]
