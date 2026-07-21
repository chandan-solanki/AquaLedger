from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.fish.service import FishService


async def get_fish_service(session: AsyncSession = Depends(get_db)) -> FishService:
    return FishService(session)
