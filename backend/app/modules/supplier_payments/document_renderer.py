"""ReportLab Platypus renderer for the Supplier Payment Receipt PDF
(Sprint 12 Session 4) - mirrors app.modules.payments.document_renderer's
own flow exactly (header/party/payment-info/amount/allocations/notes),
adapted to the Supplier Payment's own DTO shape and business direction:
money is going OUT to a supplier, so the party section reads "Paid To"
and the amount block reads "Amount Paid" rather than "Received From"/
"Amount Received". Every number rendered here is read straight off
DocumentData, formatted for display only - no financial calculation of
any kind.

Importing this module registers SupplierPaymentReceiptRenderer into the
shared DocumentRegistry singleton for DocumentType.SUPPLIER_PAYMENT_RECEIPT
- app.modules.supplier_payments.router does
`import app.modules.supplier_payments.document_renderer  # noqa: F401`
once, at module load time, the same pattern every other business
document renderer in this codebase uses.

Page-numbering/footer machinery is shared with the Invoice/Purchase
Bill/Customer Payment Receipt renderers via
app.core.document_engine.reportlab_support - see that module's own
docstring for why it was extracted there rather than duplicated.
Everything else here stays local and receipt-specific, the same
architectural boundary app.modules.payments.document_renderer draws.
"""

from decimal import Decimal
from functools import partial
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
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
from app.core.document_engine.document_models import DocumentData, DocumentTotals
from app.core.document_engine.document_types import DocumentType
from app.core.document_engine.registry import registry
from app.core.document_engine.reportlab_support import PDF_MARGIN as _MARGIN
from app.core.document_engine.reportlab_support import PDF_PAGE_SIZE as _PAGE_SIZE
from app.core.document_engine.reportlab_support import NumberedCanvas as _NumberedCanvas

_MISSING = "-"

_STYLES = getSampleStyleSheet()
_TENANT_NAME_STYLE = ParagraphStyle(
    "SupplierReceiptTenantName",
    parent=_STYLES["Heading1"],
    fontSize=16,
    leading=20,
    alignment=TA_LEFT,
)
_DOCUMENT_TITLE_STYLE = ParagraphStyle(
    "SupplierReceiptDocumentTitle",
    parent=_STYLES["Normal"],
    fontSize=10,
    leading=14,
    alignment=TA_RIGHT,
)
_SECTION_HEADING_STYLE = ParagraphStyle(
    "SupplierReceiptSectionHeading",
    parent=_STYLES["Heading3"],
    fontSize=10,
    leading=13,
    spaceBefore=4,
    spaceAfter=2,
)
_BODY_STYLE = ParagraphStyle(
    "SupplierReceiptBody", parent=_STYLES["Normal"], fontSize=9, leading=12
)
_BODY_RIGHT_STYLE = ParagraphStyle(
    "SupplierReceiptBodyRight", parent=_BODY_STYLE, alignment=TA_RIGHT
)
_TABLE_HEADER_STYLE = ParagraphStyle(
    "SupplierReceiptTableHeader",
    parent=_BODY_STYLE,
    fontName="Helvetica-Bold",
    textColor=colors.white,
)

_ALLOCATION_TABLE_HEADERS = ["Purchase Bill", "Applied Amount"]


def _money(value: Decimal | None) -> str:
    if value is None:
        return _MISSING
    return f"{value:,.2f}"


def _build_header(data: DocumentData, usable_width: float) -> Table:
    left: list[Flowable] = [Paragraph(data.tenant_name, _TENANT_NAME_STYLE)]
    if data.tenant_details:
        left.append(Paragraph(data.tenant_details, _BODY_STYLE))

    right_lines = [
        f"<b>{data.title.upper()}</b>",
        f"No: {data.document_number}",
        f"Date: {data.document_date.strftime('%d %b %Y')}",
    ]
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
        # "Paid To" - money is going out, to a supplier.
        Paragraph("Paid To", _SECTION_HEADING_STYLE),
        Paragraph("<br/>".join(lines), _BODY_STYLE),
    ]


