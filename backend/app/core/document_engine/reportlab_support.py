"""Shared ReportLab plumbing for BaseDocumentRenderer implementations
that choose ReportLab as their rendering backend (Invoice - Sprint 12
Session 2; Purchase Bill - Session 3). Extracted here once a second
concrete renderer needed the identical page-numbering/footer machinery
verbatim, per this session's own guidance: only extract an abstraction
once it is clearly shared, never as a premature framework.

This module is deliberately separate from base_document.py/
document_service.py/registry.py - those stay renderer-agnostic (nothing
in the core engine imports ReportLab); only a renderer that opts into
ReportLab imports this module. Only the page-numbering/footer machinery
lives here - Paragraph styles, colors and table layout stay local to
each renderer, since "look" is a per-document-type choice that may
legitimately diverge later, while pagination bookkeeping is pure
mechanism with no business meaning at all.
"""

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, HRFlowable, Image, Paragraph, Table, TableStyle

PDF_PAGE_SIZE = A4
PDF_MARGIN = 18 * mm

# Sprint 15 (document visual polish): a small shared palette + a few pure
# layout-mechanism widgets (badge/divider/card) every ReportLab renderer
# draws on top of its own local styles/wording. Kept here rather than
# duplicated per renderer for the same reason NumberedCanvas is - none of
# it carries any business meaning of its own (a badge's *color* is driven
# by a caller-supplied status string, a card doesn't know what's inside
# it), only mechanism. Business wording/layout choices ("Bill To" vs
# "Supplier", whether a totals table even exists) stay local to each
# renderer, unchanged.
MUTED_TEXT_HEX = "#6b7280"
MUTED_TEXT_COLOR = colors.HexColor(MUTED_TEXT_HEX)
HEADER_DIVIDER_COLOR = colors.HexColor("#1f2937")

# status string (lowercased, as stored on the domain model) -> (background, text)
# hex colors. Covers every status value used across Invoice/PurchaseBill/
# PurchaseOrder/DeliveryChallan/Payment/SupplierPayment - a status this
# codebase hasn't introduced yet falls back to _DEFAULT_STATUS_BADGE_COLORS
# rather than raising, since a renderer must never fail on an unrecognized
# status string.
_STATUS_BADGE_COLORS: dict[str, tuple[str, str]] = {
    "draft": ("#e5e7eb", "#374151"),
    "issued": ("#dbeafe", "#1e40af"),
    "posted": ("#dbeafe", "#1e40af"),
    "confirmed": ("#dbeafe", "#1e40af"),
    "dispatched": ("#dbeafe", "#1e40af"),
    "partially_paid": ("#fef3c7", "#92400e"),
    "paid": ("#d1fae5", "#065f46"),
    "fulfilled": ("#d1fae5", "#065f46"),
    "delivered": ("#d1fae5", "#065f46"),
    "cancelled": ("#fee2e2", "#991b1b"),
}
_DEFAULT_STATUS_BADGE_COLORS = ("#e5e7eb", "#374151")


