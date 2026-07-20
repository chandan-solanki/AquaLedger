import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import RateLimitError, ValidationError
from app.modules.auth.constants import AccountStatus
from app.modules.auth.exceptions import (
    AccountDisabledError,
    AccountLockedError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.modules.auth.models import User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import TokenResponse, UserProfileResponse
from app.modules.auth.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    login_rate_limiter,
    password_policy_violations,
    verify_password,
)

settings = get_settings()

# Computed once so an unknown-email login pays the same Argon2 cost as a real
# verification attempt - this is what makes the response time-invariant with
# respect to whether the email exists (anti user-enumeration, ARCHITECTURE §8.2).
_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


@dataclass(frozen=True, slots=True)
class RequestContext:
    ip: str | None
    user_agent: str | None
    request_id: str | None


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AuthRepository(session)

    async def login(self, email: str, password: str, ctx: RequestContext) -> TokenResponse:
        rate_limit_key = f"{email.strip().lower()}:{ctx.ip or 'unknown'}"
        if not login_rate_limiter.check_and_record(rate_limit_key):
            raise RateLimitError("Too many login attempts. Please try again later.")

        user = await self._repo.get_user_by_email(email)
        if user is None:
            verify_password(password, _DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError("Invalid email or password")

        now = datetime.now(UTC)
        self._raise_if_blocked(user, now)

        if not verify_password(password, user.password_hash):
            self._record_failed_login(user, now)
            await self._repo.add_audit_log(
                tenant_id=user.tenant_id,
                user_id=user.id,
                action="login_failed",
                entity_id=user.id,
                ip_address=ctx.ip,
                user_agent=ctx.user_agent,
                request_id=ctx.request_id,
            )
            await self._session.commit()  # single commit for this whole request
            raise InvalidCredentialsError("Invalid email or password")

        self._record_successful_login(user, now)
        roles, permissions = await self._repo.get_roles_and_permissions(user.id)
        refresh_token_plain = generate_refresh_token()
        await self._repo.create_refresh_token(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token_plain),
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
            user_agent=ctx.user_agent,
            ip=ctx.ip,
        )
        await self._repo.add_audit_log(
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="login_success",
            entity_id=user.id,
            ip_address=ctx.ip,
            user_agent=ctx.user_agent,
            request_id=ctx.request_id,
        )
        await self._session.commit()  # single commit for this whole request

        return self._build_token_response(user, roles, permissions, refresh_token_plain)

    async def refresh(self, refresh_token_plain: str, ctx: RequestContext) -> TokenResponse:
        token_hash = hash_refresh_token(refresh_token_plain)
        token_row = await self._repo.get_refresh_token_by_hash(token_hash)
        if token_row is None:
            raise InvalidTokenError("Invalid refresh token")

        if token_row.revoked_at is not None:
            # A revoked token being replayed means it was stolen/leaked - the
            # entire family (every descendant issued via rotation) is burned.
            await self._repo.revoke_family(token_row.family_id)
            await self._session.commit()
            raise InvalidTokenError("Refresh token reuse detected; all sessions revoked")

        now = datetime.now(UTC)
        if token_row.expires_at <= now:
            raise InvalidTokenError("Refresh token has expired")

        user = await self._repo.get_user_by_id(token_row.user_id)
        if user is None:
            raise InvalidTokenError("Invalid refresh token")
        self._raise_if_blocked(user, now)

        roles, permissions = await self._repo.get_roles_and_permissions(user.id)
        new_refresh_plain = generate_refresh_token()
        new_row = await self._repo.create_refresh_token(
            user_id=user.id,
            token_hash=hash_refresh_token(new_refresh_plain),
            family_id=token_row.family_id,
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
            user_agent=ctx.user_agent,
            ip=ctx.ip,
        )
        await self._repo.mark_revoked(token_row, replaced_by=new_row.id)
        await self._session.commit()  # single commit for this whole request

        return self._build_token_response(user, roles, permissions, new_refresh_plain)

    async def logout(self, user: User, refresh_token_plain: str, ctx: RequestContext) -> None:
        token_hash = hash_refresh_token(refresh_token_plain)
        token_row = await self._repo.get_refresh_token_by_hash(token_hash)
        if token_row is not None and token_row.user_id == user.id and token_row.revoked_at is None:
            await self._repo.mark_revoked(token_row)
        await self._repo.add_audit_log(
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="logout",
            entity_id=user.id,
            ip_address=ctx.ip,
            user_agent=ctx.user_agent,
            request_id=ctx.request_id,
        )
        await self._session.commit()

    async def get_profile(self, user: User) -> UserProfileResponse:
        roles, permissions = await self._repo.get_roles_and_permissions(user.id)
        return self._to_profile(user, roles, permissions)

    async def change_password(
        self, user: User, current_password: str, new_password: str, ctx: RequestContext
    ) -> None:
        if not verify_password(current_password, user.password_hash):
            raise InvalidCredentialsError("Current password is incorrect")

        violations = password_policy_violations(new_password)
        if violations:
            raise ValidationError(
                "Password does not meet policy requirements",
                field_errors={"new_password": violations},
            )

        user.password_hash = hash_password(new_password)
        user.password_changed_at = datetime.now(UTC)
        if user.status == AccountStatus.PASSWORD_EXPIRED:
            user.status = AccountStatus.ACTIVE

        # A password change invalidates every existing session - a stolen
        # refresh token should not survive its owner changing their password.
        await self._repo.revoke_all_for_user(user.id)
        await self._repo.add_audit_log(
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="password_changed",
            entity_id=user.id,
            ip_address=ctx.ip,
            user_agent=ctx.user_agent,
            request_id=ctx.request_id,
        )
        await self._session.commit()

    def _raise_if_blocked(self, user: User, now: datetime) -> None:
        if user.status == AccountStatus.INACTIVE:
            raise AccountDisabledError("This account has been disabled")
        if user.status == AccountStatus.LOCKED and user.locked_until and user.locked_until > now:
            raise AccountLockedError("This account is temporarily locked. Please try again later")

    def _record_failed_login(self, user: User, now: datetime) -> None:
        """Mutates the already-loaded user; caller commits once, alongside its audit log."""
        user.failed_login_count += 1
        if user.failed_login_count >= settings.account_lockout_threshold:
            user.status = AccountStatus.LOCKED
            user.locked_until = now + timedelta(minutes=settings.account_lockout_minutes)

    def _record_successful_login(self, user: User, now: datetime) -> None:
        # A lock whose window has already elapsed is stale - clear it rather
        # than requiring a separate maintenance job to do so.
        if user.status == AccountStatus.LOCKED and (
            user.locked_until is None or user.locked_until <= now
        ):
            user.status = AccountStatus.ACTIVE
            user.locked_until = None
        user.failed_login_count = 0
        user.last_login_at = now

    def _build_token_response(
        self, user: User, roles: list[str], permissions: list[str], refresh_token_plain: str
    ) -> TokenResponse:
        access_token = create_access_token(
            subject=user.id, tenant_id=user.tenant_id, roles=roles, permissions=permissions
        )
        must_change_password = (
            user.status == AccountStatus.PASSWORD_EXPIRED or user.password_changed_at is None
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_plain,
            expires_in=settings.access_token_expire_minutes * 60,
            must_change_password=must_change_password,
            user=self._to_profile(user, roles, permissions),
        )

    @staticmethod
    def _to_profile(user: User, roles: list[str], permissions: list[str]) -> UserProfileResponse:
        return UserProfileResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            phone=user.phone,
            status=AccountStatus(user.status),
            is_superuser=user.is_superuser,
            last_login_at=user.last_login_at,
            roles=roles,
            permissions=permissions,
        )
