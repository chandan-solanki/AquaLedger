from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.roles.service import RoleService


async def get_role_service(session: AsyncSession = Depends(get_db)) -> RoleService:
    return RoleService(session)
