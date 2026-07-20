from datetime import UTC, datetime, timedelta

from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import RefreshToken, User

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"


async def _login(
    client: AsyncClient,
    email: str = SUPER_ADMIN_EMAIL,
    password: str = SUPER_ADMIN_PASSWORD,
) -> Response:
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


class TestLogin:
    async def test_success_returns_tokens_and_flags_password_change(
        self, client: AsyncClient
    ) -> None:
        response = await _login(client)
        assert response.status_code == 200
        body = response.json()
        assert body["access_token"]
        assert body["refresh_token"]
        assert body["token_type"] == "bearer"
        assert body["must_change_password"] is True  # seeded admin has password_changed_at = NULL
        assert body["user"]["email"] == SUPER_ADMIN_EMAIL
        assert "super_admin" in body["user"]["roles"]
        assert "invoice:issue" in body["user"]["permissions"]

    async def test_wrong_password_is_rejected(self, client: AsyncClient) -> None:
        response = await _login(client, password="wrong-password")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"

    async def test_unknown_email_gets_same_generic_error(self, client: AsyncClient) -> None:
        response = await _login(client, email="nobody@fisherp.local", password="whatever")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"

    async def test_invalid_email_format_is_a_validation_error(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/login", json={"email": "not-an-email", "password": "x"}
        )
        assert response.status_code == 422

    async def test_account_locks_after_threshold_failures(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # account_lockout_threshold defaults to 5; seed 4 prior failures directly
        # so this test needs only 2 requests, well clear of the (also 5-attempt)
        # rate limiter, which is a separate, deliberately-not-colliding concern.
        result = await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        user = result.scalar_one()
        user.failed_login_count = 4
        await db_session.commit()

        triggering_response = await _login(client, password="wrong-password")
        assert triggering_response.status_code == 401
        assert triggering_response.json()["error"]["code"] == "INVALID_CREDENTIALS"

        locked_response = await _login(client)  # correct password, but now locked
        assert locked_response.status_code == 401
        assert locked_response.json()["error"]["code"] == "ACCOUNT_LOCKED"

    async def test_rate_limit_blocks_after_configured_attempts(self, client: AsyncClient) -> None:
        # login_rate_limit_attempts defaults to 5, keyed by email+ip regardless of outcome
        for _ in range(5):
            await _login(client, password="wrong-password")
        response = await _login(client, password="wrong-password")
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "RATE_LIMITED"


class TestRefresh:
    async def test_refresh_rotates_and_old_token_stops_working(self, client: AsyncClient) -> None:
        login_response = await _login(client)
        old_refresh = login_response.json()["refresh_token"]

        refresh_response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
        )
        assert refresh_response.status_code == 200
        new_refresh = refresh_response.json()["refresh_token"]
        assert new_refresh != old_refresh

        replay_response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
        )
        assert replay_response.status_code == 401

    async def test_reuse_of_revoked_token_burns_the_whole_family(self, client: AsyncClient) -> None:
        login_response = await _login(client)
        original_refresh = login_response.json()["refresh_token"]

        rotated_response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": original_refresh}
        )
        rotated_refresh = rotated_response.json()["refresh_token"]

        # Replaying the already-rotated (now revoked) token triggers full family revocation.
        reuse_response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": original_refresh}
        )
        assert reuse_response.status_code == 401

        # The child token issued by the legitimate rotation is now also dead.
        child_response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": rotated_refresh}
        )
        assert child_response.status_code == 401

    async def test_garbage_refresh_token_is_rejected(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"}
        )
        assert response.status_code == 401

    async def test_expired_refresh_token_is_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        login_response = await _login(client)
        refresh_token = login_response.json()["refresh_token"]

        user_result = await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        user = user_result.scalar_one()
        token_result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.user_id == user.id)
        )
        for row in token_result.scalars().all():
            row.expires_at = datetime.now(UTC) - timedelta(days=1)
        await db_session.commit()

        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert response.status_code == 401


class TestMe:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_rejects_garbage_token(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"}
        )
        assert response.status_code == 401

    async def test_returns_current_user_with_roles_and_permissions(
        self, client: AsyncClient
    ) -> None:
        login_response = await _login(client)
        access_token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == SUPER_ADMIN_EMAIL
        assert "super_admin" in body["roles"]


class TestLogout:
    async def test_logout_revokes_the_refresh_token(self, client: AsyncClient) -> None:
        login_response = await _login(client)
        access_token = login_response.json()["access_token"]
        refresh_token = login_response.json()["refresh_token"]

        logout_response = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_response.status_code == 204

        refresh_response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == 401

    async def test_logout_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/auth/logout", json={"refresh_token": "whatever"})
        assert response.status_code == 401


class TestChangePassword:
    async def test_wrong_current_password_is_rejected(self, client: AsyncClient) -> None:
        login_response = await _login(client)
        access_token = login_response.json()["access_token"]

        response = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "wrong", "new_password": "NewStrong@1"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 401

    async def test_weak_new_password_is_rejected(self, client: AsyncClient) -> None:
        login_response = await _login(client)
        access_token = login_response.json()["access_token"]

        response = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": SUPER_ADMIN_PASSWORD, "new_password": "weak"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 422
        assert "new_password" in response.json()["error"]["field_errors"]

    async def test_success_allows_login_with_new_password_and_revokes_old_sessions(
        self, client: AsyncClient
    ) -> None:
        login_response = await _login(client)
        access_token = login_response.json()["access_token"]
        old_refresh_token = login_response.json()["refresh_token"]

        change_response = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": SUPER_ADMIN_PASSWORD, "new_password": "NewStrong@1"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert change_response.status_code == 204

        old_password_login = await _login(client)
        assert old_password_login.status_code == 401

        new_password_login = await _login(client, password="NewStrong@1")
        assert new_password_login.status_code == 200
        assert new_password_login.json()["must_change_password"] is False

        stale_refresh_response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": old_refresh_token}
        )
        assert stale_refresh_response.status_code == 401

    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "x", "new_password": "NewStrong@1"},
        )
        assert response.status_code == 401
