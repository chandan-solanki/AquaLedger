"""Pure DTO -> DocumentData transformation for the purchase order PDF
(Sprint 12 Session 11). No database access, no financial/tax calculation -
every value here already came from
PurchaseOrderService.get_document_context(), itself built entirely from
existing PurchaseOrderResponse/PurchaseOrderItemResponse/SupplierResponse
fields. Nothing here is invented: fields the current Purchase Order model
doesn't carry (payment terms, bank details, a QR code, a digital signature)
are simply never set - and `DocumentTotals.paid`/`balance` are deliberately
never set either, since a purchase order is not a payable document (that
distinction belongs to Purchase Bill). Mirrors
app.modules.purchase.document_builder's own structure exactly.
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
from app.modules.purchase_orders.schemas import PurchaseOrderItemResponse, PurchaseOrderResponse
from app.modules.suppliers.schemas import SupplierResponse


def _format_supplier_address(supplier: SupplierResponse) -> str | None:
    """Supplier's own address shape (`address`, `city`, `state`,
    `country`) - duplicated field-by-field rather than shared with
    app.modules.purchase.document_builder's own identical helper, since
    cross-importing between business modules for a small helper isn't
    worth the coupling (ARCHITECTURE.md §2)."""
    parts = [supplier.address, supplier.city, supplier.state, supplier.country]
    joined = ", ".join(part for part in parts if part)
    return joined or None


def _additional_charges_section(purchase_order: PurchaseOrderResponse) -> DocumentSection | None:
    """Mirrors app.modules.purchase.document_builder's own
    `_additional_charges_section` exactly - transport_charge/other_charge
    are real, already-computed columns folded into total_amount server-side
    but have no dedicated DocumentTotals slot, so they're shown as a generic
    section only when actually non-zero."""
    lines = []
    if purchase_order.transport_charge:
        lines.append(
            DocumentLine(description="Transport Charge", line_total=purchase_order.transport_charge)
        )
    if purchase_order.other_charge:
        lines.append(
            DocumentLine(description="Other Charge", line_total=purchase_order.other_charge)
        )
    if not lines:
        return None
    return DocumentSection(title="Additional Charges", lines=lines)


def build_purchase_order_document_data(
    purchase_order: PurchaseOrderResponse,
    items: list[PurchaseOrderItemResponse],
    supplier: SupplierResponse,
    *,
    tenant_name: str,
    generated_by: str,
) -> DocumentData:
    """Converts an already-fetched purchase order + items + supplier
    (PurchaseOrderService.get_document_context()) into the generic
    `DocumentData` the Document Engine (Sprint 12 Session 1) consumes.
    Every quantity/rate/tax/total value is copied verbatim from the
    already-authoritative response DTOs - nothing is multiplied, summed, or
    rounded here.
    """
    if purchase_order.po_number is None:
        # Enforced by PurchaseOrderService.get_document_context() before
        # this is ever called - re-checked here only to satisfy mypy's
        # narrowing of `document_number: str` below, not a new business
        # rule.
        raise ValueError("purchase_order.po_number must be set before building its document")

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

    # Deliberately no paid=/balance= - a purchase order is a procurement
    # commitment, not a bill, and must never carry payment/outstanding
    # information (this session's own hard business rule).
    totals = DocumentTotals(
        subtotal=purchase_order.subtotal,
        discount=purchase_order.discount_amount,
        tax=purchase_order.tax_amount,
        rounding=purchase_order.round_off,
        total=purchase_order.total_amount,
    )

    sections = []
    additional_charges = _additional_charges_section(purchase_order)
    if additional_charges is not None:
        sections.append(additional_charges)

    return DocumentData(
        document_type=DocumentType.PURCHASE_ORDER,
        document_number=purchase_order.po_number,
        document_date=purchase_order.order_date,
        title="Purchase Order",
        tenant_name=tenant_name,
        party=party,
        sections=sections,
        line_items=line_items,
        totals=totals,
        notes=purchase_order.remarks,
        metadata={
            "status": purchase_order.status.value,
            # A real date object, not pre-formatted text - the renderer
            # owns display formatting (mirrors how `status` is stored raw
            # and title-cased only at render time).
            "expected_delivery_date": purchase_order.expected_delivery_date,
        },
        generated_at=datetime.now(UTC),
        generated_by=generated_by,
    )


__all__ = ["build_purchase_order_document_data"]
