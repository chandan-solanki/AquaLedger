from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.platform_admin.service import TenantService


async def get_tenant_service(session: AsyncSession = Depends(get_db)) -> TenantService:
    return TenantService(session)
