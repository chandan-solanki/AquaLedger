import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Permission, Role, RolePermission, Tenant, User
from app.modules.auth.security import create_access_token, hash_password

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"


async def _login(client: AsyncClient) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/login", json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    body = await _login(client)
    return {"Authorization": f"Bearer {body['access_token']}"}


async def _admin_tenant_id(client: AsyncClient) -> uuid.UUID:
    body = await _login(client)
    return uuid.UUID(body["user"]["tenant_id"])


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


async def _get_role(db_session: AsyncSession, tenant_id: uuid.UUID, name: str) -> Role:
    return (
        await db_session.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name == name))
    ).scalar_one()


async def _permission_count_for_role(db_session: AsyncSession, role_id: uuid.UUID) -> int:
    return (
        await db_session.execute(
            select(func.count())
            .select_from(RolePermission)
            .where(RolePermission.role_id == role_id)
        )
    ).scalar_one()


async def _create_user_with_role(
    client: AsyncClient, headers: dict[str, str], role_id: uuid.UUID, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "email": f"user-{uuid.uuid4().hex[:8]}@fisherp.local",
        "username": f"user-{uuid.uuid4().hex[:8]}",
        "full_name": "Role Test User",
        "password": "TempPass@123",
        "role_id": str(role_id),
    }
    payload.update(overrides)
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


