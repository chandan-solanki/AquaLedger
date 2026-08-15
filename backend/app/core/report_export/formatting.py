"""Renders one raw `ReportRow` value into a display string, for exporters
that need text (PDFExporter - a rendered document has no native numeric/
date cell types). ExcelExporter deliberately does NOT use this: its cells
keep their native Decimal/date/int type with an openpyxl `number_format`
applied, so the workbook stays sortable/filterable/summable in Excel.
CSVExporter never uses this either - CSV is raw values only (TASKS.md
Sprint 11 Session 5 Phase B). Centralizing PDF's own value-to-text
conversion here (rather than inlining it in pdf_exporter.py) is what
keeps "no duplicated export code" true if a future text-based exporter
ever needs the same conversion.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.core.report_export.export_models import ColumnFormat

_MISSING_VALUE_DISPLAY = "-"


def format_value(value: Any, column_format: ColumnFormat) -> str:
    if value is None:
        return _MISSING_VALUE_DISPLAY

    if column_format == ColumnFormat.CURRENCY:
        return f"{value:,.2f}"

    if column_format == ColumnFormat.PERCENT:
        return f"{value:.2f}%"

    if column_format in (ColumnFormat.DATE, ColumnFormat.DATETIME):
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M")
        if isinstance(value, date):
            return value.isoformat()
        return str(value)

    if column_format == ColumnFormat.NUMBER and isinstance(value, (int, Decimal)):
        return format(value, ",")

    return str(value)
