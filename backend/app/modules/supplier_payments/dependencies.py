from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.supplier_payments.service import SupplierPaymentService


async def get_supplier_payment_service(
    session: AsyncSession = Depends(get_db),
) -> SupplierPaymentService:
    return SupplierPaymentService(session)
