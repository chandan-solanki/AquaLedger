import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Reads each owning module's own `*Sequence` ORM model directly - the same
# precedent as `app.modules.dashboard.repository` reading `Invoice`/
# `PurchaseBill`/etc. models straight from their owning modules for
# reporting (ARCHITECTURE.md §2 only forbids reaching into another
# module's *internals* - private domain helpers/logic - not its plain
# persistence models). Every query here is a plain `SELECT`, never `FOR
# UPDATE`: the actual concurrency-safe allocation lock stays exactly where
# it is, inside each module's own service (ARCHITECTURE.md §13.1) - this
# read-only aggregation never participates in number allocation.
from app.modules.delivery_challans.models import DeliveryChallanSequence
from app.modules.invoices.models import InvoiceSequence
from app.modules.payments.models import PaymentSequence
from app.modules.purchase.models import PurchaseSequence
from app.modules.purchase_orders.models import PurchaseOrderSequence
from app.modules.supplier_payments.models import SupplierPaymentSequence


class NumberingSequenceRepository:
    """Read-only cross-module aggregation for Settings > Numbering
    Sequences - one lock-free lookup per document type's sequence table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_invoice_sequence(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> InvoiceSequence | None:
        result = await self._session.execute(
            select(InvoiceSequence).where(
                InvoiceSequence.tenant_id == tenant_id,
                InvoiceSequence.prefix == prefix,
                InvoiceSequence.fiscal_year == fiscal_year,
            )
        )
        return result.scalar_one_or_none()

    async def get_purchase_sequence(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> PurchaseSequence | None:
        result = await self._session.execute(
            select(PurchaseSequence).where(
                PurchaseSequence.tenant_id == tenant_id,
                PurchaseSequence.prefix == prefix,
                PurchaseSequence.fiscal_year == fiscal_year,
            )
        )
        return result.scalar_one_or_none()

    async def get_purchase_order_sequence(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> PurchaseOrderSequence | None:
        result = await self._session.execute(
            select(PurchaseOrderSequence).where(
                PurchaseOrderSequence.tenant_id == tenant_id,
                PurchaseOrderSequence.prefix == prefix,
                PurchaseOrderSequence.fiscal_year == fiscal_year,
            )
        )
        return result.scalar_one_or_none()

    async def get_payment_sequence(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> PaymentSequence | None:
        result = await self._session.execute(
            select(PaymentSequence).where(
                PaymentSequence.tenant_id == tenant_id,
                PaymentSequence.prefix == prefix,
                PaymentSequence.fiscal_year == fiscal_year,
            )
        )
        return result.scalar_one_or_none()

    async def get_supplier_payment_sequence(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> SupplierPaymentSequence | None:
        result = await self._session.execute(
            select(SupplierPaymentSequence).where(
                SupplierPaymentSequence.tenant_id == tenant_id,
                SupplierPaymentSequence.prefix == prefix,
                SupplierPaymentSequence.fiscal_year == fiscal_year,
            )
        )
        return result.scalar_one_or_none()

    async def get_delivery_challan_sequence(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> DeliveryChallanSequence | None:
        result = await self._session.execute(
            select(DeliveryChallanSequence).where(
                DeliveryChallanSequence.tenant_id == tenant_id,
                DeliveryChallanSequence.prefix == prefix,
                DeliveryChallanSequence.fiscal_year == fiscal_year,
            )
        )
        return result.scalar_one_or_none()
