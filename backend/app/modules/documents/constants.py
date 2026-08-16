from enum import StrEnum


class PartyType(StrEnum):
    """The business-entity kinds a generated document can be about
    (Sprint 12 Session 6). Deliberately just a label, not a foreign key -
    `DocumentRecord.party_id` can point at `companies.id` (CUSTOMER) or
    `suppliers.id` (SUPPLIER) depending on this value, so a real FK
    constraint spanning both possible targets isn't expressible - the
    Document Center trades that referential guarantee for staying free of
    cross-module coupling (ARCHITECTURE.md §2)."""

    CUSTOMER = "customer"
    SUPPLIER = "supplier"


class SourceType(StrEnum):
    """Which business module/table `DocumentRecord.source_id` resolves
    against (Sprint 12 Session 8) - deliberately a distinct vocabulary
    from `DocumentType`: a `customer_payment_receipt` document's source
    row lives in `payments`, not a `customer_payment_receipts` table, so
    `source_type` names the owning module ("payment"), while
    `document_type` names the rendered document ("customer_payment_
    receipt"). Like `PartyType`, this is a label only, never a foreign
    key - `source_id` can point at `invoices.id`, `purchase_bills.id`,
    `payments.id`, `supplier_payments.id`, `purchase_orders.id` or
    `delivery_challans.id` depending on this value, so no single FK
    constraint could span all six possible targets."""

    INVOICE = "invoice"
    PURCHASE_BILL = "purchase_bill"
    PAYMENT = "payment"
    SUPPLIER_PAYMENT = "supplier_payment"
    PURCHASE_ORDER = "purchase_order"
    DELIVERY_CHALLAN = "delivery_challan"
