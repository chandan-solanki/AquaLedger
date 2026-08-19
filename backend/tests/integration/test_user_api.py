import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Role, Tenant, User
from app.modules.auth.security import create_access_token, hash_password

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

_NEW_USER_PASSWORD = "TempPass@123"


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
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    permissions: list[str],
    *,
    is_superuser: bool = False,
) -> tuple[dict[str, str], User]:
    user = User(
        tenant_id=tenant_id,
        email=f"user-{uuid.uuid4().hex[:8]}@fisherp.local",
        username=f"user-{uuid.uuid4().hex[:8]}",
        password_hash=hash_password("Whatever@123"),
        full_name="Test User",
        status=AccountStatus.ACTIVE,
        is_superuser=is_superuser,
    )
    db_session.add(user)
    await db_session.commit()
    token = create_access_token(
        subject=user.id, tenant_id=user.tenant_id, roles=["custom"], permissions=permissions
    )
    return {"Authorization": f"Bearer {token}"}, user


async def _get_role_id(db_session: AsyncSession, tenant_id: uuid.UUID, name: str) -> uuid.UUID:
    role = (
        await db_session.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name == name))
    ).scalar_one()
    return role.id


async def _create_role(db_session: AsyncSession, tenant_id: uuid.UUID, name: str) -> Role:
    role = Role(tenant_id=tenant_id, name=name, description=None, is_system=False)
    db_session.add(role)
    await db_session.commit()
    return role


