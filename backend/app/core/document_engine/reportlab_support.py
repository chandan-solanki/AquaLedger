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

from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

PDF_PAGE_SIZE = A4
PDF_MARGIN = 18 * mm


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
