from decimal import Decimal
from pathlib import Path
from typing import Any

import weasyprint
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.report_export.base_exporter import BaseExporter
from app.core.report_export.export_models import ReportExportData
from app.core.report_export.formatting import format_value

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# 9+ columns (Trip/Boat Profitability, Fish Sales Analytics) render in
# landscape; the module's narrower 7-8 column reports (both Ledgers,
# Sales/Purchase, Outstanding, Aging) stay portrait (TASKS.md Sprint 11
# Session 5 Phase B: "Landscape automatically for wide reports").
_LANDSCAPE_COLUMN_THRESHOLD = 8

_environment = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
)


class PDFExporter(BaseExporter):
    """Renders `templates/report.html` (+ `templates/report.css`) via
    Jinja2, then hands the resulting HTML string straight to WeasyPrint -
    no JavaScript anywhere in the pipeline (TASKS.md Sprint 11 Session 5
    Phase B). Page numbers and the generated-by footer repeat on every
    physical page via plain CSS (`@page` margin boxes + a `position:
    running()` element in report.css) - WeasyPrint needs no Python-side
    pagination logic for that. The data table's `<thead>` repeats on
    every page natively, since WeasyPrint paginates HTML tables the same
    way browsers print them.
    """

    content_type = "application/pdf"
    file_extension = "pdf"

    def export(self, data: ReportExportData) -> bytes:
        html_string = self._render_html(data)
        pdf_bytes: bytes | None = weasyprint.HTML(
            string=html_string, base_url=str(_TEMPLATES_DIR)
        ).write_pdf()
        assert pdf_bytes is not None
        return pdf_bytes

    @classmethod
    def _render_html(cls, data: ReportExportData) -> str:
        template = _environment.get_template("report.html")
        rows = [
            {
                column.key: format_value(row.data[column.key], column.format)
                for column in data.columns
            }
            for row in data.rows
        ]
        summary = [
            {"label": item.label, "value": cls._format_summary_value(item.value)}
            for item in data.summary
        ]
        return template.render(
            title=data.title,
            subtitle=data.subtitle,
            tenant_name=data.tenant_name,
            tenant_initials=cls._initials(data.tenant_name),
            generated_at=data.generated_at.strftime("%Y-%m-%d %H:%M"),
            generated_by=data.generated_by,
            footer=data.footer,
            filters=data.filters,
            summary=summary,
            columns=data.columns,
            rows=rows,
            is_landscape=len(data.columns) > _LANDSCAPE_COLUMN_THRESHOLD,
        )

    @staticmethod
    def _initials(tenant_name: str) -> str:
        words = tenant_name.split()
        if not words:
            return "?"
        if len(words) == 1:
            return words[0][:2].upper()
        return (words[0][0] + words[-1][0]).upper()

    @staticmethod
    def _format_summary_value(value: Any) -> str:
        # ReportSummary carries no ColumnFormat of its own (unlike
        # ReportRow/ReportColumn pairs), so Decimal values here are
        # rendered as plain thousands-separated numbers rather than
        # guessing money/percent/quantity - the summary *label* already
        # says "... %" for the two percent-valued fields this module
        # produces, so not re-appending "%" here avoids a redundant
        # "73.94%%"-style suffix.
        if value is None:
            return "-"
        if isinstance(value, Decimal):
            return f"{value:,.2f}"
        if isinstance(value, int):
            return f"{value:,}"
        return str(value)
