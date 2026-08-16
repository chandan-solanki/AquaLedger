"""Unit tests for app.modules.purchase.document_renderer (Sprint 12
Session 3) - mirrors test_invoice_document_renderer.py's own style.
Assertions are deliberately structural (PDF signature, non-empty
output, page count for the multi-page case) rather than pixel-level
layout checks, per this session's own testing guidance."""

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
from app.modules.purchase.document_renderer import PurchaseBillDocumentRenderer

_NOW = datetime(2026, 8, 15, 10, 30, tzinfo=UTC)


def _make_data(**overrides: object) -> DocumentData:
    defaults: dict[str, object] = {
        "document_type": DocumentType.PURCHASE_BILL,
        "document_number": "PUR/2026-27/00001",
        "document_date": date(2026, 8, 15),
        "title": "Purchase Bill",
        "tenant_name": "Konkan Traders",
        "line_items": [
            DocumentLine(
                description="Pomfret",
                quantity=Decimal("50.000"),
                unit="KG",
                unit_price=Decimal("450.0000"),
                tax_rate=Decimal("5.00"),
                tax_amount=Decimal("1125.00"),
                line_total=Decimal("23625.00"),
            )
        ],
        "generated_at": _NOW,
        "generated_by": "admin@fisherp.test",
    }
    defaults.update(overrides)
    return DocumentData(**defaults)


class TestPurchaseBillDocumentRenderer:
    def test_returns_pdf_bytes_with_a_valid_signature(self) -> None:
        renderer = PurchaseBillDocumentRenderer()
        result = renderer.run(_make_data())
        assert result.content.startswith(b"%PDF-")
        assert len(result.content) > 0

    def test_content_type_and_extension(self) -> None:
        renderer = PurchaseBillDocumentRenderer()
        result = renderer.run(_make_data())
        assert result.content_type == "application/pdf"
        assert result.file_extension == "pdf"

    def test_renders_with_no_optional_fields_present(self) -> None:
        renderer = PurchaseBillDocumentRenderer()
        data = _make_data(party=None, totals=None, notes=None, sections=[])
        result = renderer.run(data)
        assert result.content.startswith(b"%PDF-")

    def test_renders_with_full_data_including_party_totals_and_sections(self) -> None:
        renderer = PurchaseBillDocumentRenderer()
        data = _make_data(
            party=DocumentParty(
                name="Coastal Fish Suppliers",
                code="SUP-001",
                address="12 Harbour Road, Mumbai, Maharashtra, India",
                phone="9876543210",
                email="contact@coastalfish.example",
                tax_id="27ABCDE1234F1Z5",
            ),
            totals=DocumentTotals(
                subtotal=Decimal("22500.00"),
                discount=Decimal("500.00"),
                tax=Decimal("1125.00"),
                rounding=Decimal("0.25"),
                total=Decimal("23625.25"),
                paid=Decimal("10000.00"),
                balance=Decimal("13625.25"),
            ),
            sections=[
                DocumentSection(
                    title="Additional Charges",
                    lines=[
                        DocumentLine(description="Transport Charge", line_total=Decimal("250.00"))
                    ],
                )
            ],
            notes="Weekly settlement",
        )
        result = renderer.run(data)
        assert result.content.startswith(b"%PDF-")
        assert len(result.content) > 0

    def test_multi_line_document_renders_multiple_pages(self) -> None:
        many_items = [
            DocumentLine(
                description=f"Pomfret line {i}",
                quantity=Decimal("50.000"),
                unit="KG",
                unit_price=Decimal("450.0000"),
                tax_rate=Decimal("5.00"),
                tax_amount=Decimal("1125.00"),
                line_total=Decimal("23625.00"),
            )
            for i in range(60)
        ]
        renderer = PurchaseBillDocumentRenderer()
        result = renderer.run(_make_data(line_items=many_items))

        page_objects = re.findall(rb"/Type\s*/Page[^s]", result.content)
        assert len(page_objects) > 1

    def test_single_line_document_renders_one_page(self) -> None:
        renderer = PurchaseBillDocumentRenderer()
        result = renderer.run(_make_data())

        page_objects = re.findall(rb"/Type\s*/Page[^s]", result.content)
        assert len(page_objects) == 1

    def test_ten_items_render_successfully(self) -> None:
        items = [
            DocumentLine(
                description=f"Item {i}",
                quantity=Decimal("10.000"),
                unit="KG",
                unit_price=Decimal("100.0000"),
                tax_rate=Decimal("0.00"),
                tax_amount=Decimal("0.00"),
                line_total=Decimal("1000.00"),
            )
            for i in range(10)
        ]
        renderer = PurchaseBillDocumentRenderer()
        result = renderer.run(_make_data(line_items=items))
        assert result.content.startswith(b"%PDF-")

    def test_bill_number_appears_in_the_rendered_pdf_metadata(self) -> None:
        """The bill number is passed as the PDF's own /Title metadata
        (SimpleDocTemplate's `title=` kwarg) - checking for it there is
        a structural assertion, not a pixel-level layout check."""
        renderer = PurchaseBillDocumentRenderer()
        result = renderer.run(_make_data(document_number="PUR/2026-27/00099"))
        assert b"PUR/2026-27/00099" in result.content

    def test_default_content_type_class_attributes(self) -> None:
        assert PurchaseBillDocumentRenderer.content_type == "application/pdf"
        assert PurchaseBillDocumentRenderer.file_extension == "pdf"


class TestDocumentRegistryRegistration:
    def test_purchase_bill_type_is_registered_to_purchase_bill_document_renderer(self) -> None:
        assert registry.get(DocumentType.PURCHASE_BILL) is PurchaseBillDocumentRenderer

    def test_purchase_bill_type_is_registered(self) -> None:
        assert registry.is_registered(DocumentType.PURCHASE_BILL) is True
