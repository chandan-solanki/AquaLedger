from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import AuditLog, User

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"


async def _actions_for(db_session: AsyncSession, user_id: object) -> list[str]:
    result = await db_session.execute(
        select(AuditLog.action).where(AuditLog.user_id == user_id).order_by(AuditLog.created_at)
    )
    return [row[0] for row in result.all()]


class TestLoginAuditLog:
    async def test_successful_login_is_logged(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
        )
        assert response.status_code == 200
        user_id = response.json()["user"]["id"]

        actions = await _actions_for(db_session, user_id)
        assert "login_success" in actions

    async def test_failed_login_is_logged(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": "wrong-password"},
        )
        assert response.status_code == 401

        user_result = await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        user = user_result.scalar_one()

        actions = await _actions_for(db_session, user.id)
        assert "login_failed" in actions

    async def test_audit_row_carries_request_metadata(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
            headers={"User-Agent": "pytest-audit-check"},
        )
        user_id = response.json()["user"]["id"]

        result = await db_session.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id, AuditLog.action == "login_success")
            .order_by(AuditLog.created_at.desc())
        )
        row = result.scalars().first()
        assert row is not None
        assert row.user_agent == "pytest-audit-check"
        assert row.request_id is not None
        assert row.tenant_id is not None


class TestLogoutAuditLog:
    async def test_logout_is_logged(self, client: AsyncClient, db_session: AsyncSession) -> None:
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
        )
        body = login_response.json()

        await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": body["refresh_token"]},
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )

        actions = await _actions_for(db_session, body["user"]["id"])
        assert "logout" in actions


class TestChangePasswordAuditLog:
    async def test_password_change_is_logged(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
        )
        body = login_response.json()

        change_response = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": SUPER_ADMIN_PASSWORD, "new_password": "NewStrong@1"},
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        assert change_response.status_code == 204

        actions = await _actions_for(db_session, body["user"]["id"])
        assert "password_changed" in actions
