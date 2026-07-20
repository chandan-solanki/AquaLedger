from datetime import UTC, datetime

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.constants import AccountStatus
from app.modules.auth.exceptions import AccountDisabledError, AccountLockedError, InvalidTokenError
from app.modules.auth.models import User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import AccessTokenPayload
from app.modules.auth.security import decode_access_token
from app.modules.auth.service import AuthService

# auto_error=False so a missing header raises our own consistent error
# envelope instead of FastAPI's default 403 "Not authenticated".
_bearer_scheme = HTTPBearer(auto_error=False)


def get_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AccessTokenPayload:
    if credentials is None:
        raise InvalidTokenError("Missing bearer token")
    return decode_access_token(credentials.credentials)


async def get_current_user(
    payload: AccessTokenPayload = Depends(get_token_payload),
    session: AsyncSession = Depends(get_db),
) -> User:
    user = await AuthRepository(session).get_user_by_id(payload.sub)
    if user is None:
        raise InvalidTokenError("User no longer exists")

    if user.status == AccountStatus.INACTIVE:
        raise AccountDisabledError("This account has been disabled")
    if user.status == AccountStatus.LOCKED and user.locked_until:
        if user.locked_until > datetime.now(UTC):
            raise AccountLockedError("This account is temporarily locked. Please try again later")

    return user


async def get_auth_service(session: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(session)
