"""Pure DTO -> DocumentData transformation for the customer payment
receipt PDF (Sprint 12 Session 4). No database access, no financial/
allocation/balance calculation - every value here already came from
PaymentService.get_document_context(), itself built entirely from
existing PaymentResponse/CompanyResponse/PaymentAllocationDisplay
fields. Nothing here is invented: fields the current Payment model
doesn't carry (a cheque number, a bank account number, a UTR, a GST
breakdown) are simply never set, per this session's own "do not invent
business fields" rule.
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
from app.modules.companies.schemas import CompanyResponse
from app.modules.payments.schemas import PaymentResponse
from app.modules.payments.service import PaymentAllocationDisplay


def _format_company_address(company: CompanyResponse) -> str | None:
    """Mirrors app.modules.invoices.document_builder's own
    `_format_company_address` field-by-field - duplicated rather than
    imported, since app.modules.payments must not depend on
    app.modules.invoices for a small display helper (ARCHITECTURE.md
    §2 - modules talk to each other only through service.py, and this
    isn't even a service call)."""
    state_and_pincode = " ".join(part for part in (company.state, company.pincode) if part)
    parts = [
        company.address_line1,
        company.address_line2,
        company.city,
        state_and_pincode,
        company.country,
    ]
    joined = ", ".join(part for part in parts if part)
    return joined or None


def _allocations_section(allocations: list[PaymentAllocationDisplay]) -> DocumentSection | None:
    """Renders the "Applied Payments" section only when allocations
    actually exist - an unallocated (or not-yet-allocated) payment never
    fabricates this section."""
    if not allocations:
        return None
    lines = [
        DocumentLine(description=allocation.invoice_number, line_total=allocation.allocated_amount)
        for allocation in allocations
    ]
    return DocumentSection(title="Applied Payments", lines=lines)


def build_customer_payment_receipt_document_data(
    payment: PaymentResponse,
    company: CompanyResponse,
    allocations: list[PaymentAllocationDisplay],
    *,
    tenant_name: str,
    generated_by: str,
) -> DocumentData:
    """Converts an already-fetched payment + billed company + resolved
    allocations (PaymentService.get_document_context()) into the
    generic `DocumentData` the Document Engine (Sprint 12 Session 1)
    consumes. The authoritative amount is `payment.amount` - nothing is
    summed, multiplied, or recomputed here.
    """
    if payment.payment_number is None:
        # Enforced by PaymentService.get_document_context() before this
        # is ever called - re-checked here only to satisfy mypy's
        # narrowing of `document_number: str` below, not a new business
        # rule.
        raise ValueError("payment.payment_number must be set before building its document")

    party = DocumentParty(
        id=str(company.id),
        name=company.name,
        code=company.code,
        address=_format_company_address(company),
        phone=company.phone,
        email=company.email,
        tax_id=company.gstin,
    )

    # No tax/discount/rounding concept on a payment - subtotal and total
    # both legitimately equal the one authoritative amount. `paid`/
    # `balance` are reused here for allocated_amount/unallocated_amount
    # (both always populated on Payment) - the renderer gives them their
    # own receipt-appropriate labels ("Applied to Invoices"/"Unallocated
    # Amount"), never the generic "Paid"/"Balance Due" wording an
    # invoice uses.
    totals = DocumentTotals(
        subtotal=payment.amount,
        total=payment.amount,
        paid=payment.allocated_amount,
        balance=payment.unallocated_amount,
    )

    metadata: dict[str, Any] = {
        "payment_method": payment.payment_method.value,
        "status": payment.status.value,
    }
    if payment.reference_number:
        metadata["reference_number"] = payment.reference_number
    if payment.bank_name:
        metadata["bank_name"] = payment.bank_name

    sections = []
    allocations_section = _allocations_section(allocations)
    if allocations_section is not None:
        sections.append(allocations_section)

    return DocumentData(
        document_type=DocumentType.CUSTOMER_PAYMENT_RECEIPT,
        document_number=payment.payment_number,
        document_date=payment.payment_date,
        title="Customer Payment Receipt",
        tenant_name=tenant_name,
        party=party,
        sections=sections,
        totals=totals,
        notes=payment.remarks,
        metadata=metadata,
        generated_at=datetime.now(UTC),
        generated_by=generated_by,
    )


__all__ = ["build_customer_payment_receipt_document_data"]
