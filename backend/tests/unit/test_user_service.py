import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from app.core.errors import ConflictError
from app.modules.auth.constants import ADMIN_ROLE, SUPER_ADMIN_ROLE, AccountStatus
from app.modules.auth.models import Role, User
from app.modules.users.exceptions import (
    DuplicateUserEmailError,
    DuplicateUsernameError,
    SuperAdminRoleProtectedError,
)
from app.modules.users.schemas import UserListParams
from app.modules.users.service import UserService


class _FakeConstraintCause(Exception):
    """`__cause__` must be a BaseException, so this stands in for the part of
    asyncpg's UniqueViolationError that _translate_integrity_error reads."""

    def __init__(self, constraint_name: str) -> None:
        super().__init__("fake constraint violation")
        self.constraint_name = constraint_name


class _FakeDriverError(Exception):
    """Stands in for asyncpg's UniqueViolationError, chained as __cause__."""

    def __init__(self, constraint_name: str) -> None:
        super().__init__("duplicate key value violates unique constraint")
        self.__cause__ = _FakeConstraintCause(constraint_name)


class _FakeIntegrityError(Exception):
    """Stands in for sqlalchemy.exc.IntegrityError - only `.orig` is read."""

    def __init__(self, constraint_name: str) -> None:
        super().__init__("integrity error")
        self.orig = _FakeDriverError(constraint_name)


class _FakeRepo:
    def __init__(self, rows: list[User], total: int) -> None:
        self.rows = rows
        self.total = total
        self.last_call: dict[str, Any] | None = None

    async def search(self, tenant_id: uuid.UUID, **kwargs: Any) -> tuple[list[User], int]:
        self.last_call = {"tenant_id": tenant_id, **kwargs}
        return self.rows, self.total


def _make_role(name: str) -> Role:
    return Role(id=uuid.uuid4(), tenant_id=uuid.uuid4(), name=name)


def _make_user(*, roles: list[Role] | None = None, **overrides: Any) -> User:
    """A User that satisfies UserResponse validation without touching the DB -
    mirrors test_company_service.py's _make_company."""
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
    user = User(**defaults)
    user.roles = roles or []
    return user


def _service_with_fake_repo(rows: list[User], total: int) -> tuple[UserService, _FakeRepo]:
    service = UserService.__new__(UserService)
    fake_repo = _FakeRepo(rows, total)
    service._repo = fake_repo  # type: ignore[assignment]
    return service, fake_repo


class TestTranslateIntegrityError:
    def test_email_constraint_maps_to_duplicate_email_error(self) -> None:
        exc = _FakeIntegrityError("ix_users_tenant_email")
        result = UserService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert isinstance(result, DuplicateUserEmailError)

    def test_username_constraint_maps_to_duplicate_username_error(self) -> None:
        exc = _FakeIntegrityError("ix_users_tenant_username")
        result = UserService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert isinstance(result, DuplicateUsernameError)

    def test_unknown_constraint_falls_back_to_generic_conflict(self) -> None:
        exc = _FakeIntegrityError("some_other_constraint")
        result = UserService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert type(result) is ConflictError

    def test_missing_orig_falls_back_to_generic_conflict(self) -> None:
        class _BareError(Exception):
            orig = None

        result = UserService._translate_integrity_error(_BareError())  # type: ignore[arg-type]
        assert type(result) is ConflictError


