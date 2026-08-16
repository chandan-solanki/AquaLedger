"""Unit tests for app.modules.delivery_challans.document_renderer (Sprint
12 Session 16) - mirrors test_purchase_order_document_renderer.py's own
style. Assertions are deliberately structural (PDF signature, non-empty
output, page count for the multi-page case) rather than pixel-level layout
checks, per this session's own testing guidance."""

import re
from datetime import UTC, date, datetime
from decimal import Decimal

from app.core.document_engine.document_models import DocumentData, DocumentLine, DocumentParty
from app.core.document_engine.document_types import DocumentType
from app.core.document_engine.registry import registry
from app.modules.delivery_challans.document_renderer import DeliveryChallanDocumentRenderer

_NOW = datetime(2026, 8, 15, 10, 30, tzinfo=UTC)


def _make_data(**overrides: object) -> DocumentData:
    defaults: dict[str, object] = {
        "document_type": DocumentType.DELIVERY_CHALLAN,
        "document_number": "DC/2026-27/00001",
        "document_date": date(2026, 8, 15),
        "title": "Delivery Challan",
        "tenant_name": "Konkan Traders",
        "line_items": [
            DocumentLine(
                description="Pomfret - Grade A",
                quantity=Decimal("40.000"),
                unit="KG",
                line_total=Decimal("40.000"),
                metadata={
                    "invoiced_quantity": Decimal("100.000"),
                    "previously_delivered_quantity": Decimal("0.000"),
                },
            )
        ],
        "generated_at": _NOW,
        "generated_by": "admin@fisherp.test",
    }
    defaults.update(overrides)
    return DocumentData(**defaults)


