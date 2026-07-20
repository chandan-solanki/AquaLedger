from collections.abc import Awaitable, Callable

from fastapi import Depends

from app.core.errors import AuthorizationError
from app.modules.auth.dependencies import get_current_user, get_token_payload
from app.modules.auth.models import User
from app.modules.auth.schemas import AccessTokenPayload


def require_permission(code: str) -> Callable[..., Awaitable[None]]:
    """Route dependency: 403s unless the caller has `code`.

    Reads permissions from the JWT claims, not a fresh DB query - the
    documented trade-off in ARCHITECTURE §8.1 (fast per-request checks;
    a revoked permission takes up to access-token-expiry to bite). A
    superuser bypasses this regardless of the token's permission list, so a
    permission introduced by a future module doesn't silently lock out the
    seeded super admin until its role is updated.
    """

    async def _check(
        current_user: User = Depends(get_current_user),
        payload: AccessTokenPayload = Depends(get_token_payload),
    ) -> None:
        if current_user.is_superuser:
            return
        if code not in payload.permissions:
            raise AuthorizationError(f"Missing required permission: {code}")

    return _check


def require_role(name: str) -> Callable[..., Awaitable[None]]:
    """Route dependency: 403s unless the caller holds role `name`."""

    async def _check(
        current_user: User = Depends(get_current_user),
        payload: AccessTokenPayload = Depends(get_token_payload),
    ) -> None:
        if current_user.is_superuser:
            return
        if name not in payload.roles:
            raise AuthorizationError(f"Missing required role: {name}")

    return _check
