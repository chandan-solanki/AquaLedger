"""Unit tests for app.modules.supplier_payments.document_renderer
(Sprint 12 Session 4) - mirrors test_customer_payment_document_renderer.py's
own style. Assertions are deliberately structural (PDF signature, non-
empty output, page count for the multi-allocation case) rather than
pixel-level layout checks."""

import re
from datetime import UTC, date, datetime
from decimal import Decimal

from app.core.document_engine.document_models import (
    DocumentData,
    DocumentLine,
    DocumentParty,
    DocumentSection,
    DocumentTotals,
)
from app.core.document_engine.document_types import DocumentType
from app.core.document_engine.registry import registry
from app.modules.supplier_payments.document_renderer import SupplierPaymentReceiptRenderer

_NOW = datetime(2026, 8, 15, 10, 30, tzinfo=UTC)


def _make_data(**overrides: object) -> DocumentData:
    defaults: dict[str, object] = {
        "document_type": DocumentType.SUPPLIER_PAYMENT_RECEIPT,
        "document_number": "SPAY/2026-27/00001",
        "document_date": date(2026, 8, 15),
        "title": "Supplier Payment Receipt",
        "tenant_name": "Konkan Traders",
        "party": DocumentParty(name="Coastal Fish Suppliers", code="SUP-001"),
        "totals": DocumentTotals(
            subtotal=Decimal("150000.00"),
            total=Decimal("150000.00"),
            paid=Decimal("90000.00"),
            balance=Decimal("60000.00"),
        ),
        "metadata": {
            "payment_method": "cheque",
            "reference_number": "778821",
            "bank_name": "State Bank",
            "status": "posted",
        },
        "generated_at": _NOW,
        "generated_by": "admin@fisherp.test",
    }
    defaults.update(overrides)
    return DocumentData(**defaults)


class TestSupplierPaymentReceiptRenderer:
    def test_returns_pdf_bytes_with_a_valid_signature(self) -> None:
        renderer = SupplierPaymentReceiptRenderer()
        result = renderer.run(_make_data())
        assert result.content.startswith(b"%PDF-")
        assert len(result.content) > 0

    def test_content_type_and_extension(self) -> None:
        renderer = SupplierPaymentReceiptRenderer()
        result = renderer.run(_make_data())
        assert result.content_type == "application/pdf"
        assert result.file_extension == "pdf"

    def test_title_appears_in_the_rendered_pdf(self) -> None:
        renderer = SupplierPaymentReceiptRenderer()
        result = renderer.run(_make_data())
        assert b"SUPPLIER PAYMENT RECEIPT" in result.content

    def test_party_name_appears_in_the_rendered_pdf(self) -> None:
        renderer = SupplierPaymentReceiptRenderer()
        data = _make_data(party=DocumentParty(name="Konkan Seafoods Supply Co"))
        result = renderer.run(data)
        assert b"Konkan Seafoods Supply Co" in result.content

    def test_payment_number_appears_in_the_rendered_pdf_metadata(self) -> None:
        """The payment number is passed as the PDF's own /Title metadata
        (SimpleDocTemplate's `title=` kwarg) - checking for it there is
        a structural assertion, not a pixel-level layout check."""
        renderer = SupplierPaymentReceiptRenderer()
        result = renderer.run(_make_data(document_number="SPAY/2026-27/00099"))
        assert b"SPAY/2026-27/00099" in result.content

    def test_amount_appears_in_the_rendered_pdf(self) -> None:
        renderer = SupplierPaymentReceiptRenderer()
        data = _make_data(
            totals=DocumentTotals(subtotal=Decimal("321000.00"), total=Decimal("321000.00"))
        )
        result = renderer.run(data)
        assert b"321,000.00" in result.content

    def test_renders_with_no_optional_fields_present(self) -> None:
        renderer = SupplierPaymentReceiptRenderer()
        data = _make_data(party=None, totals=None, notes=None, sections=[], metadata={})
        result = renderer.run(data)
        assert result.content.startswith(b"%PDF-")

    def test_one_page_receipt_with_no_allocations(self) -> None:
        renderer = SupplierPaymentReceiptRenderer()
        result = renderer.run(_make_data())
        page_objects = re.findall(rb"/Type\s*/Page[^s]", result.content)
        assert len(page_objects) == 1

    def test_multi_page_allocation_receipt(self) -> None:
        many_allocations = [
            DocumentLine(description=f"PUR/2026-27/{i:05d}", line_total=Decimal("500.00"))
            for i in range(80)
        ]
        renderer = SupplierPaymentReceiptRenderer()
        data = _make_data(
            sections=[DocumentSection(title="Applied Payments", lines=many_allocations)]
        )
        result = renderer.run(data)
        page_objects = re.findall(rb"/Type\s*/Page[^s]", result.content)
        assert len(page_objects) > 1

    def test_allocation_section_renders_purchase_bill_numbers(self) -> None:
        renderer = SupplierPaymentReceiptRenderer()
        data = _make_data(
            sections=[
                DocumentSection(
                    title="Applied Payments",
                    lines=[
                        DocumentLine(
                            description="PUR/2026-27/00001", line_total=Decimal("90000.00")
                        )
                    ],
                )
            ]
        )
        result = renderer.run(data)
        assert b"PUR/2026-27/00001" in result.content

    def test_footer_generated_by_appears_on_every_page(self) -> None:
        renderer = SupplierPaymentReceiptRenderer()
        result = renderer.run(_make_data(generated_by="Ravi Kumar"))
        assert result.content.count(b"Ravi Kumar") >= 1
        assert b"system generated document" in result.content

    def test_default_content_type_class_attributes(self) -> None:
        assert SupplierPaymentReceiptRenderer.content_type == "application/pdf"
        assert SupplierPaymentReceiptRenderer.file_extension == "pdf"


class TestDocumentRegistryRegistration:
    def test_supplier_payment_receipt_type_is_registered(self) -> None:
        assert registry.get(DocumentType.SUPPLIER_PAYMENT_RECEIPT) is SupplierPaymentReceiptRenderer

    def test_supplier_payment_receipt_is_registered_true(self) -> None:
        assert registry.is_registered(DocumentType.SUPPLIER_PAYMENT_RECEIPT) is True