def build_status_badge(status: str) -> Flowable:
    """A small pill-shaped, colored label for a document's status (Paid,
    Draft, Cancelled, ...) - replaces a plain 'Status: X' text line in a
    document header with something a reader can recognize at a glance.
    Caller is responsible for right-aligning it (`hAlign="RIGHT"` is set
    here, but placement within the page is up to the caller's layout)."""
    background_hex, text_hex = _STATUS_BADGE_COLORS.get(
        status.lower(), _DEFAULT_STATUS_BADGE_COLORS
    )
    style = ParagraphStyle(
        "StatusBadgeLabel",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor(text_hex),
        alignment=TA_CENTER,
    )
    label = status.replace("_", " ").upper()
    table = Table([[Paragraph(label, style)]], hAlign="RIGHT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(background_hex)),
                ("ROUNDEDCORNERS", [6, 6, 6, 6]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    return table


def build_header_divider() -> Flowable:
    """A thin rule separating the tenant/document header block from the
    document body - drawn in the same slate tone as every renderer's
    line-item table header, so it reads as one deliberate palette rather
    than an arbitrary new color."""
    return HRFlowable(
        width="100%",
        thickness=1.2,
        color=HEADER_DIVIDER_COLOR,
        spaceBefore=8,
        spaceAfter=10,
        lineCap="round",
    )


def build_card(flowables: list[Flowable]) -> Table:
    """Wraps already-built flowables (a section heading + its body
    Paragraph, typically) in a padded, light-bordered box - the shared
    'info card' look every renderer uses for its party/payment-info
    section. Pure layout mechanism: this function has no idea what's
    inside the box, only how to draw the box itself."""
    table = Table([[flowables]])
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#e5e7eb")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fafb")),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return table


class NumberedCanvas(Canvas):
    """Stamps a caller-supplied left/right footer plus 'Page N of M' on
    every page. The total page count isn't known until the whole
    document has been laid out, so each page's drawing state is
    captured via `showPage()` and replayed in `save()` once the true
    total is known - the standard ReportLab technique for a total-page-
    count footer, applied here without depending on any private Canvas
    attribute for the current page number (the loop's own `enumerate`
    index is used instead, only for robustness against ReportLab
    feature changes across its own versions).
    """

    def __init__(
        self, *args: Any, footer_left: str = "", footer_right: str = "", **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self._footer_left = footer_left
        self._footer_right = footer_right
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()  # type: ignore[attr-defined]  # ReportLab-internal, not in the stub package

    def save(self) -> None:
        total_pages = len(self._saved_page_states)
        for page_number, state in enumerate(self._saved_page_states, start=1):
            self.__dict__.update(state)
            self._draw_footer(page_number, total_pages)
            super().showPage()
        super().save()

    def _draw_footer(self, page_number: int, total_pages: int) -> None:
        self.setStrokeColor(colors.lightgrey)
        self.setLineWidth(0.5)
        self.line(PDF_MARGIN, PDF_MARGIN - 4, PDF_PAGE_SIZE[0] - PDF_MARGIN, PDF_MARGIN - 4)
        self.setFont("Helvetica", 7)
        self.setFillColor(colors.grey)
        self.drawString(PDF_MARGIN, PDF_MARGIN - 14, self._footer_left)
        self.drawRightString(
            PDF_PAGE_SIZE[0] - PDF_MARGIN,
            PDF_MARGIN - 14,
            f"{self._footer_right}  -  Page {page_number} of {total_pages}",
        )


def build_logo_flowable(
    logo_bytes: bytes | None, *, max_width: float, max_height: float
) -> Flowable | None:
    """Builds a ReportLab Image flowable from raw logo bytes (Sprint 14 -
    Company Profile), scaled to fit within max_width x max_height while
    preserving aspect ratio. Returns None if logo_bytes is empty, or if
    the bytes can't be decoded as an image - a corrupt/unsupported logo
    must never break document generation, the header simply renders
    without one, same tolerance CompanyProfileService.get_document_context
    already applies at the storage-read layer.

    Deliberately only the image-decoding/scaling mechanism, not a
    rewritten _build_header - per this module's own scope, "look" stays
    local to each renderer; only pagination/asset mechanics with no
    business meaning live here.
    """
    if not logo_bytes:
        return None
    try:
        reader = ImageReader(BytesIO(logo_bytes))
        natural_width, natural_height = reader.getSize()
        if not natural_width or not natural_height:
            return None
        # Forces the full pixel decode now, inside this try/except -
        # Image() below is lazy (it only decodes at draw time, deep
        # inside doc.build()), so without this eager call a truncated/
        # corrupt image would construct successfully here and only fail
        # much later, well outside any error handling - taking down the
        # entire document instead of just rendering without a logo.
        # Image() itself cannot take this same `reader` (an ImageReader):
        # unlike ImageReader's own constructor, Image.__init__ only
        # special-cases a path string, a file-like object (`hasattr(...,
        # "read")`) or a Drawing - passed anything else it tries
        # os.path.splitext() on it directly and crashes. A fresh BytesIO
        # of the same already-validated bytes is what it actually wants.
        reader.getRGBData()  # type: ignore[no-untyped-call]  # untyped in the stub package
        scale = min(max_width / natural_width, max_height / natural_height, 1.0)
        return Image(
            BytesIO(logo_bytes),
            width=natural_width * scale,
            height=natural_height * scale,
        )
    except Exception:
        return None
