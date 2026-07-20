import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import AuditLog, Tenant, User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.security import hash_password, hash_refresh_token


@pytest.fixture
async def repo(db_session: AsyncSession) -> AuthRepository:
    return AuthRepository(db_session)


async def _make_user(db_session: AsyncSession, **overrides: object) -> User:
    tenant = (await db_session.execute(select(Tenant))).scalars().first()
    assert tenant is not None
    defaults: dict[str, object] = {
        "tenant_id": tenant.id,
        "email": "repo-test@fisherp.local",
        "username": "repo-test",
        "password_hash": hash_password("Whatever@123"),
        "full_name": "Repo Test User",
        "status": AccountStatus.ACTIVE,
        "is_superuser": False,
    }
    defaults.update(overrides)
    user = User(**defaults)
    db_session.add(user)
    await db_session.commit()
    return user


class TestGetUserByEmail:
    async def test_finds_user_case_insensitively(
        self, repo: AuthRepository, db_session: AsyncSession
    ) -> None:
        await _make_user(db_session, email="Mixed-Case@Fisherp.Local")
        found = await repo.get_user_by_email("mixed-case@fisherp.local")
        assert found is not None
        assert found.email == "Mixed-Case@Fisherp.Local"

    async def test_returns_none_for_unknown_email(self, repo: AuthRepository) -> None:
        assert await repo.get_user_by_email("nobody@fisherp.local") is None

    async def test_excludes_soft_deleted_users(
        self, repo: AuthRepository, db_session: AsyncSession
    ) -> None:
        await _make_user(
            db_session, email="deleted@fisherp.local", deleted_at=datetime.now(UTC)
        )
        assert await repo.get_user_by_email("deleted@fisherp.local") is None


class TestGetRolesAndPermissions:
    async def test_super_admin_gets_full_permission_set(
        self, repo: AuthRepository, db_session: AsyncSession
    ) -> None:
        user_result = await db_session.execute(
            select(User).where(User.email == "admin@fisherp.local")
        )
        user = user_result.scalar_one()

        roles, permissions = await repo.get_roles_and_permissions(user.id)

        assert roles == ["super_admin"]
        assert "invoice:issue" in permissions
        assert "user:manage" in permissions
        assert len(permissions) == len(set(permissions))  # no duplicates from the join

    async def test_user_with_no_roles_gets_empty_lists(
        self, repo: AuthRepository, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, email="no-roles@fisherp.local")
        roles, permissions = await repo.get_roles_and_permissions(user.id)
        assert roles == []
        assert permissions == []


class TestRefreshTokenLifecycle:
    async def test_create_and_lookup_by_hash(
        self, repo: AuthRepository, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        token_hash = hash_refresh_token("some-raw-token")
        created = await repo.create_refresh_token(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )

        assert created.family_id is not None  # picked up the model's default factory

        found = await repo.get_refresh_token_by_hash(token_hash)
        assert found is not None
        assert found.id == created.id

    async def test_explicit_family_id_is_respected(
        self, repo: AuthRepository, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        family_id = uuid.uuid4()
        created = await repo.create_refresh_token(
            user_id=user.id,
            token_hash=hash_refresh_token("another-token"),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            family_id=family_id,
        )
        assert created.family_id == family_id

    async def test_mark_revoked_sets_timestamp_and_replacement(
        self, repo: AuthRepository, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        token = await repo.create_refresh_token(
            user_id=user.id,
            token_hash=hash_refresh_token("to-be-revoked"),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        assert token.revoked_at is None

        replacement_id = token.id
        await repo.mark_revoked(token, replaced_by=replacement_id)

        assert token.revoked_at is not None
        assert token.replaced_by == replacement_id

    async def test_revoke_family_revokes_every_unrevoked_member(
        self, repo: AuthRepository, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        family_id = uuid.uuid4()
        first = await repo.create_refresh_token(
            user_id=user.id,
            token_hash=hash_refresh_token("family-a"),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            family_id=family_id,
        )
        second = await repo.create_refresh_token(
            user_id=user.id,
            token_hash=hash_refresh_token("family-b"),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            family_id=family_id,
        )
        await db_session.commit()

        await repo.revoke_family(family_id)
        await db_session.commit()
        await db_session.refresh(first)
        await db_session.refresh(second)

        assert first.revoked_at is not None
        assert second.revoked_at is not None

    async def test_revoke_all_for_user_only_touches_that_user(
        self, repo: AuthRepository, db_session: AsyncSession
    ) -> None:
        user_a = await _make_user(db_session, email="a@fisherp.local", username="a-user")
        user_b = await _make_user(db_session, email="b@fisherp.local", username="b-user")

        token_a = await repo.create_refresh_token(
            user_id=user_a.id,
            token_hash=hash_refresh_token("user-a-token"),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        token_b = await repo.create_refresh_token(
            user_id=user_b.id,
            token_hash=hash_refresh_token("user-b-token"),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        await db_session.commit()

        await repo.revoke_all_for_user(user_a.id)
        await db_session.commit()
        await db_session.refresh(token_a)
        await db_session.refresh(token_b)

        assert token_a.revoked_at is not None
        assert token_b.revoked_at is None


class TestAuditLog:
    async def test_add_audit_log_persists_a_row(
        self, repo: AuthRepository, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        await repo.add_audit_log(
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="login_success",
            entity_id=user.id,
            ip_address="127.0.0.1",
            user_agent="pytest",
            request_id="req-123",
        )
        await db_session.commit()

        result = await db_session.execute(select(AuditLog).where(AuditLog.user_id == user.id))
        row = result.scalar_one()
        assert row.action == "login_success"
        # INET column round-trips as ipaddress.IPv4Address, not str.
        assert str(row.ip_address) == "127.0.0.1"
        assert row.request_id == "req-123"
