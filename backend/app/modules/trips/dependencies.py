from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.trips.service import TripService


async def get_trip_service(session: AsyncSession = Depends(get_db)) -> TripService:
    return TripService(session)
