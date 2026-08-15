"""Builds a friendly, filename-safe download name from an already-built
`ReportExportData` (TASKS.md Sprint 11 Session 5 Phase D) - shared by
every export-serving endpoint (the generic `/reports/export` dispatcher
and both Customer/Supplier Statement endpoints) so filename conventions
never drift between them.

Entity-scoped documents (Customer/Supplier Ledger, Customer/Supplier
Statement) set `ReportExportData.subtitle` to `"{name} ({code})"` - the
only 4 of the 11 report/statement types that do, since they're the only
ones scoped to a single named party. That's used as the signal to name
the file after the party (e.g. "Customer_Ledger_Konkan_Seafoods.xlsx")
rather than today's date (e.g. "Sales_Report_2026-07-30.pdf") - matching
every other (aggregate, not single-party) report.
"""

import re
from datetime import date

from app.core.report_export.export_models import ReportExportData

_ILLEGAL_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE_OR_HYPHEN = re.compile(r"[\s-]+")
_REPEATED_UNDERSCORES = re.compile(r"_{2,}")


def _sanitize(text: str) -> str:
    """`data.title` and entity names already arrive properly worded
    (e.g. "Sales Report", "Konkan Seafoods") - this never re-cases
    anything, it only strips characters Windows/Unix both forbid in
    filenames and collapses whitespace/hyphens into single underscores."""
    cleaned = _ILLEGAL_FILENAME_CHARS.sub("", text)
    cleaned = _WHITESPACE_OR_HYPHEN.sub("_", cleaned)
    cleaned = _REPEATED_UNDERSCORES.sub("_", cleaned)
    return cleaned.strip("_")


def build_export_filename(data: ReportExportData, *, extension: str) -> str:
    label = _sanitize(data.title)
    if data.subtitle:
        entity_name = data.subtitle.split(" (")[0]
        identifier = _sanitize(entity_name) or date.today().isoformat()
    else:
        identifier = date.today().isoformat()
    return f"{label}_{identifier}.{extension}"
