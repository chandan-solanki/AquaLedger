import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import AuditLog, Role, Tenant, User
from app.modules.auth.security import create_access_token, hash_password

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"


async def _login(
    client: AsyncClient, email: str = SUPER_ADMIN_EMAIL, password: str = SUPER_ADMIN_PASSWORD
) -> dict[str, Any]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    body = await _login(client)
    return {"Authorization": f"Bearer {body['access_token']}"}


async def _admin_tenant_id(client: AsyncClient) -> uuid.UUID:
    body = await _login(client)
    return uuid.UUID(body["user"]["tenant_id"])


async def _admin_user_id(client: AsyncClient) -> uuid.UUID:
    body = await _login(client)
    return uuid.UUID(body["user"]["id"])


async def _make_user_headers(
    db_session: AsyncSession, tenant_id: uuid.UUID, permissions: list[str]
) -> dict[str, str]:
    user = User(
        tenant_id=tenant_id,
        email=f"user-{uuid.uuid4().hex[:8]}@fisherp.local",
        username=f"user-{uuid.uuid4().hex[:8]}",
        password_hash=hash_password("Whatever@123"),
        full_name="Test User",
        status=AccountStatus.ACTIVE,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    token = create_access_token(
        subject=user.id, tenant_id=user.tenant_id, roles=["custom"], permissions=permissions
    )
    return {"Authorization": f"Bearer {token}"}


async def _get_role_id(db_session: AsyncSession, tenant_id: uuid.UUID, name: str) -> uuid.UUID:
    role = (
        await db_session.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name == name))
    ).scalar_one()
    return role.id


async def _create_user(
    client: AsyncClient, headers: dict[str, str], role_id: uuid.UUID, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "email": f"user-{uuid.uuid4().hex[:8]}@fisherp.local",
        "username": f"user-{uuid.uuid4().hex[:8]}",
        "full_name": "Audit Test User",
        "password": "TempPass@123",
        "role_id": str(role_id),
    }
    payload.update(overrides)
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _list_logs(client: AsyncClient, headers: dict[str, str], **params: Any) -> dict[str, Any]:
    response = await client.get("/api/v1/audit-logs", headers=headers, params=params)
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


async def _rows_for_entity(
    client: AsyncClient, headers: dict[str, str], entity_id: str
) -> list[dict[str, Any]]:
    body = await _list_logs(client, headers, entity_type="user", page_size=100)
    return [row for row in body["data"] if row["entity_id"] == entity_id]


class TestListAuditLogsAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/audit-logs")
        assert response.status_code == 401

    async def test_requires_audit_log_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get("/api/v1/audit-logs", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_user_manage_alone_is_not_sufficient(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """audit_log:view is a distinct permission from user:manage (the
        seed data grants manager both, but a narrower custom role could hold
        just one) - this module must not accept user:manage as a substitute."""
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["user:manage"])
        response = await client.get("/api/v1/audit-logs", headers=headers)
        assert response.status_code == 403


class TestListAuditLogs:
    async def test_login_success_is_visible(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        body = await _list_logs(client, headers)
        actions = {row["action"] for row in body["data"]}
        assert "login_success" in actions

    async def test_actor_information_is_included(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        admin_user_id = await _admin_user_id(client)
        body = await _list_logs(client, headers, action="login_success", page_size=5)
        assert body["data"], "expected at least one login_success row"
        row = body["data"][0]
        assert row["actor"]["id"] == str(admin_user_id)
        assert row["actor"]["email"] == SUPER_ADMIN_EMAIL

    async def test_filter_by_action(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        body = await _list_logs(client, headers, action="login_success")
        assert body["data"]
        assert all(row["action"] == "login_success" for row in body["data"])

    async def test_filter_by_entity_type(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        body = await _list_logs(client, headers, entity_type="user")
        assert body["data"]
        assert all(row["entity_type"] == "user" for row in body["data"])

    async def test_filter_by_user_id(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        admin_user_id = await _admin_user_id(client)
        body = await _list_logs(client, headers, user_id=str(admin_user_id))
        assert body["data"]
        assert all(row["actor"]["id"] == str(admin_user_id) for row in body["data"])

    async def test_search_by_actor_name(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        body = await _list_logs(client, headers, q="Super Admin")
        assert body["data"]
        assert all(row["actor"] is not None for row in body["data"])

    async def test_date_range_filter_excludes_out_of_range_rows(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        body = await _list_logs(client, headers, from_date="2000-01-01", to_date="2000-01-02")
        assert body["data"] == []

    async def test_invalid_date_range_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/audit-logs",
            headers=headers,
            params={"from_date": "2026-08-20", "to_date": "2026-08-01"},
        )
        assert response.status_code == 422

    async def test_invalid_sort_field_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/audit-logs", headers=headers, params={"sort": "action"}
        )
        assert response.status_code == 422

    async def test_pagination_page_size_is_honored(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _login(client)
        await _login(client)
        body = await _list_logs(client, headers, page_size=1)
        assert len(body["data"]) == 1
        assert body["meta"]["page_size"] == 1
        assert body["meta"]["total_records"] >= 3

    async def test_sorted_descending_by_default(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        body = await _list_logs(client, headers, page_size=50)
        timestamps = [row["created_at"] for row in body["data"]]
        assert timestamps == sorted(timestamps, reverse=True)

    async def test_sorted_ascending_when_requested(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        body = await _list_logs(client, headers, sort="created_at", page_size=50)
        timestamps = [row["created_at"] for row in body["data"]]
        assert timestamps == sorted(timestamps)

    async def test_no_credentials_leak_in_response(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        body = await _list_logs(client, headers, page_size=50)
        raw = str(body)
        assert SUPER_ADMIN_PASSWORD not in raw
        assert "password_hash" not in raw
        assert "refresh_token" not in raw


class TestAuditLogTenantIsolation:
    async def test_cannot_see_another_tenants_audit_logs(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(name="Other Audit Co", slug=f"other-audit-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_user = User(
            tenant_id=other_tenant.id,
            email=f"user-{uuid.uuid4().hex[:8]}@fisherp.local",
            username=f"user-{uuid.uuid4().hex[:8]}",
            password_hash=hash_password("Whatever@123"),
            full_name="Other Tenant User",
            status=AccountStatus.ACTIVE,
        )
        db_session.add(other_user)
        await db_session.commit()
        db_session.add(
            AuditLog(
                tenant_id=other_tenant.id,
                user_id=other_user.id,
                action="login_success",
                entity_type="user",
                entity_id=other_user.id,
            )
        )
        await db_session.commit()

        other_headers = await _make_user_headers(db_session, other_tenant.id, ["audit_log:view"])
        other_body = await _list_logs(client, other_headers, page_size=100)
        assert any(row["entity_id"] == str(other_user.id) for row in other_body["data"])

        admin_headers = await _admin_headers(client)
        admin_body = await _list_logs(client, admin_headers, page_size=100)
        assert all(row["entity_id"] != str(other_user.id) for row in admin_body["data"])


class TestAuditLogImmutability:
    async def test_no_create_endpoint(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post("/api/v1/audit-logs", headers=headers, json={})
        assert response.status_code == 405

    async def test_no_update_endpoint(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _admin_headers(client)
        log = (await db_session.execute(select(AuditLog).limit(1))).scalars().first()
        assert log is not None
        response = await client.put(f"/api/v1/audit-logs/{log.id}", headers=headers, json={})
        assert response.status_code in (404, 405)

    async def test_no_delete_endpoint(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _admin_headers(client)
        log = (await db_session.execute(select(AuditLog).limit(1))).scalars().first()
        assert log is not None
        response = await client.delete(f"/api/v1/audit-logs/{log.id}", headers=headers)
        assert response.status_code in (404, 405)


class TestUserMutationsAreAudited:
    """Sprint 14 Session 5 Phase 4/7 - Users module mutations must generate
    audit records; verified end-to-end through the real API and the real
    audit-logs read endpoint, not by inspecting the ORM directly."""

    async def test_user_created_is_audited(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        admin_user_id = await _admin_user_id(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")

        created = await _create_user(client, headers, role_id)

        rows = await _rows_for_entity(client, headers, created["id"])
        matches = [row for row in rows if row["action"] == "user_created"]
        assert len(matches) == 1
        entry = matches[0]
        assert entry["actor"]["id"] == str(admin_user_id)
        assert entry["changes"]["email"] == created["email"]
        assert entry["changes"]["role"] == "accountant"
        assert "password" not in str(entry["changes"]).lower()

    async def test_user_updated_is_audited_with_old_and_new_values(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        created = await _create_user(client, headers, role_id, full_name="Original Name")

        response = await client.put(
            f"/api/v1/users/{created['id']}", headers=headers, json={"full_name": "Updated Name"}
        )
        assert response.status_code == 200

        rows = await _rows_for_entity(client, headers, created["id"])
        matches = [row for row in rows if row["action"] == "user_updated"]
        assert len(matches) == 1
        assert matches[0]["changes"]["full_name"] == {"old": "Original Name", "new": "Updated Name"}

    async def test_user_deactivated_then_activated_is_audited_in_order(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        created = await _create_user(client, headers, role_id)

        deactivate = await client.patch(
            f"/api/v1/users/{created['id']}/status", headers=headers, json={"status": "inactive"}
        )
        assert deactivate.status_code == 200
        activate = await client.patch(
            f"/api/v1/users/{created['id']}/status", headers=headers, json={"status": "active"}
        )
        assert activate.status_code == 200

        rows = await _rows_for_entity(client, headers, created["id"])
        ordered_actions = [row["action"] for row in sorted(rows, key=lambda row: row["created_at"])]
        assert "user_deactivated" in ordered_actions
        assert "user_activated" in ordered_actions
        assert ordered_actions.index("user_deactivated") < ordered_actions.index("user_activated")

        deactivated_entry = next(row for row in rows if row["action"] == "user_deactivated")
        assert deactivated_entry["changes"]["status"] == {"old": "active", "new": "inactive"}

    async def test_user_role_changed_is_audited(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        accountant_role_id = await _get_role_id(db_session, tenant_id, "accountant")
        operator_role_id = await _get_role_id(db_session, tenant_id, "operator")
        created = await _create_user(client, headers, accountant_role_id)

        response = await client.put(
            f"/api/v1/users/{created['id']}",
            headers=headers,
            json={"role_id": str(operator_role_id)},
        )
        assert response.status_code == 200

        rows = await _rows_for_entity(client, headers, created["id"])
        matches = [row for row in rows if row["action"] == "user_role_changed"]
        assert len(matches) == 1
        assert matches[0]["changes"]["role"] == {"old": "accountant", "new": "operator"}

    async def test_failed_user_creation_does_not_create_a_false_audit_row(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        existing = await _create_user(client, headers, role_id)

        before = await _list_logs(client, headers, action="user_created", page_size=100)
        duplicate_response = await client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "email": existing["email"],
                "username": f"user-{uuid.uuid4().hex[:8]}",
                "full_name": "Duplicate Email User",
                "password": "TempPass@123",
                "role_id": str(role_id),
            },
        )
        assert duplicate_response.status_code == 409
        after = await _list_logs(client, headers, action="user_created", page_size=100)
        assert after["meta"]["total_records"] == before["meta"]["total_records"]

    async def test_failed_user_update_does_not_create_a_false_audit_row(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        user_a = await _create_user(client, headers, role_id)
        user_b = await _create_user(client, headers, role_id)

        before = await _list_logs(client, headers, action="user_updated", page_size=100)
        conflict_response = await client.put(
            f"/api/v1/users/{user_b['id']}", headers=headers, json={"email": user_a["email"]}
        )
        assert conflict_response.status_code == 409
        after = await _list_logs(client, headers, action="user_updated", page_size=100)
        assert after["meta"]["total_records"] == before["meta"]["total_records"]