def _build_payment_info(data: DocumentData) -> list[Flowable]:
    metadata = data.metadata or {}
    lines = []
    method = metadata.get("payment_method")
    if method:
        lines.append(f"Payment Method: {str(method).replace('_', ' ').title()}")
    reference = metadata.get("reference_number")
    if reference:
        lines.append(f"Reference Number: {reference}")
    bank = metadata.get("bank_name")
    if bank:
        lines.append(f"Bank Name: {bank}")
    status = metadata.get("status")
    if status:
        lines.append(f"Status: {str(status).replace('_', ' ').title()}")
    if not lines:
        return []
    return [
        Paragraph("Payment Information", _SECTION_HEADING_STYLE),
        Paragraph("<br/>".join(lines), _BODY_STYLE),
    ]


def _build_amount_block(totals: DocumentTotals | None) -> Table | None:
    if totals is None:
        return None
    rows: list[tuple[str, str]] = [("Amount Paid", _money(totals.total))]
    if totals.paid is not None:
        rows.append(("Applied to Purchase Bills", _money(totals.paid)))
    if totals.balance is not None:
        rows.append(("Unallocated Amount", _money(totals.balance)))

    table_data = [
        [Paragraph(label, _BODY_STYLE), Paragraph(value, _BODY_RIGHT_STYLE)]
        for label, value in rows
    ]
    table = Table(table_data, colWidths=[150, 100], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.black),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _build_allocations_section(data: DocumentData, usable_width: float) -> list[Flowable]:
    """Renders DocumentData.sections generically (the builder's own
    "Applied Payments" section, one row per allocation) - the renderer
    has no knowledge of what a section means, only how to lay out its
    title and optional line rows. `repeatRows=1` repeats the header row
    if a large payment's allocation list spans multiple pages."""
    flowables: list[Flowable] = []
    for section in data.sections:
        if section.title:
            flowables.append(Paragraph(section.title, _SECTION_HEADING_STYLE))
        if section.lines:
            header_row: list[Flowable] = [
                Paragraph(text, _TABLE_HEADER_STYLE) for text in _ALLOCATION_TABLE_HEADERS
            ]
            rows: list[list[Flowable]] = [header_row]
            for line in section.lines:
                rows.append(
                    [
                        Paragraph(line.description, _BODY_STYLE),
                        Paragraph(_money(line.line_total), _BODY_RIGHT_STYLE),
                    ]
                )
            table = Table(rows, colWidths=[usable_width * 0.65, usable_width * 0.35], repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#f9fafb")],
                        ),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            flowables.append(table)
        flowables.append(Spacer(1, 6))
    return flowables


def _build_notes(data: DocumentData) -> list[Flowable]:
    if not data.notes:
        return []
    return [
        Spacer(1, 10),
        Paragraph("Remarks", _SECTION_HEADING_STYLE),
        Paragraph(data.notes, _BODY_STYLE),
    ]


class SupplierPaymentReceiptRenderer(BaseDocumentRenderer):
    """Renders a supplier payment receipt DocumentData to PDF bytes via
    ReportLab Platypus. A large allocation list paginates correctly
    because every element is a flowable - `Table(..., repeatRows=1)`
    repeats the allocation table's header row on every page it splits
    across, and `KeepTogether` keeps the amount block from splitting
    mid-block."""

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
            # Uncompressed content streams - a receipt is a small,
            # almost-always-one-page document, so the size cost is
            # negligible, and it keeps the PDF's text greppable for
            # debugging/auditing.
            pageCompression=0,
        )

        story: list[Flowable] = [_build_header(data, usable_width), Spacer(1, 14)]
        story.extend(_build_party_section(data))
        story.append(Spacer(1, 10))
        story.extend(_build_payment_info(data))
        story.append(Spacer(1, 10))
        amount_table = _build_amount_block(data.totals)
        if amount_table is not None:
            story.append(KeepTogether([Paragraph("Amount", _SECTION_HEADING_STYLE), amount_table]))
        story.append(Spacer(1, 10))
        story.extend(_build_allocations_section(data, usable_width))
        story.extend(_build_notes(data))

        generated_at_display = data.generated_at.strftime("%Y-%m-%d %H:%M")
        footer_left = f"Generated by {data.generated_by} on {generated_at_display}"
        footer_right = "This is a system generated document."
        canvas_factory = partial(
            _NumberedCanvas, footer_left=footer_left, footer_right=footer_right
        )
        doc.build(story, canvasmaker=canvas_factory)
        return buffer.getvalue()


registry.register(DocumentType.SUPPLIER_PAYMENT_RECEIPT, SupplierPaymentReceiptRenderer)
