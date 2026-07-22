"""Sprint 9 Session 5 - invoice numbering (ARCHITECTURE.md §13.1).

Pure formatting/calculation helpers only - no SQLAlchemy or FastAPI imports
(ARCHITECTURE.md §1.3's Domain Layer). The actual concurrency-safe counter
allocation (`INSERT ... ON CONFLICT DO NOTHING` + `SELECT ... FOR UPDATE`)
lives in InvoiceRepository/InvoiceService, since that requires the database.
"""

import datetime as dt

_SEQUENCE_WIDTH = 5


def fiscal_year_for(invoice_date: dt.date) -> str:
    """Indian GST fiscal year (April 1 - March 31) as "YYYY-YY", e.g.
    2026-07-22 -> "2026-27", 2026-02-10 -> "2025-26"."""
    start_year = invoice_date.year if invoice_date.month >= 4 else invoice_date.year - 1
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def format_invoice_number(prefix: str, fiscal_year: str, sequence: int) -> str:
    """`{prefix}/{fiscal_year}/{zero-padded sequence}`, e.g. "INV/2025-26/00042"."""
    return f"{prefix}/{fiscal_year}/{sequence:0{_SEQUENCE_WIDTH}d}"
