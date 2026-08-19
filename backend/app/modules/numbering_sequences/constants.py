from enum import StrEnum

# Mirrors app.modules.dashboard.repository's own precedent for cross-module
# reads (ARCHITECTURE.md §2 only forbids reaching into another module's
# *internals* - private domain helpers/constants - not its plain, stable
# public constants like a status enum or, here, a numbering prefix).
from app.modules.delivery_challans.constants import DELIVERY_CHALLAN_NUMBER_PREFIX
from app.modules.invoices.constants import INVOICE_NUMBER_PREFIX
from app.modules.payments.constants import PAYMENT_NUMBER_PREFIX
from app.modules.purchase.constants import PURCHASE_NUMBER_PREFIX
from app.modules.purchase_orders.constants import PURCHASE_ORDER_NUMBER_PREFIX
from app.modules.supplier_payments.constants import SUPPLIER_PAYMENT_NUMBER_PREFIX

# Zero-padded digit width of the sequence portion of every generated
# document number - mirrors each module's own `domain/numbering.py`
# `_SEQUENCE_WIDTH` exactly (all six are "5", per the audit backing this
# Settings > Numbering Sequences page).
SEQUENCE_WIDTH = 5


class NumberingDocumentType(StrEnum):
    INVOICE = "invoice"
    PURCHASE_BILL = "purchase_bill"
    PURCHASE_ORDER = "purchase_order"
    CUSTOMER_PAYMENT = "customer_payment"
    SUPPLIER_PAYMENT = "supplier_payment"
    DELIVERY_CHALLAN = "delivery_challan"


NUMBERING_DOCUMENT_LABELS: dict[NumberingDocumentType, str] = {
    NumberingDocumentType.INVOICE: "Invoice",
    NumberingDocumentType.PURCHASE_BILL: "Purchase Bill",
    NumberingDocumentType.PURCHASE_ORDER: "Purchase Order",
    NumberingDocumentType.CUSTOMER_PAYMENT: "Customer Payment",
    NumberingDocumentType.SUPPLIER_PAYMENT: "Supplier Payment",
    NumberingDocumentType.DELIVERY_CHALLAN: "Delivery Challan",
}

NUMBERING_DOCUMENT_PREFIXES: dict[NumberingDocumentType, str] = {
    NumberingDocumentType.INVOICE: INVOICE_NUMBER_PREFIX,
    NumberingDocumentType.PURCHASE_BILL: PURCHASE_NUMBER_PREFIX,
    NumberingDocumentType.PURCHASE_ORDER: PURCHASE_ORDER_NUMBER_PREFIX,
    NumberingDocumentType.CUSTOMER_PAYMENT: PAYMENT_NUMBER_PREFIX,
    NumberingDocumentType.SUPPLIER_PAYMENT: SUPPLIER_PAYMENT_NUMBER_PREFIX,
    NumberingDocumentType.DELIVERY_CHALLAN: DELIVERY_CHALLAN_NUMBER_PREFIX,
}
