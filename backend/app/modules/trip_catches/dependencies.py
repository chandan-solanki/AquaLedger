from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.trip_catches.service import TripCatchService


async def get_trip_catch_service(session: AsyncSession = Depends(get_db)) -> TripCatchService:
    return TripCatchService(session)
