import datetime as dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.numbering_sequences.constants import (
    NUMBERING_DOCUMENT_LABELS,
    NUMBERING_DOCUMENT_PREFIXES,
    SEQUENCE_WIDTH,
    NumberingDocumentType,
)
from app.modules.numbering_sequences.repository import NumberingSequenceRepository
from app.modules.numbering_sequences.schemas import (
    NumberingSequenceResponse,
    NumberingSequenceStatus,
)


# Byte-identical to every one of the six owning modules' own
# `domain/numbering.py` `fiscal_year_for` (Indian GST fiscal year, April 1 -
# March 31) - duplicated here rather than imported from any one of them,
# mirroring the same "mirrors X exactly" precedent those six files already
# use for each other (ARCHITECTURE.md §2: modules never reach into another
# module's internals; pure domain logic is copied, not imported).
def _fiscal_year_for(reference_date: dt.date) -> str:
    start_year = reference_date.year if reference_date.month >= 4 else reference_date.year - 1
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def _format_number(prefix: str, fiscal_year: str, sequence: int) -> str:
    return f"{prefix}/{fiscal_year}/{sequence:0{SEQUENCE_WIDTH}d}"


class NumberingSequenceService:
    """Read-only view over the six independent, already-safe sequence
    allocators (invoices/purchase bills/purchase orders/customer payments/
    supplier payments/delivery challans) for Settings > Numbering
    Sequences. Deliberately has no write path: Sprint 14 Session 2's audit
    found prefix/fiscal-year are hardcoded per module today (not stored
    anywhere per-tenant), so there is nothing safe to let an administrator
    edit yet without inventing new, unrequested configuration - this page
    only surfaces what already exists."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = NumberingSequenceRepository(session)

    async def list_sequences(
        self, tenant_id: uuid.UUID, *, today: dt.date | None = None
    ) -> list[NumberingSequenceResponse]:
        fiscal_year = _fiscal_year_for(today or dt.date.today())
        return [
            await self._build_response(document_type, tenant_id, fiscal_year)
            for document_type in NumberingDocumentType
        ]

    async def _build_response(
        self, document_type: NumberingDocumentType, tenant_id: uuid.UUID, fiscal_year: str
    ) -> NumberingSequenceResponse:
        prefix = NUMBERING_DOCUMENT_PREFIXES[document_type]
        last_number = await self._current_last_number(document_type, tenant_id, prefix, fiscal_year)
        next_number = last_number + 1
        return NumberingSequenceResponse(
            document_type=document_type,
            document_label=NUMBERING_DOCUMENT_LABELS[document_type],
            prefix=prefix,
            fiscal_year=fiscal_year,
            current_number=last_number,
            next_number=next_number,
            next_number_formatted=_format_number(prefix, fiscal_year, next_number),
            number_format=f"{prefix}/{fiscal_year}/{'0' * SEQUENCE_WIDTH}",
            status=(
                NumberingSequenceStatus.ACTIVE
                if last_number > 0
                else NumberingSequenceStatus.NOT_STARTED
            ),
        )

    async def _current_last_number(
        self,
        document_type: NumberingDocumentType,
        tenant_id: uuid.UUID,
        prefix: str,
        fiscal_year: str,
    ) -> int:
        match document_type:
            case NumberingDocumentType.INVOICE:
                invoice_sequence = await self._repo.get_invoice_sequence(
                    tenant_id, prefix, fiscal_year
                )
                return invoice_sequence.last_number if invoice_sequence else 0
            case NumberingDocumentType.PURCHASE_BILL:
                purchase_sequence = await self._repo.get_purchase_sequence(
                    tenant_id, prefix, fiscal_year
                )
                return purchase_sequence.last_number if purchase_sequence else 0
            case NumberingDocumentType.PURCHASE_ORDER:
                purchase_order_sequence = await self._repo.get_purchase_order_sequence(
                    tenant_id, prefix, fiscal_year
                )
                return purchase_order_sequence.last_number if purchase_order_sequence else 0
            case NumberingDocumentType.CUSTOMER_PAYMENT:
                payment_sequence = await self._repo.get_payment_sequence(
                    tenant_id, prefix, fiscal_year
                )
                return payment_sequence.last_number if payment_sequence else 0
            case NumberingDocumentType.SUPPLIER_PAYMENT:
                supplier_payment_sequence = await self._repo.get_supplier_payment_sequence(
                    tenant_id, prefix, fiscal_year
                )
                return supplier_payment_sequence.last_number if supplier_payment_sequence else 0
            case NumberingDocumentType.DELIVERY_CHALLAN:
                delivery_challan_sequence = await self._repo.get_delivery_challan_sequence(
                    tenant_id, prefix, fiscal_year
                )
                return delivery_challan_sequence.last_number if delivery_challan_sequence else 0
