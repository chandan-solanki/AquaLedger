"""ReportLab Platypus renderer for the Delivery Challan PDF (Sprint 12
Session 16) - mirrors app.modules.purchase_orders.document_renderer's own
flow (header/party/line-items/notes), adapted to a delivery challan's own
DTO shape: the counterparty is a customer (labeled "Customer", not
"Supplier"), the item table shows quantity/delivery progress instead of
rate/tax/amount, and - the one deliberate divergence from every other
document renderer in this codebase - there is no totals table at all, since
a delivery challan is a physical delivery record, never a financial
document (this session's own hard business rule). A blank, printable
physical-acknowledgment area (Received By / Signature / Date) is added
instead - deliberately NOT a digital signature, QR code, or electronic
signing feature (out of this session's scope).

Importing this module registers DeliveryChallanDocumentRenderer into the
shared DocumentRegistry singleton for DocumentType.DELIVERY_CHALLAN -
app.modules.delivery_challans.router does
`import app.modules.delivery_challans.document_renderer  # noqa: F401` once,
at module load time, the same pattern every other document-bearing module
uses.

Page-numbering/footer machinery is shared with every other document
renderer via app.core.document_engine.reportlab_support - see that
module's own docstring for why it was extracted there rather than
duplicated.
"""

from datetime import date, datetime
from decimal import Decimal
from functools import partial
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.document_engine.base_document import BaseDocumentRenderer
from app.core.document_engine.document_models import DocumentData, DocumentLine
from app.core.document_engine.document_types import DocumentType
from app.core.document_engine.registry import registry
from app.core.document_engine.reportlab_support import PDF_MARGIN as _MARGIN
from app.core.document_engine.reportlab_support import PDF_PAGE_SIZE as _PAGE_SIZE
from app.core.document_engine.reportlab_support import NumberedCanvas as _NumberedCanvas

_MISSING = "-"

_STYLES = getSampleStyleSheet()
_TENANT_NAME_STYLE = ParagraphStyle(
    "DeliveryChallanTenantName",
    parent=_STYLES["Heading1"],
    fontSize=16,
    leading=20,
    alignment=TA_LEFT,
)
_DOCUMENT_TITLE_STYLE = ParagraphStyle(
    "DeliveryChallanDocumentTitle",
    parent=_STYLES["Normal"],
    fontSize=10,
    leading=14,
    alignment=TA_RIGHT,
)
_SECTION_HEADING_STYLE = ParagraphStyle(
    "DeliveryChallanSectionHeading",
    parent=_STYLES["Heading3"],
    fontSize=10,
    leading=13,
    spaceBefore=4,
    spaceAfter=2,
)
_BODY_STYLE = ParagraphStyle(
    "DeliveryChallanBody", parent=_STYLES["Normal"], fontSize=9, leading=12
)
_BODY_RIGHT_STYLE = ParagraphStyle(
    "DeliveryChallanBodyRight", parent=_BODY_STYLE, alignment=TA_RIGHT
)
_TABLE_HEADER_STYLE = ParagraphStyle(
    "DeliveryChallanTableHeader",
    parent=_BODY_STYLE,
    fontName="Helvetica-Bold",
    textColor=colors.white,
)

_LINE_ITEM_HEADERS = ["#", "Item", "Unit", "Invoiced", "Previously Delivered", "This Delivery"]
_LINE_ITEM_COLUMN_FRACTIONS = [0.05, 0.35, 0.10, 0.16, 0.19, 0.15]


def _quantity(value: Decimal | None) -> str:
    if value is None:
        return _MISSING
    return f"{value:,.3f}"


def _build_header(data: DocumentData, usable_width: float) -> Table:
    left: list[Flowable] = [Paragraph(data.tenant_name, _TENANT_NAME_STYLE)]
    if data.tenant_details:
        left.append(Paragraph(data.tenant_details, _BODY_STYLE))

    right_lines = [
        f"<b>{data.title.upper()}</b>",
        f"No: {data.document_number}",
        f"Date: {data.document_date.strftime('%d %b %Y')}",
    ]
    invoice_number = data.metadata.get("invoice_number") if data.metadata else None
    if invoice_number:
        right_lines.append(f"Invoice No: {invoice_number}")
    invoice_date = data.metadata.get("invoice_date") if data.metadata else None
    if isinstance(invoice_date, date):
        right_lines.append(f"Invoice Date: {invoice_date.strftime('%d %b %Y')}")
    status = data.metadata.get("status") if data.metadata else None
    if status:
        right_lines.append(f"Status: {str(status).replace('_', ' ').title()}")
    right = [Paragraph("<br/>".join(right_lines), _DOCUMENT_TITLE_STYLE)]

    table = Table([[left, right]], colWidths=[usable_width * 0.6, usable_width * 0.4])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return table


