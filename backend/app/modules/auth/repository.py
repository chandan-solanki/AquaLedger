import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.modules.auth.models import (
    AuditLog,
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    User,
    UserRole,
)


class AuthRepository:
    """All raw queries for the auth module live here - services never build SQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User)
            .where(
                func.lower(User.email) == email.strip().lower(),
                User.deleted_at.is_(None),
            )
            # Sprint 17 Session 2: login needs user.tenant.status. User.tenant
            # is a plain lazy="select" relationship and Base has no AsyncAttrs
            # mixin, so a bare attribute access here would raise
            # MissingGreenlet rather than just costing an extra round trip -
            # eager-loading is not an optimization, it's required correctness.
            .options(joinedload(User.tenant))
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(
            select(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .options(joinedload(User.tenant))  # see get_user_by_email
        )
        return result.scalar_one_or_none()

    async def get_roles_and_permissions(self, user_id: uuid.UUID) -> tuple[list[str], list[str]]:
        role_result = await self._session.execute(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        roles = [row[0] for row in role_result.all()]

        permission_result = await self._session.execute(
            select(Permission.code)
            .distinct()
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == user_id)
        )
        permissions = [row[0] for row in permission_result.all()]
        return roles, permissions

    async def create_refresh_token(
        self,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        family_id: uuid.UUID | None = None,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip=ip,
        )
        if family_id is not None:
            token.family_id = family_id
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_refresh_token_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def mark_revoked(
        self, token: RefreshToken, *, replaced_by: uuid.UUID | None = None
    ) -> None:
        token.revoked_at = datetime.now(UTC)
        if replaced_by is not None:
            token.replaced_by = replaced_by

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )

    async def revoke_all_for_tenant(self, tenant_id: uuid.UUID) -> None:
        """Defense-in-depth for suspending/deactivating a tenant (Sprint 17
        Session 2) - not required for correctness (raise_if_tenant_blocked
        already rejects a suspended tenant's refresh attempts immediately,
        the same way it rejects login/get_current_user), but mirrors
        UserService.set_status's own "revoke on block" convention rather
        than leaving already-issued refresh tokens live and unused."""
        await self._session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id.in_(select(User.id).where(User.tenant_id == tenant_id)),
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )

    async def add_audit_log(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None,
        action: str,
        entity_type: str = "user",
        entity_id: uuid.UUID | None = None,
        changes: dict[str, object] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> None:
        self._session.add(
            AuditLog(
                tenant_id=tenant_id,
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
            )
        )