class TestListUsersPaginationMath:
    async def test_first_page_of_several(self) -> None:
        rows = [_make_user() for _ in range(2)]
        service, fake_repo = _service_with_fake_repo(rows, total=5)

        result = await service.list_users(
            tenant_id=uuid.uuid4(), params=UserListParams(page=1, page_size=2)
        )

        assert len(result.data) == 2
        assert result.meta.total_records == 5
        assert result.meta.total_pages == 3
        assert result.meta.has_next is True
        assert result.meta.has_previous is False
        assert fake_repo.last_call is not None

    async def test_last_page_has_no_next(self) -> None:
        rows = [_make_user()]
        service, _ = _service_with_fake_repo(rows, total=5)

        result = await service.list_users(
            tenant_id=uuid.uuid4(), params=UserListParams(page=3, page_size=2)
        )

        assert result.meta.has_next is False
        assert result.meta.has_previous is True

    async def test_empty_result_gives_zero_pages(self) -> None:
        service, _ = _service_with_fake_repo([], total=0)

        result = await service.list_users(
            tenant_id=uuid.uuid4(), params=UserListParams(page=1, page_size=20)
        )

        assert result.data == []
        assert result.meta.total_records == 0
        assert result.meta.total_pages == 0

    async def test_filters_are_forwarded_to_the_repository(self) -> None:
        service, fake_repo = _service_with_fake_repo([], total=0)
        tenant_id = uuid.uuid4()
        role_id = uuid.uuid4()

        await service.list_users(
            tenant_id=tenant_id,
            params=UserListParams(
                q="priya",
                role_id=role_id,
                status=AccountStatus.ACTIVE,
                sort="-full_name",
                page=2,
                page_size=10,
            ),
        )

        assert fake_repo.last_call == {
            "tenant_id": tenant_id,
            "q": "priya",
            "role_id": role_id,
            "status": AccountStatus.ACTIVE,
            "sort": "-full_name",
            "page": 2,
            "page_size": 10,
        }


class TestIsAdministrator:
    """UserService._is_administrator - the "last active administrator"
    guard in set_status treats is_superuser and the admin/super_admin roles
    as equally privileged, since a role holder gets the same _ALL_CODES
    permission set as is_superuser (67c33121fc54's seed data)."""

    def test_superuser_flag_counts_as_administrator(self) -> None:
        assert UserService._is_administrator(_make_user(is_superuser=True)) is True

    def test_admin_role_counts_as_administrator(self) -> None:
        user = _make_user(roles=[_make_role(ADMIN_ROLE)])
        assert UserService._is_administrator(user) is True

    def test_super_admin_role_counts_as_administrator(self) -> None:
        user = _make_user(roles=[_make_role(SUPER_ADMIN_ROLE)])
        assert UserService._is_administrator(user) is True

    def test_other_role_is_not_an_administrator(self) -> None:
        user = _make_user(roles=[_make_role("accountant")])
        assert UserService._is_administrator(user) is False

    def test_no_role_and_not_superuser_is_not_an_administrator(self) -> None:
        assert UserService._is_administrator(_make_user()) is False


class TestGuardSuperAdminAssignment:
    """UserService._guard_super_admin_assignment - only an existing
    superuser may grant the super_admin role to anyone (create or update)."""

    def test_non_superuser_cannot_assign_super_admin_role(self) -> None:
        actor = _make_user(is_superuser=False)
        role = _make_role(SUPER_ADMIN_ROLE)
        with pytest.raises(SuperAdminRoleProtectedError):
            UserService._guard_super_admin_assignment(role, actor)

    def test_superuser_can_assign_super_admin_role(self) -> None:
        actor = _make_user(is_superuser=True)
        UserService._guard_super_admin_assignment(_make_role(SUPER_ADMIN_ROLE), actor)

    def test_non_superuser_can_assign_non_super_admin_roles(self) -> None:
        actor = _make_user(is_superuser=False)
        UserService._guard_super_admin_assignment(_make_role(ADMIN_ROLE), actor)


class TestGuardSuperAdminRevocation:
    """UserService._guard_super_admin_revocation - only an existing
    superuser may change the role of a user who currently holds super_admin."""

    def test_non_superuser_cannot_touch_a_super_admins_role(self) -> None:
        actor = _make_user(is_superuser=False)
        target = _make_user(roles=[_make_role(SUPER_ADMIN_ROLE)])
        with pytest.raises(SuperAdminRoleProtectedError):
            UserService._guard_super_admin_revocation(target, actor)

    def test_superuser_can_touch_a_super_admins_role(self) -> None:
        actor = _make_user(is_superuser=True)
        target = _make_user(roles=[_make_role(SUPER_ADMIN_ROLE)])
        UserService._guard_super_admin_revocation(target, actor)

    def test_non_superuser_can_touch_a_non_super_admins_role(self) -> None:
        actor = _make_user(is_superuser=False)
        target = _make_user(roles=[_make_role(ADMIN_ROLE)])
        UserService._guard_super_admin_revocation(target, actor)
