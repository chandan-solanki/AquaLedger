from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.delivery_challans.service import DeliveryChallanService
from app.modules.invoices.service import InvoiceService


async def get_delivery_challan_service(
    session: AsyncSession = Depends(get_db),
) -> DeliveryChallanService:
    return DeliveryChallanService(session, invoice_service=InvoiceService(session))
