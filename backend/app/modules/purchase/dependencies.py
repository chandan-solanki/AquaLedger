from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.purchase.service import PurchaseService
from app.modules.purchase_orders.service import PurchaseOrderService


async def get_purchase_service(session: AsyncSession = Depends(get_db)) -> PurchaseService:
    return PurchaseService(session, purchase_order_service=PurchaseOrderService(session))
