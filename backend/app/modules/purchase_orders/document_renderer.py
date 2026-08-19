"""ReportLab Platypus renderer for the Purchase Order PDF (Sprint 12
Session 11) - mirrors app.modules.purchase.document_renderer's own flow
(header/party/line-items/totals/notes), adapted to the Purchase Order's own
DTO shape: no fish name, the counterparty is a supplier (labeled "Supplier",
not "Bill To"), and - the one deliberate divergence from the Purchase Bill
renderer - the totals table never reads `paid`/`balance` at all, since a
purchase order is not a payable document. Every number rendered here is
read straight off DocumentData, formatted for display only - no financial
calculation of any kind.

Importing this module registers PurchaseOrderDocumentRenderer into the
shared DocumentRegistry singleton for DocumentType.PURCHASE_ORDER -
app.modules.purchase_orders.router does
`import app.modules.purchase_orders.document_renderer  # noqa: F401` once,
at module load time, the same pattern every other document-bearing module
uses.

Page-numbering/footer machinery is shared with every other document
renderer via app.core.document_engine.reportlab_support - see that
module's own docstring for why it was extracted there rather than
duplicated.
"""

from datetime import date
from decimal import Decimal
from functools import partial
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.document_engine.base_document import BaseDocumentRenderer
from app.core.document_engine.document_models import DocumentData, DocumentLine, DocumentTotals
from app.core.document_engine.document_types import DocumentType
from app.core.document_engine.registry import registry
from app.core.document_engine.reportlab_support import MUTED_TEXT_HEX as _MUTED_TEXT_HEX
from app.core.document_engine.reportlab_support import PDF_MARGIN as _MARGIN
from app.core.document_engine.reportlab_support import PDF_PAGE_SIZE as _PAGE_SIZE
from app.core.document_engine.reportlab_support import NumberedCanvas as _NumberedCanvas
from app.core.document_engine.reportlab_support import build_card as _build_card
from app.core.document_engine.reportlab_support import build_header_divider as _build_header_divider
from app.core.document_engine.reportlab_support import build_logo_flowable as _build_logo_flowable
from app.core.document_engine.reportlab_support import build_status_badge as _build_status_badge

_MISSING = "-"

_STYLES = getSampleStyleSheet()
_TENANT_NAME_STYLE = ParagraphStyle(
    "PurchaseOrderTenantName",
    parent=_STYLES["Heading1"],
    fontSize=16,
    leading=20,
    alignment=TA_LEFT,
)
_DOCUMENT_TITLE_STYLE = ParagraphStyle(
    "PurchaseOrderDocumentTitle",
    parent=_STYLES["Normal"],
    fontSize=10,
    leading=14,
    alignment=TA_RIGHT,
)
_SECTION_HEADING_STYLE = ParagraphStyle(
    "PurchaseOrderSectionHeading",
    parent=_STYLES["Heading3"],
    fontSize=10,
    leading=13,
    spaceBefore=4,
    spaceAfter=2,
)
_BODY_STYLE = ParagraphStyle("PurchaseOrderBody", parent=_STYLES["Normal"], fontSize=9, leading=12)
_BODY_RIGHT_STYLE = ParagraphStyle("PurchaseOrderBodyRight", parent=_BODY_STYLE, alignment=TA_RIGHT)
_TABLE_HEADER_STYLE = ParagraphStyle(
    "PurchaseOrderTableHeader",
    parent=_BODY_STYLE,
    fontName="Helvetica-Bold",
    textColor=colors.white,
)

_LINE_ITEM_HEADERS = ["#", "Item", "Qty", "Unit", "Rate", "Tax", "Amount"]
_LINE_ITEM_COLUMN_FRACTIONS = [0.05, 0.35, 0.10, 0.08, 0.14, 0.12, 0.16]


def _money(value: Decimal | None) -> str:
    if value is None:
        return _MISSING
    return f"{value:,.2f}"


def _quantity(value: Decimal | None) -> str:
    if value is None:
        return _MISSING
    return f"{value:,.3f}"


def _build_header(data: DocumentData, usable_width: float) -> Table:
    left: list[Flowable] = []
    logo = _build_logo_flowable(data.tenant_logo_bytes, max_width=28 * mm, max_height=18 * mm)
    if logo is not None:
        left.append(logo)
    left.append(Paragraph(data.tenant_name, _TENANT_NAME_STYLE))
    if data.tenant_details:
        muted_details = f'<font color="{_MUTED_TEXT_HEX}">{data.tenant_details}</font>'
        left.append(Paragraph(muted_details, _BODY_STYLE))

    right_lines = [
        f"<b>{data.title.upper()}</b>",
        f"No: {data.document_number}",
        f"Date: {data.document_date.strftime('%d %b %Y')}",
    ]
    expected_delivery = data.metadata.get("expected_delivery_date") if data.metadata else None
    if isinstance(expected_delivery, date):
        right_lines.append(f"Expected Delivery: {expected_delivery.strftime('%d %b %Y')}")
    right: list[Flowable] = [Paragraph("<br/>".join(right_lines), _DOCUMENT_TITLE_STYLE)]
    status = data.metadata.get("status") if data.metadata else None
    if status:
        right.append(Spacer(1, 4))
        right.append(_build_status_badge(str(status)))

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
    body = "<br/>".join(
        line if index == 0 else f'<font color="{_MUTED_TEXT_HEX}">{line}</font>'
        for index, line in enumerate(lines)
    )
    return [
        # "Supplier", not "Bill To" - a purchase order's counterparty is
        # who we're ordering from, the opposite direction from an
        # invoice's customer.
        _build_card([Paragraph("Supplier", _SECTION_HEADING_STYLE), Paragraph(body, _BODY_STYLE)])
    ]