class TestListRoles:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/roles")
        assert response.status_code == 401

    async def test_requires_user_manage_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get("/api/v1/roles", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_returns_every_seeded_system_role(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/roles", headers=headers)
        assert response.status_code == 200
        names = {row["name"] for row in response.json()}
        assert names == {"super_admin", "admin", "manager", "accountant", "operator"}
        assert all(row["is_system"] is True for row in response.json())

    async def test_permission_count_matches_the_database(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        accountant = await _get_role(db_session, tenant_id, "accountant")
        expected_count = await _permission_count_for_role(db_session, accountant.id)

        response = await client.get("/api/v1/roles", headers=headers)
        row = next(r for r in response.json() if r["name"] == "accountant")
        assert row["permission_count"] == expected_count

    async def test_user_count_reflects_role_assignments(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        accountant = await _get_role(db_session, tenant_id, "accountant")

        before = await client.get("/api/v1/roles", headers=headers)
        before_count = next(r for r in before.json() if r["name"] == "accountant")["user_count"]

        await _create_user_with_role(client, headers, accountant.id)

        after = await client.get("/api/v1/roles", headers=headers)
        after_count = next(r for r in after.json() if r["name"] == "accountant")["user_count"]
        assert after_count == before_count + 1

    async def test_tenant_isolation_returns_only_own_roles(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(name="Other Roles Co", slug=f"other-roles-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_role = Role(
            tenant_id=other_tenant.id, name="custom_role", description=None, is_system=False
        )
        db_session.add(other_role)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, ["user:manage"])

        response = await client.get("/api/v1/roles", headers=other_headers)
        assert response.status_code == 200
        names = {row["name"] for row in response.json()}
        assert names == {"custom_role"}


class TestGetRole:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/roles/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_permission(self, client: AsyncClient, db_session: AsyncSession) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(f"/api/v1/roles/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_returns_permissions_matching_the_database(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        operator = await _get_role(db_session, tenant_id, "operator")
        expected_count = await _permission_count_for_role(db_session, operator.id)

        response = await client.get(f"/api/v1/roles/{operator.id}", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "operator"
        assert len(body["permissions"]) == expected_count
        assert body["permissions"] == sorted(
            body["permissions"], key=lambda p: (p["resource"], p["action"])
        )

    async def test_includes_users_holding_the_role(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        accountant = await _get_role(db_session, tenant_id, "accountant")
        created = await _create_user_with_role(client, headers, accountant.id)

        response = await client.get(f"/api/v1/roles/{accountant.id}", headers=headers)
        assert response.status_code == 200
        user_ids = {u["id"] for u in response.json()["users"]}
        assert created["id"] in user_ids

    async def test_deactivated_user_still_appears_with_inactive_status(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        accountant = await _get_role(db_session, tenant_id, "accountant")
        created = await _create_user_with_role(client, headers, accountant.id)

        status_response = await client.patch(
            f"/api/v1/users/{created['id']}/status", json={"status": "inactive"}, headers=headers
        )
        assert status_response.status_code == 200

        response = await client.get(f"/api/v1/roles/{accountant.id}", headers=headers)
        member = next(u for u in response.json()["users"] if u["id"] == created["id"])
        assert member["status"] == "inactive"

    async def test_response_never_contains_password_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        accountant = await _get_role(db_session, tenant_id, "accountant")
        await _create_user_with_role(client, headers, accountant.id)

        response = await client.get(f"/api/v1/roles/{accountant.id}", headers=headers)
        body_text = response.text
        assert "password" not in body_text.lower()

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(f"/api/v1/roles/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "ROLE_NOT_FOUND"

    async def test_other_tenants_role_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        other_tenant = Tenant(
            name="Other Role Detail Co", slug=f"other-role-detail-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_role = Role(
            tenant_id=other_tenant.id, name="custom_role", description=None, is_system=False
        )
        db_session.add(other_role)
        await db_session.commit()

        response = await client.get(f"/api/v1/roles/{other_role.id}", headers=headers)
        assert response.status_code == 404


class TestListPermissions:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/roles/permissions")
        assert response.status_code == 401

    async def test_requires_permission(self, client: AsyncClient, db_session: AsyncSession) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get("/api/v1/roles/permissions", headers=headers)
        assert response.status_code == 403

    async def test_matches_total_permission_count_in_the_database(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        expected = (
            await db_session.execute(select(func.count()).select_from(Permission))
        ).scalar_one()

        response = await client.get("/api/v1/roles/permissions", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == expected

    async def test_global_reference_data_is_identical_across_tenants(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        admin_headers = await _admin_headers(client)
        admin_response = await client.get("/api/v1/roles/permissions", headers=admin_headers)

        other_tenant = Tenant(
            name="Other Permissions Co", slug=f"other-perms-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, ["user:manage"])
        other_response = await client.get("/api/v1/roles/permissions", headers=other_headers)

        admin_codes = sorted(p["code"] for p in admin_response.json())
        other_codes = sorted(p["code"] for p in other_response.json())
        assert admin_codes == other_codes

    async def test_sorted_by_resource_then_action(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/roles/permissions", headers=headers)
        permissions = response.json()
        assert permissions == sorted(permissions, key=lambda p: (p["resource"], p["action"]))


class TestUsersRolesIntegrationRegression:
    """Confirms this read-only module doesn't disturb Session 3's Users
    behavior - role/permission viewing is additive, never mutates
    user_roles/role_permissions."""

    async def test_creating_and_editing_a_user_still_works_after_viewing_roles(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        accountant = await _get_role(db_session, tenant_id, "accountant")
        operator = await _get_role(db_session, tenant_id, "operator")

        # Viewing roles/permissions in between must not affect subsequent writes.
        await client.get("/api/v1/roles", headers=headers)
        await client.get(f"/api/v1/roles/{accountant.id}", headers=headers)
        await client.get("/api/v1/roles/permissions", headers=headers)

        created = await _create_user_with_role(client, headers, accountant.id)
        update_response = await client.put(
            f"/api/v1/users/{created['id']}",
            json={"role_id": str(operator.id)},
            headers=headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["role"]["name"] == "operator"

        deactivate_response = await client.patch(
            f"/api/v1/users/{created['id']}/status", json={"status": "inactive"}, headers=headers
        )
        assert deactivate_response.status_code == 200
        assert deactivate_response.json()["status"] == "inactive"

    async def test_role_permission_rows_are_untouched_by_viewing(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        accountant = await _get_role(db_session, tenant_id, "accountant")
        before = await _permission_count_for_role(db_session, accountant.id)

        headers = await _admin_headers(client)
        for _ in range(3):
            await client.get(f"/api/v1/roles/{accountant.id}", headers=headers)

        after = await _permission_count_for_role(db_session, accountant.id)
        assert after == before