def _build_party_section(data: DocumentData) -> list[Flowable]:
    if data.party is None:
        return []
    lines = [f"<b>{data.party.name}</b>"]
    if data.party.code:
        lines.append(f"Code: {data.party.code}")
    if data.party.address:
        lines.append(data.party.address)
    if data.party.phone:
        lines.append(f"Phone: {data.party.phone}")
    if data.party.email:
        lines.append(f"Email: {data.party.email}")
    if data.party.tax_id:
        lines.append(f"GSTIN: {data.party.tax_id}")
    return [
        # "Customer", not "Supplier"/"Bill To" - a delivery challan's
        # counterparty is who the goods were physically delivered to.
        Paragraph("Customer", _SECTION_HEADING_STYLE),
        Paragraph("<br/>".join(lines), _BODY_STYLE),
    ]


def _build_line_items_table(items: list[DocumentLine], usable_width: float) -> Table:
    header_row: list[Flowable] = [
        Paragraph(text, _TABLE_HEADER_STYLE) for text in _LINE_ITEM_HEADERS
    ]
    rows: list[list[Flowable]] = [header_row]
    for index, line in enumerate(items, start=1):
        invoiced_quantity = line.metadata.get("invoiced_quantity") if line.metadata else None
        previously_delivered = (
            line.metadata.get("previously_delivered_quantity") if line.metadata else None
        )
        rows.append(
            [
                Paragraph(str(index), _BODY_STYLE),
                Paragraph(line.description, _BODY_STYLE),
                Paragraph(line.unit or _MISSING, _BODY_STYLE),
                Paragraph(_quantity(invoiced_quantity), _BODY_RIGHT_STYLE),
                Paragraph(_quantity(previously_delivered), _BODY_RIGHT_STYLE),
                Paragraph(_quantity(line.quantity), _BODY_RIGHT_STYLE),
            ]
        )

    col_widths = [usable_width * fraction for fraction in _LINE_ITEM_COLUMN_FRACTIONS]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _build_notes(data: DocumentData) -> list[Flowable]:
    if not data.notes:
        return []
    return [
        Spacer(1, 10),
        Paragraph("Remarks", _SECTION_HEADING_STYLE),
        Paragraph(data.notes, _BODY_STYLE),
    ]


def _build_acknowledgment_section() -> list[Flowable]:
    """A blank, printable physical-acknowledgment area - three plain lines
    a recipient fills in by hand once goods are physically received.
    Deliberately NOT a digital signature, QR code, or electronic signing
    feature (out of this session's scope) - just static text, never
    data-driven from DocumentData."""
    blank = "_" * 32
    return [
        Spacer(1, 24),
        Paragraph(f"Received By: {blank}", _BODY_STYLE),
        Spacer(1, 16),
        Paragraph(f"Signature: {blank}", _BODY_STYLE),
        Spacer(1, 16),
        Paragraph(f"Date: {blank}", _BODY_STYLE),
    ]


class DeliveryChallanDocumentRenderer(BaseDocumentRenderer):
    """Renders a delivery challan DocumentData to PDF bytes via ReportLab
    Platypus. Multi-item challans paginate correctly because every element
    is a flowable - `Table(..., repeatRows=1)` repeats the line-item header
    row on every page the table itself splits across."""

    content_type = "application/pdf"
    file_extension = "pdf"

    def render(self, data: DocumentData) -> bytes:
        buffer = BytesIO()
        usable_width = _PAGE_SIZE[0] - 2 * _MARGIN
        doc = SimpleDocTemplate(
            buffer,
            pagesize=_PAGE_SIZE,
            leftMargin=_MARGIN,
            rightMargin=_MARGIN,
            topMargin=_MARGIN,
            bottomMargin=_MARGIN + 12,
            title=f"{data.title} {data.document_number}",
            # Uncompressed content streams - a delivery challan is a small,
            # few-page document, so the size cost is negligible, and it
            # keeps the PDF's text greppable for debugging/auditing.
            pageCompression=0,
        )

        story: list[Flowable] = [_build_header(data, usable_width), Spacer(1, 14)]
        story.extend(_build_party_section(data))
        story.append(Spacer(1, 10))
        story.append(_build_line_items_table(data.line_items, usable_width))
        story.extend(_build_notes(data))
        story.extend(_build_acknowledgment_section())

        generated_at_display: datetime = data.generated_at
        footer_left = (
            f"Generated by {data.generated_by} on {generated_at_display.strftime('%Y-%m-%d %H:%M')}"
        )
        footer_right = "This is a system generated document."
        canvas_factory = partial(
            _NumberedCanvas, footer_left=footer_left, footer_right=footer_right
        )
        doc.build(story, canvasmaker=canvas_factory)
        return buffer.getvalue()


registry.register(DocumentType.DELIVERY_CHALLAN, DeliveryChallanDocumentRenderer)