def _build_line_items_table(items: list[DocumentLine], usable_width: float) -> Table:
    header_row: list[Flowable] = [
        Paragraph(text, _TABLE_HEADER_STYLE) for text in _LINE_ITEM_HEADERS
    ]
    rows: list[list[Flowable]] = [header_row]
    for index, line in enumerate(items, start=1):
        rows.append(
            [
                Paragraph(str(index), _BODY_STYLE),
                Paragraph(line.description, _BODY_STYLE),
                Paragraph(_quantity(line.quantity), _BODY_RIGHT_STYLE),
                Paragraph(line.unit or _MISSING, _BODY_STYLE),
                Paragraph(_money(line.unit_price), _BODY_RIGHT_STYLE),
                Paragraph(_money(line.tax_amount), _BODY_RIGHT_STYLE),
                Paragraph(_money(line.line_total), _BODY_RIGHT_STYLE),
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


def _build_sections(data: DocumentData) -> list[Flowable]:
    """Renders DocumentData.sections generically (e.g. the purchase order
    builder's own "Additional Charges" section for a non-zero
    transport_charge/other_charge) - the renderer has no knowledge of what
    a section means, only how to lay out its title and optional line
    rows."""
    flowables: list[Flowable] = []
    for section in data.sections:
        if section.title:
            flowables.append(Paragraph(section.title, _SECTION_HEADING_STYLE))
        if section.lines:
            rows = [
                [
                    Paragraph(line.description, _BODY_STYLE),
                    Paragraph(_money(line.line_total), _BODY_RIGHT_STYLE),
                ]
                for line in section.lines
            ]
            table = Table(rows, colWidths=[None, 80], hAlign="RIGHT")
            flowables.append(table)
        flowables.append(Spacer(1, 6))
    return flowables


def _build_totals_table(totals: DocumentTotals) -> Table:
    """Deliberately reads only subtotal/discount/tax/rounding/total - never
    `totals.paid`/`totals.balance`, even though DocumentTotals (a model
    shared with payable documents like Purchase Bill) still carries those
    fields. A purchase order is a procurement commitment, not a bill, so
    this renderer must never surface payment/outstanding information,
    regardless of what the caller happens to populate."""
    rows: list[tuple[str, str]] = [("Subtotal", _money(totals.subtotal))]
    if totals.discount:
        rows.append(("Discount", f"-{_money(totals.discount)}"))
    if totals.tax:
        rows.append(("Tax", _money(totals.tax)))
    if totals.rounding:
        rows.append(("Rounding", _money(totals.rounding)))
    total_row_index = len(rows)
    rows.append(("Total", _money(totals.total)))

    table_data = [
        [Paragraph(label, _BODY_STYLE), Paragraph(value, _BODY_RIGHT_STYLE)]
        for label, value in rows
    ]
    table = Table(table_data, colWidths=[120, 90], hAlign="RIGHT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, total_row_index), (-1, -1), colors.HexColor("#f3f4f6")),
                ("LINEABOVE", (0, total_row_index), (-1, total_row_index), 0.75, colors.black),
                ("FONTNAME", (0, total_row_index), (-1, total_row_index), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return table


def _build_notes(data: DocumentData) -> list[Flowable]:
    if not data.notes:
        return []
    return [
        Spacer(1, 10),
        Paragraph("Notes", _SECTION_HEADING_STYLE),
        Paragraph(data.notes, _BODY_STYLE),
    ]


class PurchaseOrderDocumentRenderer(BaseDocumentRenderer):
    """Renders a purchase order DocumentData to PDF bytes via ReportLab
    Platypus. Multi-page orders paginate correctly because every element is
    a flowable - `Table(..., repeatRows=1)` repeats the line-item header row
    on every page the table itself splits across, and `KeepTogether` keeps
    the totals block from splitting mid-block."""

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
            # Uncompressed content streams - a purchase order is a small,
            # few-page document, so the size cost is negligible, and it
            # keeps the PDF's text greppable for debugging/auditing.
            pageCompression=0,
        )

        story: list[Flowable] = [_build_header(data, usable_width), _build_header_divider()]
        story.extend(_build_party_section(data))
        story.append(Spacer(1, 10))
        story.append(_build_line_items_table(data.line_items, usable_width))
        story.append(Spacer(1, 10))
        story.extend(_build_sections(data))
        if data.totals is not None:
            story.append(KeepTogether([_build_totals_table(data.totals)]))
        story.extend(_build_notes(data))

        generated_at_display = data.generated_at.strftime("%Y-%m-%d %H:%M")
        footer_left = f"Generated by {data.generated_by} on {generated_at_display}"
        footer_right = "This is a system generated document."
        canvas_factory = partial(
            _NumberedCanvas, footer_left=footer_left, footer_right=footer_right
        )
        doc.build(story, canvasmaker=canvas_factory)
        return buffer.getvalue()


registry.register(DocumentType.PURCHASE_ORDER, PurchaseOrderDocumentRenderer)
