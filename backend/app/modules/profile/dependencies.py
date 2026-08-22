from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.service import AuthService
from app.modules.profile.service import ProfileService


async def get_profile_service(session: AsyncSession = Depends(get_db)) -> ProfileService:
    return ProfileService(session, AuthService(session))
