"""Pure DTO -> DocumentData transformation for the delivery challan PDF
(Sprint 12 Session 16). No database access, no financial/quantity
calculation - every value here already came from
DeliveryChallanService.get_document_context(), itself built entirely from
existing DeliveryChallanResponse/DeliveryChallanItemResponse/InvoiceResponse/
InvoiceItemResponse/FishResponse/CompanyResponse fields plus the delivered-
quantity aggregation DeliveryChallanRepository.sum_delivered_by_invoice_items
already provides. Mirrors app.modules.purchase_orders.document_builder's own
structure exactly, with one deliberate divergence: a delivery challan is a
physical delivery record, never a financial document, so `DocumentTotals` is
never set at all here (not even with paid/balance left None) - there is
nothing to total.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.core.document_engine.document_models import DocumentData, DocumentLine, DocumentParty
from app.core.document_engine.document_types import DocumentType
from app.modules.companies.schemas import CompanyResponse
from app.modules.delivery_challans.schemas import (
    DeliveryChallanItemResponse,
    DeliveryChallanResponse,
)
from app.modules.fish.schemas import FishResponse
from app.modules.invoices.schemas import InvoiceItemResponse, InvoiceResponse


def _format_company_address(company: CompanyResponse) -> str | None:
    """Field-by-field duplicate of app.modules.invoices.document_builder's
    own `_format_company_address` - not imported, since
    app.modules.delivery_challans must not depend on app.modules.invoices'
    document-building internals (ARCHITECTURE.md §2), only its service."""
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


def _line_description(fish: FishResponse, invoice_item: InvoiceItemResponse) -> str:
    """Mirrors app.modules.invoices.document_builder's own
    `_line_description` exactly - a delivery challan item carries no
    description of its own (it references an invoice item, never a fish,
    directly), so the invoiced line's own fish name + optional free-text
    description is what identifies "what was delivered"."""
    if invoice_item.description:
        return f"{fish.name} - {invoice_item.description}"
    return fish.name


def build_delivery_challan_document_data(
    delivery_challan: DeliveryChallanResponse,
    items: list[DeliveryChallanItemResponse],
    invoice: InvoiceResponse,
    invoice_items_by_id: dict[uuid.UUID, InvoiceItemResponse],
    fish_by_id: dict[uuid.UUID, FishResponse],
    previously_delivered_by_item_id: dict[uuid.UUID, Decimal],
    company: CompanyResponse,
    *,
    tenant_name: str,
    generated_by: str,
) -> DocumentData:
    """Converts an already-fetched delivery challan + items + linked
    invoice + billed company (DeliveryChallanService.get_document_context())
    into the generic `DocumentData` the Document Engine (Sprint 12 Session 1)
    consumes. Every quantity value is copied verbatim from the already-
    authoritative response DTOs or the already-computed
    `previously_delivered_by_item_id` map - nothing is summed, subtracted,
    or re-validated here.

    Hard business rule (this session's own): a delivery challan is a
    physical delivery record, never a financial document. This function
    never sets `DocumentTotals` (there is no subtotal/tax/total to show),
    and `DocumentLine.unit_price`/`tax_rate`/`tax_amount` are never set
    either - only `description`/`quantity`/`unit` carry real information;
    `line_total` is populated with the line's own delivered quantity purely
    to satisfy `DocumentLine`'s required field (never rendered as a money
    figure by DeliveryChallanDocumentRenderer, which has no "Amount" column
    at all). "Invoiced Quantity"/"Previously Delivered Quantity" - the two
    figures this document's own item table needs beyond what `DocumentLine`
    has dedicated fields for - travel in `DocumentLine.metadata`, the
    generic per-line scratch space the engine already provides, rather than
    extending `DocumentLine` itself.
    """
    if delivery_challan.challan_number is None:
        # Enforced by DeliveryChallanService.get_document_context() before
        # this is ever called - re-checked here only to satisfy mypy's
        # narrowing of `document_number: str` below, not a new business
        # rule.
        raise ValueError("delivery_challan.challan_number must be set before building its document")

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
            description=_line_description(
                fish_by_id[invoice_items_by_id[item.invoice_item_id].fish_id],
                invoice_items_by_id[item.invoice_item_id],
            ),
            quantity=item.quantity,
            unit=item.unit,
            line_total=item.quantity,
            metadata={
                "invoiced_quantity": invoice_items_by_id[item.invoice_item_id].quantity,
                "previously_delivered_quantity": previously_delivered_by_item_id[item.id],
            },
        )
        for item in items
    ]

    return DocumentData(
        document_type=DocumentType.DELIVERY_CHALLAN,
        document_number=delivery_challan.challan_number,
        document_date=delivery_challan.challan_date,
        title="Delivery Challan",
        tenant_name=tenant_name,
        party=party,
        line_items=line_items,
        totals=None,
        notes=delivery_challan.remarks,
        metadata={
            "status": delivery_challan.status.value,
            "invoice_number": invoice.invoice_number,
            # Real date/datetime objects, not pre-formatted text - the
            # renderer owns display formatting.
            "invoice_date": invoice.invoice_date,
            "dispatched_at": delivery_challan.dispatched_at,
            "delivered_at": delivery_challan.delivered_at,
        },
        generated_at=datetime.now(UTC),
        generated_by=generated_by,
    )


__all__ = ["build_delivery_challan_document_data"]
