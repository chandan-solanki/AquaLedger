from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.suppliers.service import SupplierService


async def get_supplier_service(session: AsyncSession = Depends(get_db)) -> SupplierService:
    return SupplierService(session)
