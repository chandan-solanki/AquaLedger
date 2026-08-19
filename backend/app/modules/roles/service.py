import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Permission, Role, User
from app.modules.roles.repository import RoleRepository
from app.modules.roles.schemas import (
    PermissionSummary,
    RoleDetailResponse,
    RoleListItem,
    RoleUserSummary,
)
from app.modules.users.exceptions import RoleNotFoundError


class RoleService:
    """Read-only by design - see router.py's module docstring for why this
    module has no permission-assignment mutation endpoint yet."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = RoleRepository(session)

    async def list_roles(self, *, tenant_id: uuid.UUID) -> list[RoleListItem]:
        rows = await self._repo.list_roles_with_counts(tenant_id)
        return [
            self._to_list_item(role, user_count, permission_count)
            for role, user_count, permission_count in rows
        ]

    async def get_role_detail(
        self, role_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> RoleDetailResponse:
        role = await self._get_or_raise(role_id, tenant_id)
        users = await self._repo.list_users_for_role(role_id, tenant_id)
        return self._to_detail_response(role, users)

    async def list_permissions(self) -> list[PermissionSummary]:
        permissions = await self._repo.list_permissions()
        return [PermissionSummary.model_validate(permission) for permission in permissions]

    async def _get_or_raise(self, role_id: uuid.UUID, tenant_id: uuid.UUID) -> Role:
        role = await self._repo.get_role_by_id(role_id, tenant_id)
        if role is None:
            raise RoleNotFoundError("Role not found")
        return role

    @staticmethod
    def _to_list_item(role: Role, user_count: int, permission_count: int) -> RoleListItem:
        return RoleListItem(
            id=role.id,
            tenant_id=role.tenant_id,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            user_count=user_count,
            permission_count=permission_count,
            created_at=role.created_at,
            updated_at=role.updated_at,
        )

    @staticmethod
    def _to_detail_response(role: Role, users: list[User]) -> RoleDetailResponse:
        sorted_permissions: list[Permission] = sorted(
            role.permissions, key=lambda p: (p.resource, p.action)
        )
        return RoleDetailResponse(
            id=role.id,
            tenant_id=role.tenant_id,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            permissions=[PermissionSummary.model_validate(p) for p in sorted_permissions],
            users=[RoleUserSummary.model_validate(u) for u in users],
            created_at=role.created_at,
            updated_at=role.updated_at,
        )
