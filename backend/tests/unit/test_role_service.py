import uuid
from datetime import UTC, datetime
from typing import Any

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Permission, Role, User
from app.modules.roles.service import RoleService


def _make_role(**overrides: Any) -> Role:
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "name": "accountant",
        "description": "Financial recording and reporting access",
        "is_system": True,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return Role(**defaults)


def _make_permission(code: str, resource: str, action: str) -> Permission:
    return Permission(
        id=uuid.uuid4(), code=code, resource=resource, action=action, description=None
    )


def _make_user(**overrides: Any) -> User:
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "email": "user@fisherp.local",
        "username": "user",
        "password_hash": "hash",
        "full_name": "Test User",
        "status": AccountStatus.ACTIVE,
        "is_superuser": False,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return User(**defaults)


class TestToListItem:
    def test_maps_role_fields_and_counts(self) -> None:
        role = _make_role(name="manager")
        item = RoleService._to_list_item(role, user_count=3, permission_count=24)

        assert item.id == role.id
        assert item.tenant_id == role.tenant_id
        assert item.name == "manager"
        assert item.is_system is True
        assert item.user_count == 3
        assert item.permission_count == 24

    def test_zero_counts_for_an_unused_role(self) -> None:
        role = _make_role(name="operator")
        item = RoleService._to_list_item(role, user_count=0, permission_count=0)

        assert item.user_count == 0
        assert item.permission_count == 0


class TestToDetailResponse:
    """RoleService._to_detail_response - the sort-by-(resource, action)
    behavior is the one piece of real logic in this otherwise-thin mapping
    (the frontend groups by `resource`, per this session's Phase 4 spec, so
    a stable order here keeps that grouping deterministic)."""

    def test_permissions_are_sorted_by_resource_then_action(self) -> None:
        role = _make_role()
        role.permissions = [
            _make_permission("invoice:issue", "invoice", "issue"),
            _make_permission("company:view", "company", "view"),
            _make_permission("invoice:create", "invoice", "create"),
            _make_permission("company:create", "company", "create"),
        ]

        detail = RoleService._to_detail_response(role, users=[])

        assert [p.code for p in detail.permissions] == [
            "company:create",
            "company:view",
            "invoice:create",
            "invoice:issue",
        ]

    def test_empty_permissions_and_users(self) -> None:
        role = _make_role()
        role.permissions = []

        detail = RoleService._to_detail_response(role, users=[])

        assert detail.permissions == []
        assert detail.users == []

    def test_users_are_mapped_without_leaking_password_fields(self) -> None:
        role = _make_role()
        role.permissions = []
        user = _make_user(full_name="Priya Nair", email="priya@fisherp.local")

        detail = RoleService._to_detail_response(role, users=[user])

        assert len(detail.users) == 1
        mapped = detail.users[0]
        assert mapped.id == user.id
        assert mapped.full_name == "Priya Nair"
        assert mapped.email == "priya@fisherp.local"
        assert mapped.status == AccountStatus.ACTIVE
        assert not hasattr(mapped, "password_hash")
