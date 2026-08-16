"""Pure DTO -> DocumentData transformation for the purchase bill PDF
(Sprint 12 Session 3). No database access, no financial/tax/balance
calculation - every value here already came from
PurchaseService.get_document_context(), itself built entirely from
existing PurchaseBillResponse/PurchaseBillItemResponse/SupplierResponse
fields. Nothing here is invented: fields the current Purchase Bill model
doesn't carry (a PO reference, payment terms, bank details, a QR code, a
digital signature) are simply never set, per this session's own "do not
invent business fields" rule. Mirrors
app.modules.invoices.document_builder's own structure exactly.
"""

from datetime import UTC, datetime

from app.core.document_engine.document_models import (
    DocumentData,
    DocumentLine,
    DocumentParty,
    DocumentSection,
    DocumentTotals,
)
from app.core.document_engine.document_types import DocumentType
from app.modules.purchase.schemas import PurchaseBillItemResponse, PurchaseBillResponse
from app.modules.suppliers.schemas import SupplierResponse


def _format_supplier_address(supplier: SupplierResponse) -> str | None:
    """Supplier's own address shape (`address`, `city`, `state`,
    `country` - no `address_line2`/`pincode`/`state_code` the way
    CompanyResponse has) - duplicated field-by-field rather than shared
    with app.modules.invoices.document_builder's own
    `_format_company_address`, since the two DTOs' shapes differ and
    cross-importing between business modules for a small helper isn't
    worth the coupling."""
    parts = [supplier.address, supplier.city, supplier.state, supplier.country]
    joined = ", ".join(part for part in parts if part)
    return joined or None


def _additional_charges_section(purchase_bill: PurchaseBillResponse) -> DocumentSection | None:
    """Mirrors app.modules.invoices.document_builder's own
    `_additional_charges_section` exactly - transport_charge/
    other_charge are real, already-computed columns folded into
    total_amount server-side but have no dedicated DocumentTotals slot,
    so they're shown as a generic section only when actually non-zero."""
    lines = []
    if purchase_bill.transport_charge:
        lines.append(
            DocumentLine(description="Transport Charge", line_total=purchase_bill.transport_charge)
        )
    if purchase_bill.other_charge:
        lines.append(
            DocumentLine(description="Other Charge", line_total=purchase_bill.other_charge)
        )
    if not lines:
        return None
    return DocumentSection(title="Additional Charges", lines=lines)


def build_purchase_bill_document_data(
    purchase_bill: PurchaseBillResponse,
    items: list[PurchaseBillItemResponse],
    supplier: SupplierResponse,
    *,
    tenant_name: str,
    generated_by: str,
) -> DocumentData:
    """Converts an already-fetched purchase bill + items + supplier
    (PurchaseService.get_document_context()) into the generic
    `DocumentData` the Document Engine (Sprint 12 Session 1) consumes.
    Every quantity/rate/tax/total value is copied verbatim from the
    already-authoritative response DTOs - nothing is multiplied, summed,
    or rounded here.
    """
    if purchase_bill.bill_number is None:
        # Enforced by PurchaseService.get_document_context() before this
        # is ever called - re-checked here only to satisfy mypy's
        # narrowing of `document_number: str` below, not a new business
        # rule.
        raise ValueError("purchase_bill.bill_number must be set before building its document")

    party = DocumentParty(
        id=str(supplier.id),
        name=supplier.name,
        code=supplier.code,
        address=_format_supplier_address(supplier),
        phone=supplier.phone,
        email=supplier.email,
        tax_id=supplier.gstin,
    )

    line_items = [
        DocumentLine(
            description=item.description or "-",
            quantity=item.quantity,
            unit=item.unit,
            unit_price=item.rate,
            tax_rate=item.tax_rate,
            tax_amount=item.tax_amount,
            line_total=item.line_total,
        )
        for item in items
    ]

    totals = DocumentTotals(
        subtotal=purchase_bill.subtotal,
        discount=purchase_bill.discount_amount,
        tax=purchase_bill.tax_amount,
        rounding=purchase_bill.round_off,
        total=purchase_bill.total_amount,
        paid=purchase_bill.paid_amount,
        balance=purchase_bill.balance_amount,
    )

    sections = []
    additional_charges = _additional_charges_section(purchase_bill)
    if additional_charges is not None:
        sections.append(additional_charges)

    return DocumentData(
        document_type=DocumentType.PURCHASE_BILL,
        document_number=purchase_bill.bill_number,
        document_date=purchase_bill.bill_date,
        title="Purchase Bill",
        tenant_name=tenant_name,
        party=party,
        sections=sections,
        line_items=line_items,
        totals=totals,
        notes=purchase_bill.remarks,
        metadata={"status": purchase_bill.status.value},
        generated_at=datetime.now(UTC),
        generated_by=generated_by,
    )


__all__ = ["build_purchase_bill_document_data"]
