from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.company_profile.service import CompanyProfileService


async def get_company_profile_service(
    session: AsyncSession = Depends(get_db),
) -> CompanyProfileService:
    return CompanyProfileService(session)
