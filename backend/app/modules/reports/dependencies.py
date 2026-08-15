from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.reports.service import ReportsService


async def get_reports_service(session: AsyncSession = Depends(get_db)) -> ReportsService:
    return ReportsService(session)
