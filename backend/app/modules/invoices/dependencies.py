from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.invoices.service import InvoiceService


async def get_invoice_service(session: AsyncSession = Depends(get_db)) -> InvoiceService:
    return InvoiceService(session)
