from fastapi import APIRouter, Depends, Request, status

from app.common.schemas import ErrorResponse
from app.modules.auth.dependencies import get_auth_service, get_current_user
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserProfileResponse,
)
from app.modules.auth.service import AuthService, RequestContext

router = APIRouter(prefix="/auth", tags=["auth"])

_AUTH_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Invalid credentials or token"},
}


def _build_context(request: Request) -> RequestContext:
    return RequestContext(
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in with email and password",
    description=(
        "Returns an access token (JWT) and a refresh token. `must_change_password` "
        "is true when the account has never had its password changed (as with the "
        "seeded super admin) - prompt for change-password before anything else. "
        "Rate-limited per email+IP; the account itself also auto-locks after "
        "repeated failed attempts, independent of the rate limit."
    ),
    responses={
        **_AUTH_ERROR_RESPONSES,
        423: {"model": ErrorResponse, "description": "Account locked or disabled"},
        429: {"model": ErrorResponse, "description": "Too many login attempts"},
    },
)
async def login(
    payload: LoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return await service.login(payload.email, payload.password, _build_context(request))


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange a refresh token for a new access/refresh token pair",
    description=(
        "Rotates the refresh token: the one presented here is revoked and a new "
        "one is issued in its place. Presenting an already-rotated (revoked) "
        "token is treated as theft/reuse and immediately revokes every token "
        "descended from the same original login - all of that session's devices "
        "are logged out."
    ),
    responses=_AUTH_ERROR_RESPONSES,
)
async def refresh(
    payload: RefreshTokenRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return await service.refresh(payload.refresh_token, _build_context(request))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a refresh token",
    description=(
        "Revokes the specific refresh token supplied - other active sessions for "
        "this user are unaffected. Idempotent: revoking an already-revoked or "
        "unknown token still returns 204."
    ),
    responses=_AUTH_ERROR_RESPONSES,
)
async def logout(
    payload: RefreshTokenRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> None:
    await service.logout(current_user, payload.refresh_token, _build_context(request))


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get the current authenticated user",
    description=(
        "Roles/permissions reflect what's stored now (a fresh query), not what "
        "was embedded in the access token at login time - use this endpoint if "
        "you need the current, not-yet-15-minutes-stale, permission set."
    ),
    responses=_AUTH_ERROR_RESPONSES,
)
async def get_me(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> UserProfileResponse:
    return await service.get_profile(current_user)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change the current user's password",
    description=(
        "New password must satisfy the configured policy (min length, upper/"
        "lower/digit/special character). On success, every refresh token for "
        "this user is revoked - other devices/sessions must log in again."
    ),
    responses={
        **_AUTH_ERROR_RESPONSES,
        422: {"model": ErrorResponse, "description": "New password fails the password policy"},
    },
)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> None:
    await service.change_password(
        current_user, payload.current_password, payload.new_password, _build_context(request)
    )
