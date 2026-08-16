"""The controlled set of business documents this engine knows how to
validate against. Adding a new document type later means adding one
value here - the engine itself (registry.py, document_service.py) never
special-cases a specific type by name.

Statements (Customer/Supplier Statement) are deliberately excluded -
those are analytical documents built from Reports data and remain part
of `app.core.report_export` (ARCHITECTURE.md §41), not this engine.
"""

from enum import StrEnum


class DocumentType(StrEnum):
    INVOICE = "invoice"
    PURCHASE_BILL = "purchase_bill"
    CUSTOMER_PAYMENT_RECEIPT = "customer_payment_receipt"
    SUPPLIER_PAYMENT_RECEIPT = "supplier_payment_receipt"
    PURCHASE_ORDER = "purchase_order"
    DELIVERY_CHALLAN = "delivery_challan"
