"""Pure DTO -> DocumentData transformation for the invoice PDF (Sprint 12
Session 2). No database access, no financial/tax/balance calculation -
every value here already came from InvoiceService.get_document_context(),
itself built entirely from existing InvoiceResponse/InvoiceItemResponse/
CompanyResponse/FishResponse fields. Nothing here is invented: fields the
current Invoice model doesn't carry (payment terms, shipping/billing
address split, a QR code, a digital signature, an HSN/tax breakdown table)
are simply never set, per this session's own "do not invent business
fields" rule.
"""

import uuid
from datetime import UTC, datetime

from app.core.document_engine.document_models import (
    DocumentData,
    DocumentLine,
    DocumentParty,
    DocumentSection,
    DocumentTotals,
)
from app.core.document_engine.document_types import DocumentType
from app.modules.companies.schemas import CompanyResponse
from app.modules.fish.schemas import FishResponse
from app.modules.invoices.schemas import InvoiceItemResponse, InvoiceResponse


def _format_company_address(company: CompanyResponse) -> str | None:
    """Mirrors app.modules.reports.statement_builder's own
    `_format_company_address` field-by-field - duplicated rather than
    imported, since app.modules.invoices must not depend on
    app.modules.reports (ARCHITECTURE.md §41: reports/statements and
    business documents are deliberately separate concerns) and the
    logic is small enough that sharing it isn't worth a cross-module
    dependency."""
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


def _line_description(fish: FishResponse, item: InvoiceItemResponse) -> str:
    if item.description:
        return f"{fish.name} - {item.description}"
    return fish.name


def _additional_charges_section(invoice: InvoiceResponse) -> DocumentSection | None:
    """`transport_charge`/`other_charge` are real, already-computed
    invoice columns folded into `total_amount` server-side
    (ARCHITECTURE.md §13.4) but have no dedicated `DocumentTotals` slot
    (Session 1's model is fixed, not extended here) - shown as a generic
    section only when a charge actually carries a non-zero value, never
    as an empty placeholder line."""
    lines = []
    if invoice.transport_charge:
        lines.append(
            DocumentLine(description="Transport Charge", line_total=invoice.transport_charge)
        )
    if invoice.other_charge:
        lines.append(DocumentLine(description="Other Charge", line_total=invoice.other_charge))
    if not lines:
        return None
    return DocumentSection(title="Additional Charges", lines=lines)


def build_invoice_document_data(
    invoice: InvoiceResponse,
    items: list[InvoiceItemResponse],
    company: CompanyResponse,
    fish_by_id: dict[uuid.UUID, FishResponse],
    *,
    tenant_name: str,
    generated_by: str,
) -> DocumentData:
    """Converts an already-fetched invoice + items + billed company +
    fish map (InvoiceService.get_document_context()) into the generic
    `DocumentData` the Document Engine (Sprint 12 Session 1) consumes.
    Every quantity/rate/tax/total value is copied verbatim from the
    already-authoritative response DTOs - nothing is multiplied, summed,
    or rounded here.
    """
    if invoice.invoice_number is None:
        # Enforced by InvoiceService.get_document_context() before this
        # is ever called - re-checked here only to satisfy mypy's
        # narrowing of `document_number: str` below, not a new business
        # rule.
        raise ValueError("invoice.invoice_number must be set before building its document")

    party = DocumentParty(
        id=str(company.id),
        name=company.name,
        code=company.code,
        address=_format_company_address(company),
        phone=company.phone,
        email=company.email,
        tax_id=company.gstin,
    )

    line_items = [
        DocumentLine(
            description=_line_description(fish_by_id[item.fish_id], item),
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
        subtotal=invoice.subtotal,
        discount=invoice.discount_amount,
        tax=invoice.tax_amount,
        rounding=invoice.round_off,
        total=invoice.total_amount,
        paid=invoice.paid_amount,
        balance=invoice.balance_amount,
    )

    sections = []
    additional_charges = _additional_charges_section(invoice)
    if additional_charges is not None:
        sections.append(additional_charges)

    return DocumentData(
        document_type=DocumentType.INVOICE,
        document_number=invoice.invoice_number,
        document_date=invoice.invoice_date,
        title="Invoice",
        tenant_name=tenant_name,
        party=party,
        sections=sections,
        line_items=line_items,
        totals=totals,
        notes=invoice.remarks,
        metadata={"status": invoice.status.value},
        generated_at=datetime.now(UTC),
        generated_by=generated_by,
    )


__all__ = ["build_invoice_document_data"]
