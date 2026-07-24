"""Sprint 12 Session 5 - supplier payment numbering (ARCHITECTURE.md §13.1,
applied to supplier payments).

Pure formatting/calculation helpers only - no SQLAlchemy or FastAPI imports
(ARCHITECTURE.md §1.3's Domain Layer). Mirrors payments/domain/numbering.py /
purchase/domain/numbering.py exactly; the actual concurrency-safe counter
allocation (`INSERT ... ON CONFLICT DO NOTHING` + `SELECT ... FOR UPDATE`)
lives in SupplierPaymentRepository/SupplierPaymentService, since that
requires the database.
"""

import datetime as dt

_SEQUENCE_WIDTH = 5


def fiscal_year_for(payment_date: dt.date) -> str:
    """Indian GST fiscal year (April 1 - March 31) as "YYYY-YY", e.g.
    2026-07-23 -> "2026-27", 2026-02-10 -> "2025-26"."""
    start_year = payment_date.year if payment_date.month >= 4 else payment_date.year - 1
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def format_supplier_payment_number(prefix: str, fiscal_year: str, sequence: int) -> str:
    """`{prefix}/{fiscal_year}/{zero-padded sequence}`, e.g. "SPAY/2026-27/00042"."""
    return f"{prefix}/{fiscal_year}/{sequence:0{_SEQUENCE_WIDTH}d}"
