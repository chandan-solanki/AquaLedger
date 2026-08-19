"""Pure DTO -> DocumentData transformation for the supplier payment
receipt PDF (Sprint 12 Session 4). No database access, no financial/
allocation/balance calculation - every value here already came from
SupplierPaymentService.get_document_context(), itself built entirely
from existing SupplierPaymentResponse/SupplierResponse/
SupplierPaymentAllocationDisplay fields. Nothing here is invented:
fields the current SupplierPayment model doesn't carry (a cheque
number, a bank account number, a UTR, a GST breakdown) are simply never
set. Mirrors app.modules.payments.document_builder's own structure
exactly.
"""

from datetime import UTC, datetime
from typing import Any

from app.core.document_engine.document_models import (
    DocumentData,
    DocumentLine,
    DocumentParty,
    DocumentSection,
    DocumentTotals,
)
from app.core.document_engine.document_types import DocumentType
from app.modules.supplier_payments.schemas import SupplierPaymentResponse
from app.modules.supplier_payments.service import SupplierPaymentAllocationDisplay
from app.modules.suppliers.schemas import SupplierResponse


def _format_supplier_address(supplier: SupplierResponse) -> str | None:
    """Mirrors app.modules.purchase.document_builder's own
    `_format_supplier_address` field-by-field - duplicated rather than
    imported, since app.modules.supplier_payments must not depend on
    app.modules.purchase for a small display helper."""
    parts = [supplier.address, supplier.city, supplier.state, supplier.country]
    joined = ", ".join(part for part in parts if part)
    return joined or None


def _allocations_section(
    allocations: list[SupplierPaymentAllocationDisplay],
) -> DocumentSection | None:
    """Renders the "Applied Payments" section only when allocations
    actually exist - an unallocated (or not-yet-allocated) payment never
    fabricates this section."""
    if not allocations:
        return None
    lines = [
        DocumentLine(
            description=allocation.purchase_bill_number, line_total=allocation.allocated_amount
        )
        for allocation in allocations
    ]
    return DocumentSection(title="Applied Payments", lines=lines)


def build_supplier_payment_receipt_document_data(
    supplier_payment: SupplierPaymentResponse,
    supplier: SupplierResponse,
    allocations: list[SupplierPaymentAllocationDisplay],
    *,
    tenant_name: str,
    tenant_details: str | None = None,
    tenant_logo_bytes: bytes | None = None,
    generated_by: str,
) -> DocumentData:
    """Converts an already-fetched supplier payment + supplier +
    resolved allocations (SupplierPaymentService.get_document_context())
    into the generic `DocumentData` the Document Engine (Sprint 12
    Session 1) consumes. The authoritative amount is
    `supplier_payment.amount` - nothing is summed, multiplied, or
    recomputed here.
    """
    if supplier_payment.payment_number is None:
        # Enforced by SupplierPaymentService.get_document_context()
        # before this is ever called - re-checked here only to satisfy
        # mypy's narrowing of `document_number: str` below, not a new
        # business rule.
        raise ValueError("supplier_payment.payment_number must be set before building its document")

    party = DocumentParty(
        id=str(supplier.id),
        name=supplier.name,
        code=supplier.code,
        address=_format_supplier_address(supplier),
        phone=supplier.phone,
        email=supplier.email,
        tax_id=supplier.gstin,
    )

    # No tax/discount/rounding concept on a payment - subtotal and total
    # both legitimately equal the one authoritative amount. `paid`/
    # `balance` are reused here for allocated_amount/unallocated_amount
    # (both always populated on SupplierPayment) - the renderer gives
    # them their own receipt-appropriate labels ("Applied to Purchase
    # Bills"/"Unallocated Amount"), never the generic "Paid"/"Balance
    # Due" wording a purchase bill uses.
    totals = DocumentTotals(
        subtotal=supplier_payment.amount,
        total=supplier_payment.amount,
        paid=supplier_payment.allocated_amount,
        balance=supplier_payment.unallocated_amount,
    )

    metadata: dict[str, Any] = {
        "payment_method": supplier_payment.payment_method.value,
        "status": supplier_payment.status.value,
    }
    if supplier_payment.reference_number:
        metadata["reference_number"] = supplier_payment.reference_number
    if supplier_payment.bank_name:
        metadata["bank_name"] = supplier_payment.bank_name

    sections = []
    allocations_section = _allocations_section(allocations)
    if allocations_section is not None:
        sections.append(allocations_section)

    return DocumentData(
        document_type=DocumentType.SUPPLIER_PAYMENT_RECEIPT,
        document_number=supplier_payment.payment_number,
        document_date=supplier_payment.payment_date,
        title="Supplier Payment Receipt",
        tenant_name=tenant_name,
        tenant_details=tenant_details,
        tenant_logo_bytes=tenant_logo_bytes,
        party=party,
        sections=sections,
        totals=totals,
        notes=supplier_payment.remarks,
        metadata=metadata,
        generated_at=datetime.now(UTC),
        generated_by=generated_by,
    )


__all__ = ["build_supplier_payment_receipt_document_data"]
