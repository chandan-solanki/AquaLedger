import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.models import Permission, Role, RolePermission, User, UserRole


class RoleRepository:
    """All raw queries for the roles module live here - services never
    build SQL. Reads only: this module never writes to roles, permissions,
    role_permissions or user_roles (see router.py's module docstring)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_roles_with_counts(self, tenant_id: uuid.UUID) -> list[tuple[Role, int, int]]:
        """Every role for this tenant plus its user/permission counts, in one
        query via correlated scalar subqueries - not N+1 (one query per role
        would be five extra round trips for the seeded set, more for a
        tenant with custom roles)."""
        user_count = (
            select(func.count(UserRole.user_id))
            .join(User, User.id == UserRole.user_id)
            .where(UserRole.role_id == Role.id, User.deleted_at.is_(None))
            .correlate(Role)
            .scalar_subquery()
        )
        permission_count = (
            select(func.count(RolePermission.permission_id))
            .where(RolePermission.role_id == Role.id)
            .correlate(Role)
            .scalar_subquery()
        )
        result = await self._session.execute(
            select(Role, user_count.label("user_count"), permission_count.label("permission_count"))
            .where(Role.tenant_id == tenant_id)
            .order_by(Role.name)
        )
        return [(row.Role, row.user_count, row.permission_count) for row in result.all()]

    async def get_role_by_id(self, role_id: uuid.UUID, tenant_id: uuid.UUID) -> Role | None:
        result = await self._session.execute(
            select(Role)
            .where(Role.id == role_id, Role.tenant_id == tenant_id)
            .options(selectinload(Role.permissions))
        )
        return result.scalar_one_or_none()

    async def list_users_for_role(self, role_id: uuid.UUID, tenant_id: uuid.UUID) -> list[User]:
        result = await self._session.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .where(
                UserRole.role_id == role_id,
                User.tenant_id == tenant_id,
                User.deleted_at.is_(None),
            )
            .order_by(User.full_name)
        )
        return list(result.scalars().all())

    async def list_permissions(self) -> list[Permission]:
        """Global reference data (Permission is not tenant-scoped) - same
        result for every tenant."""
        result = await self._session.execute(
            select(Permission).order_by(Permission.resource, Permission.action)
        )
        return list(result.scalars().all())
