from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.companies.service import CompanyService


async def get_company_service(session: AsyncSession = Depends(get_db)) -> CompanyService:
    return CompanyService(session)
