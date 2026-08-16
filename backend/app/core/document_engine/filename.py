"""Builds a friendly, filename-safe download name for a business
document (Sprint 12 Session 1) - one convention shared by every future
renderer/download endpoint, mirroring
`app.core.report_export.filenames.build_export_filename`'s own role for
reports.

Naming is deterministic and carries no random component (no UUID) - the
document number alone is enough to make the name unique and
human-readable: `Invoice_INV-000001.pdf`, `Purchase_Bill_PB-000021.pdf`,
`Customer_Payment_Receipt_RCP-000055.pdf`,
`Supplier_Payment_Receipt_SPR-000031.pdf`, `Purchase_Order_PO-000021.pdf`,
`Delivery_Challan_DC-000044.pdf`.
"""

import re

from app.core.document_engine.document_types import DocumentType

_ILLEGAL_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE = re.compile(r"\s+")
_REPEATED_UNDERSCORES = re.compile(r"_{2,}")

_DOCUMENT_TYPE_LABELS: dict[DocumentType, str] = {
    DocumentType.INVOICE: "Invoice",
    DocumentType.PURCHASE_BILL: "Purchase_Bill",
    DocumentType.CUSTOMER_PAYMENT_RECEIPT: "Customer_Payment_Receipt",
    DocumentType.SUPPLIER_PAYMENT_RECEIPT: "Supplier_Payment_Receipt",
    DocumentType.PURCHASE_ORDER: "Purchase_Order",
    DocumentType.DELIVERY_CHALLAN: "Delivery_Challan",
}


def _sanitize(text: str) -> str:
    """Unlike `report_export.filenames`'s sanitizer, hyphens are left
    untouched - a document number's own hyphen (`INV-000001`) is
    meaningful and must survive verbatim, whereas only whitespace is a
    word-separator worth collapsing here."""
    cleaned = _ILLEGAL_FILENAME_CHARS.sub("", text)
    cleaned = _WHITESPACE.sub("_", cleaned)
    cleaned = _REPEATED_UNDERSCORES.sub("_", cleaned)
    return cleaned.strip("_.")


def build_document_filename(
    document_type: DocumentType, document_number: str, *, extension: str
) -> str:
    label = _DOCUMENT_TYPE_LABELS[document_type]
    number = _sanitize(document_number)
    if not number:
        raise ValueError(
            f"document_number {document_number!r} has no nameable characters after sanitizing"
        )
    return f"{label}_{number}.{extension}"
