from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.payments.service import PaymentService


async def get_payment_service(session: AsyncSession = Depends(get_db)) -> PaymentService:
    return PaymentService(session)