class TestDeliveryChallanDocumentRenderer:
    def test_returns_pdf_bytes_with_a_valid_signature(self) -> None:
        renderer = DeliveryChallanDocumentRenderer()
        result = renderer.run(_make_data())
        assert result.content.startswith(b"%PDF-")
        assert len(result.content) > 0

    def test_content_type_and_extension(self) -> None:
        renderer = DeliveryChallanDocumentRenderer()
        result = renderer.run(_make_data())
        assert result.content_type == "application/pdf"
        assert result.file_extension == "pdf"

    def test_renders_with_no_optional_fields_present(self) -> None:
        renderer = DeliveryChallanDocumentRenderer()
        data = _make_data(party=None, notes=None)
        result = renderer.run(data)
        assert result.content.startswith(b"%PDF-")

    def test_renders_with_full_data_including_party_and_notes(self) -> None:
        renderer = DeliveryChallanDocumentRenderer()
        data = _make_data(
            party=DocumentParty(
                name="Ocean Fresh Traders",
                code="CUST-001",
                address="12 Harbour Road, Mumbai, Maharashtra 400001, India",
                phone="9876543210",
                email="contact@oceanfresh.example",
                tax_id="27ABCDE1234F1Z5",
            ),
            notes="Handle with care",
            metadata={
                "status": "dispatched",
                "invoice_number": "INV/2026-27/00001",
                "invoice_date": date(2026, 8, 1),
            },
        )
        result = renderer.run(data)
        assert result.content.startswith(b"%PDF-")
        assert len(result.content) > 0

    def test_customer_name_appears_in_the_rendered_pdf(self) -> None:
        renderer = DeliveryChallanDocumentRenderer()
        data = _make_data(party=DocumentParty(name="Ocean Fresh Traders"))
        result = renderer.run(data)
        assert b"Ocean Fresh Traders" in result.content

    def test_invoice_number_appears_in_the_rendered_pdf(self) -> None:
        renderer = DeliveryChallanDocumentRenderer()
        data = _make_data(metadata={"invoice_number": "INV/2026-27/00042"})
        result = renderer.run(data)
        assert b"INV/2026-27/00042" in result.content

    def test_challan_number_appears_in_the_rendered_pdf(self) -> None:
        renderer = DeliveryChallanDocumentRenderer()
        result = renderer.run(_make_data(document_number="DC/2026-27/00099"))
        assert b"DC/2026-27/00099" in result.content

    def test_item_description_and_quantities_appear_in_the_rendered_pdf(self) -> None:
        renderer = DeliveryChallanDocumentRenderer()
        data = _make_data(
            line_items=[
                DocumentLine(
                    description="Surmai - Grade A",
                    quantity=Decimal("25.000"),
                    unit="KG",
                    line_total=Decimal("25.000"),
                    metadata={
                        "invoiced_quantity": Decimal("60.000"),
                        "previously_delivered_quantity": Decimal("35.000"),
                    },
                )
            ]
        )
        result = renderer.run(data)
        assert b"Surmai - Grade A" in result.content
        assert b"60.000" in result.content
        assert b"35.000" in result.content
        assert b"25.000" in result.content

    def test_remarks_appear_in_the_rendered_pdf_when_present(self) -> None:
        renderer = DeliveryChallanDocumentRenderer()
        result = renderer.run(_make_data(notes="Fragile - handle with care"))
        assert b"Fragile - handle with care" in result.content

    def test_acknowledgment_section_is_always_present(self) -> None:
        """The blank physical-acknowledgment lines (Received By/Signature/
        Date) are static, never data-driven - present regardless of what
        DocumentData carries."""
        renderer = DeliveryChallanDocumentRenderer()
        result = renderer.run(_make_data())
        assert b"Received By" in result.content
        assert b"Signature" in result.content

    def test_multi_item_document_renders_multiple_pages(self) -> None:
        many_items = [
            DocumentLine(
                description=f"Pomfret line {i}",
                quantity=Decimal("5.000"),
                unit="KG",
                line_total=Decimal("5.000"),
                metadata={
                    "invoiced_quantity": Decimal("10.000"),
                    "previously_delivered_quantity": Decimal("0.000"),
                },
            )
            for i in range(80)
        ]
        renderer = DeliveryChallanDocumentRenderer()
        result = renderer.run(_make_data(line_items=many_items))

        page_objects = re.findall(rb"/Type\s*/Page[^s]", result.content)
        assert len(page_objects) > 1

    def test_single_item_document_renders_one_page(self) -> None:
        renderer = DeliveryChallanDocumentRenderer()
        result = renderer.run(_make_data())

        page_objects = re.findall(rb"/Type\s*/Page[^s]", result.content)
        assert len(page_objects) == 1

    def test_ten_items_render_successfully(self) -> None:
        items = [
            DocumentLine(
                description=f"Item {i}",
                quantity=Decimal("10.000"),
                unit="KG",
                line_total=Decimal("10.000"),
                metadata={
                    "invoiced_quantity": Decimal("20.000"),
                    "previously_delivered_quantity": Decimal("0.000"),
                },
            )
            for i in range(10)
        ]
        renderer = DeliveryChallanDocumentRenderer()
        result = renderer.run(_make_data(line_items=items))
        assert result.content.startswith(b"%PDF-")

    def test_default_content_type_class_attributes(self) -> None:
        assert DeliveryChallanDocumentRenderer.content_type == "application/pdf"
        assert DeliveryChallanDocumentRenderer.file_extension == "pdf"

    def test_rendered_pdf_never_mentions_payment_or_outstanding_information(self) -> None:
        """Hard business rule: a delivery challan is not a financial
        document - the rendered PDF must never mention Paid/Balance/
        Outstanding, since DeliveryChallanDocumentRenderer never reads (or
        even receives) any DocumentTotals at all."""
        renderer = DeliveryChallanDocumentRenderer()
        result = renderer.run(_make_data())
        assert b"Paid" not in result.content
        assert b"Balance" not in result.content
        assert b"Outstanding" not in result.content


class TestDocumentRegistryRegistration:
    def test_delivery_challan_type_is_registered_to_its_renderer(self) -> None:
        assert registry.get(DocumentType.DELIVERY_CHALLAN) is DeliveryChallanDocumentRenderer

    def test_delivery_challan_type_is_registered(self) -> None:
        assert registry.is_registered(DocumentType.DELIVERY_CHALLAN) is True