async def _create_user(
    client: AsyncClient, headers: dict[str, str], role_id: uuid.UUID, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "email": f"user-{uuid.uuid4().hex[:8]}@fisherp.local",
        "username": f"user-{uuid.uuid4().hex[:8]}",
        "full_name": "New User",
        "password": _NEW_USER_PASSWORD,
        "role_id": str(role_id),
    }
    payload.update(overrides)
    response = await client.post("/api/v1/users", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


class TestCreateUser:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/users", json={})
        assert response.status_code == 401

    async def test_requires_user_manage_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers, _ = await _make_user_headers(db_session, tenant_id, [])
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        response = await client.post(
            "/api/v1/users",
            json={
                "email": "x@fisherp.local",
                "username": "xuser",
                "full_name": "X",
                "password": _NEW_USER_PASSWORD,
                "role_id": str(role_id),
            },
            headers=headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_success_creates_active_user_forced_to_change_password(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")

        body = await _create_user(client, headers, role_id)
        assert body["status"] == "active"
        assert body["is_superuser"] is False
        assert body["role"]["name"] == "accountant"
        assert "password" not in body
        assert "password_hash" not in body

        login_body = await _login(client, email=body["email"], password=_NEW_USER_PASSWORD)
        assert login_body["must_change_password"] is True

    async def test_duplicate_email_is_409(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        first = await _create_user(client, headers, role_id)

        response = await client.post(
            "/api/v1/users",
            json={
                "email": first["email"],
                "username": f"other-{uuid.uuid4().hex[:8]}",
                "full_name": "Dup",
                "password": _NEW_USER_PASSWORD,
                "role_id": str(role_id),
            },
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DUPLICATE_USER_EMAIL"

    async def test_duplicate_username_is_409(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        first = await _create_user(client, headers, role_id)

        response = await client.post(
            "/api/v1/users",
            json={
                "email": f"other-{uuid.uuid4().hex[:8]}@fisherp.local",
                "username": first["username"],
                "full_name": "Dup",
                "password": _NEW_USER_PASSWORD,
                "role_id": str(role_id),
            },
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DUPLICATE_USERNAME"

    async def test_invalid_email_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        response = await client.post(
            "/api/v1/users",
            json={
                "email": "not-an-email",
                "username": "someone",
                "full_name": "Someone",
                "password": _NEW_USER_PASSWORD,
                "role_id": str(role_id),
            },
            headers=headers,
        )
        assert response.status_code == 422

    async def test_weak_password_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        response = await client.post(
            "/api/v1/users",
            json={
                "email": f"weak-{uuid.uuid4().hex[:8]}@fisherp.local",
                "username": f"weak-{uuid.uuid4().hex[:8]}",
                "full_name": "Weak",
                "password": "alllowercase",
                "role_id": str(role_id),
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "password" in response.json()["error"]["field_errors"]

    async def test_unknown_role_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/users",
            json={
                "email": f"norol-{uuid.uuid4().hex[:8]}@fisherp.local",
                "username": f"norole-{uuid.uuid4().hex[:8]}",
                "full_name": "No Role",
                "password": _NEW_USER_PASSWORD,
                "role_id": str(uuid.uuid4()),
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "ROLE_NOT_FOUND"

    async def test_non_superuser_cannot_assign_super_admin_role(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        actor_headers, _ = await _make_user_headers(
            db_session, tenant_id, ["user:manage"], is_superuser=False
        )
        super_admin_role_id = await _get_role_id(db_session, tenant_id, "super_admin")

        response = await client.post(
            "/api/v1/users",
            json={
                "email": f"escalate-{uuid.uuid4().hex[:8]}@fisherp.local",
                "username": f"escalate-{uuid.uuid4().hex[:8]}",
                "full_name": "Escalate",
                "password": _NEW_USER_PASSWORD,
                "role_id": str(super_admin_role_id),
            },
            headers=actor_headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "SUPER_ADMIN_ROLE_PROTECTED"

    async def test_superuser_can_assign_super_admin_role(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        super_admin_role_id = await _get_role_id(db_session, tenant_id, "super_admin")

        body = await _create_user(client, headers, super_admin_role_id)
        assert body["role"]["name"] == "super_admin"


class TestListUsers:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/users")
        assert response.status_code == 401

    async def test_requires_permission(self, client: AsyncClient, db_session: AsyncSession) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers, _ = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get("/api/v1/users", headers=headers)
        assert response.status_code == 403

    async def test_default_response_shape(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        await _create_user(client, headers, role_id)

        response = await client.get("/api/v1/users", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert "data" in body and "meta" in body
        assert set(body["meta"]) == {
            "total_records",
            "total_pages",
            "current_page",
            "page_size",
            "has_next",
            "has_previous",
        }

    async def test_search_matches_full_name_case_insensitively(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        marker = uuid.uuid4().hex[:8]
        await _create_user(client, headers, role_id, full_name=f"Special Search {marker}")
        await _create_user(client, headers, role_id, full_name=f"Irrelevant {marker}")

        response = await client.get(
            "/api/v1/users", params={"q": f"special search {marker}".upper()}, headers=headers
        )
        names = [u["full_name"] for u in response.json()["data"]]
        assert names == [f"Special Search {marker}"]

    async def test_filter_by_role_id(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        accountant_role_id = await _get_role_id(db_session, tenant_id, "accountant")
        operator_role_id = await _get_role_id(db_session, tenant_id, "operator")
        marker = uuid.uuid4().hex[:8]
        await _create_user(client, headers, accountant_role_id, full_name=f"Acc {marker}")
        await _create_user(client, headers, operator_role_id, full_name=f"Op {marker}")

        response = await client.get(
            "/api/v1/users",
            params={"role_id": str(accountant_role_id), "q": marker},
            headers=headers,
        )
        names = [u["full_name"] for u in response.json()["data"]]
        assert names == [f"Acc {marker}"]

    async def test_filter_by_status(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        marker = uuid.uuid4().hex[:8]
        created = await _create_user(client, headers, role_id, full_name=f"StatusTest {marker}")
        await client.patch(
            f"/api/v1/users/{created['id']}/status", json={"status": "inactive"}, headers=headers
        )

        response = await client.get(
            "/api/v1/users", params={"status": "inactive", "q": marker}, headers=headers
        )
        ids = [u["id"] for u in response.json()["data"]]
        assert created["id"] in ids

    async def test_sort_ascending_and_descending(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        marker = uuid.uuid4().hex[:8]
        await _create_user(client, headers, role_id, full_name=f"Bravo {marker}")
        await _create_user(client, headers, role_id, full_name=f"Alpha {marker}")

        asc = await client.get(
            "/api/v1/users", params={"q": marker, "sort": "full_name"}, headers=headers
        )
        assert [u["full_name"] for u in asc.json()["data"]] == [
            f"Alpha {marker}",
            f"Bravo {marker}",
        ]

        desc = await client.get(
            "/api/v1/users", params={"q": marker, "sort": "-full_name"}, headers=headers
        )
        assert [u["full_name"] for u in desc.json()["data"]] == [
            f"Bravo {marker}",
            f"Alpha {marker}",
        ]

    async def test_invalid_sort_field_is_422(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/users", params={"sort": "password_hash"}, headers=await _admin_headers(client)
        )
        assert response.status_code == 422

    async def test_tenant_isolation_returns_only_own_users(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        await _create_user(client, headers, role_id)

        other_tenant = Tenant(name="Other Co", slug=f"other-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_role = await _create_role(db_session, other_tenant.id, "admin")
        other_headers, _ = await _make_user_headers(db_session, other_tenant.id, ["user:manage"])

        response = await client.get("/api/v1/users", headers=other_headers)
        assert response.status_code == 200
        # Only the one actor user created in the other tenant, never tenant A's rows.
        for row in response.json()["data"]:
            assert row["tenant_id"] == str(other_tenant.id)
        assert other_role.tenant_id == other_tenant.id


class TestGetUser:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/users/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_permission(self, client: AsyncClient, db_session: AsyncSession) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers, _ = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(f"/api/v1/users/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_returns_the_user(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        created = await _create_user(client, headers, role_id)

        response = await client.get(f"/api/v1/users/{created['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(f"/api/v1/users/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "USER_NOT_FOUND"

    async def test_other_tenants_user_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        created = await _create_user(client, headers, role_id)

        other_tenant = Tenant(name="Isolated Co", slug=f"isolated-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers, _ = await _make_user_headers(db_session, other_tenant.id, ["user:manage"])

        response = await client.get(f"/api/v1/users/{created['id']}", headers=other_headers)
        assert response.status_code == 404


class TestUpdateUser:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.put(f"/api/v1/users/{uuid.uuid4()}", json={"full_name": "X"})
        assert response.status_code == 401

    async def test_requires_permission(self, client: AsyncClient, db_session: AsyncSession) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers, _ = await _make_user_headers(db_session, tenant_id, [])
        response = await client.put(
            f"/api/v1/users/{uuid.uuid4()}", json={"full_name": "X"}, headers=headers
        )
        assert response.status_code == 403

    async def test_partial_update_only_changes_supplied_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        created = await _create_user(client, headers, role_id, full_name="Original Name")

        response = await client.put(
            f"/api/v1/users/{created['id']}", json={"phone": "9876500000"}, headers=headers
        )
        assert response.status_code == 200
        body = response.json()
        assert body["phone"] == "9876500000"
        assert body["full_name"] == "Original Name"

    async def test_role_change_updates_role(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        accountant_role_id = await _get_role_id(db_session, tenant_id, "accountant")
        operator_role_id = await _get_role_id(db_session, tenant_id, "operator")
        created = await _create_user(client, headers, accountant_role_id)

        response = await client.put(
            f"/api/v1/users/{created['id']}",
            json={"role_id": str(operator_role_id)},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["role"]["name"] == "operator"

    async def test_duplicate_email_on_update_is_409(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        first = await _create_user(client, headers, role_id)
        second = await _create_user(client, headers, role_id)

        response = await client.put(
            f"/api/v1/users/{second['id']}", json={"email": first["email"]}, headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DUPLICATE_USER_EMAIL"

    async def test_non_superuser_cannot_promote_to_super_admin(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        admin_headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        accountant_role_id = await _get_role_id(db_session, tenant_id, "accountant")
        target = await _create_user(client, admin_headers, accountant_role_id)

        actor_headers, _ = await _make_user_headers(
            db_session, tenant_id, ["user:manage"], is_superuser=False
        )
        super_admin_role_id = await _get_role_id(db_session, tenant_id, "super_admin")

        response = await client.put(
            f"/api/v1/users/{target['id']}",
            json={"role_id": str(super_admin_role_id)},
            headers=actor_headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "SUPER_ADMIN_ROLE_PROTECTED"

    async def test_non_superuser_cannot_change_an_existing_super_admins_role(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        admin_headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        super_admin_role_id = await _get_role_id(db_session, tenant_id, "super_admin")
        operator_role_id = await _get_role_id(db_session, tenant_id, "operator")
        target = await _create_user(client, admin_headers, super_admin_role_id)

        actor_headers, _ = await _make_user_headers(
            db_session, tenant_id, ["user:manage"], is_superuser=False
        )

        response = await client.put(
            f"/api/v1/users/{target['id']}",
            json={"role_id": str(operator_role_id)},
            headers=actor_headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "SUPER_ADMIN_ROLE_PROTECTED"

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            f"/api/v1/users/{uuid.uuid4()}", json={"full_name": "X"}, headers=headers
        )
        assert response.status_code == 404

    async def test_other_tenants_user_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        created = await _create_user(client, headers, role_id)

        other_tenant = Tenant(name="Other Updater Co", slug=f"other-upd-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers, _ = await _make_user_headers(db_session, other_tenant.id, ["user:manage"])

        response = await client.put(
            f"/api/v1/users/{created['id']}", json={"full_name": "Hijacked"}, headers=other_headers
        )
        assert response.status_code == 404

        still_there = await client.get(f"/api/v1/users/{created['id']}", headers=headers)
        assert still_there.json()["full_name"] != "Hijacked"

    async def test_invalid_email_on_update_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        created = await _create_user(client, headers, role_id)

        response = await client.put(
            f"/api/v1/users/{created['id']}", json={"email": "not-an-email"}, headers=headers
        )
        assert response.status_code == 422


class TestUpdateUserStatus:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.patch(
            f"/api/v1/users/{uuid.uuid4()}/status", json={"status": "inactive"}
        )
        assert response.status_code == 401

    async def test_requires_permission(self, client: AsyncClient, db_session: AsyncSession) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers, _ = await _make_user_headers(db_session, tenant_id, [])
        response = await client.patch(
            f"/api/v1/users/{uuid.uuid4()}/status", json={"status": "inactive"}, headers=headers
        )
        assert response.status_code == 403

    async def test_deactivate_then_reactivate_happy_path(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        created = await _create_user(client, headers, role_id)

        deactivate = await client.patch(
            f"/api/v1/users/{created['id']}/status", json={"status": "inactive"}, headers=headers
        )
        assert deactivate.status_code == 200
        assert deactivate.json()["status"] == "inactive"

        reactivate = await client.patch(
            f"/api/v1/users/{created['id']}/status", json={"status": "active"}, headers=headers
        )
        assert reactivate.status_code == 200
        assert reactivate.json()["status"] == "active"

    async def test_cannot_deactivate_self(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        admin_id = await _admin_user_id(client)

        response = await client.patch(
            f"/api/v1/users/{admin_id}/status", json={"status": "inactive"}, headers=headers
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "CANNOT_DEACTIVATE_SELF"

    async def test_cannot_deactivate_last_active_admin(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        admin_id = await _admin_user_id(client)
        actor_headers, _ = await _make_user_headers(
            db_session, tenant_id, ["user:manage"], is_superuser=False
        )

        response = await client.patch(
            f"/api/v1/users/{admin_id}/status", json={"status": "inactive"}, headers=actor_headers
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "CANNOT_DEACTIVATE_LAST_ADMIN"

        still_active = (
            await db_session.execute(select(User).where(User.id == admin_id))
        ).scalar_one()
        assert still_active.status == AccountStatus.ACTIVE

    async def test_deactivating_a_non_admin_does_not_trigger_last_admin_check(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        created = await _create_user(client, headers, role_id)

        response = await client.patch(
            f"/api/v1/users/{created['id']}/status", json={"status": "inactive"}, headers=headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "inactive"

    async def test_deactivating_revokes_sessions_and_blocks_further_login(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        admin_headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        created = await _create_user(client, admin_headers, role_id)

        target_login = await _login(client, email=created["email"], password=_NEW_USER_PASSWORD)
        refresh_token = target_login["refresh_token"]

        deactivate = await client.patch(
            f"/api/v1/users/{created['id']}/status",
            json={"status": "inactive"},
            headers=admin_headers,
        )
        assert deactivate.status_code == 200

        refresh_response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == 401

        login_again = await client.post(
            "/api/v1/auth/login",
            json={"email": created["email"], "password": _NEW_USER_PASSWORD},
        )
        assert login_again.status_code == 401
        assert login_again.json()["error"]["code"] == "ACCOUNT_DISABLED"

    async def test_invalid_status_value_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        created = await _create_user(client, headers, role_id)

        response = await client.patch(
            f"/api/v1/users/{created['id']}/status", json={"status": "locked"}, headers=headers
        )
        assert response.status_code == 422

    async def test_other_tenants_user_status_change_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        role_id = await _get_role_id(db_session, tenant_id, "accountant")
        created = await _create_user(client, headers, role_id)

        other_tenant = Tenant(name="Other Status Co", slug=f"other-status-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers, _ = await _make_user_headers(db_session, other_tenant.id, ["user:manage"])

        response = await client.patch(
            f"/api/v1/users/{created['id']}/status",
            json={"status": "inactive"},
            headers=other_headers,
        )
        assert response.status_code == 404


class TestRoleOptions:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/users/roles")
        assert response.status_code == 401

    async def test_requires_permission(self, client: AsyncClient, db_session: AsyncSession) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers, _ = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get("/api/v1/users/roles", headers=headers)
        assert response.status_code == 403

    async def test_superuser_sees_super_admin_role(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/users/roles", headers=headers)
        assert response.status_code == 200
        names = [r["name"] for r in response.json()]
        assert "super_admin" in names

    async def test_non_superuser_does_not_see_super_admin_role(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers, _ = await _make_user_headers(
            db_session, tenant_id, ["user:manage"], is_superuser=False
        )
        response = await client.get("/api/v1/users/roles", headers=headers)
        assert response.status_code == 200
        names = [r["name"] for r in response.json()]
        assert "super_admin" not in names
        assert "accountant" in names
