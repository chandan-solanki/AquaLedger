from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.boats.service import BoatService


async def get_boat_service(session: AsyncSession = Depends(get_db)) -> BoatService:
    return BoatService(session)
