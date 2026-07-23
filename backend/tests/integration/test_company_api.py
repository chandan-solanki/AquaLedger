import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.companies.models import Company

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

_ALL_COMPANY_PERMISSIONS = [
    "company:view",
    "company:create",
    "company:edit",
    "company:delete",
]


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _admin_tenant_id(client: AsyncClient) -> uuid.UUID:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
    )
    return uuid.UUID(response.json()["user"]["tenant_id"])


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


async def _create_company(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": f"C-{uuid.uuid4().hex[:8]}",
        "name": f"Company {uuid.uuid4().hex[:8]}",
        "company_type": "customer",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/companies", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


class TestCreateCompany:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/companies",
            json={"code": "X", "name": "X", "company_type": "customer"},
        )
        assert response.status_code == 401

    async def test_requires_create_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["company:view"])
        response = await client.post(
            "/api/v1/companies",
            json={"code": "X", "name": "X", "company_type": "customer"},
            headers=headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_success_returns_201_with_defaults_and_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        unique_name = f"Ocean Fresh Traders {uuid.uuid4().hex[:8]}"
        body = await _create_company(client, headers, name=unique_name)

        assert body["name"] == unique_name
        assert body["status"] == "active"
        assert body["outstanding_amount"] == "0.00"
        assert body["created_at"] == body["updated_at"]

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(select(Company).where(Company.id == uuid.UUID(body["id"])))
        ).scalar_one()
        assert row.created_by == admin.id
        assert row.updated_by == admin.id
        assert row.tenant_id == admin.tenant_id

    async def test_duplicate_code_is_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_company(client, headers, code="DUP-CODE", name="First Co")
        response = await client.post(
            "/api/v1/companies",
            json={"code": "DUP-CODE", "name": "Second Co", "company_type": "customer"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DUPLICATE_COMPANY_CODE"

    async def test_duplicate_name_is_409_case_insensitive(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_company(client, headers, name="Unique Trading Co")
        response = await client.post(
            "/api/v1/companies",
            json={"code": "OTHER-CODE", "name": "unique trading co", "company_type": "customer"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DUPLICATE_COMPANY_NAME"

    async def test_invalid_email_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/companies",
            json={
                "code": "V-1",
                "name": "V1",
                "company_type": "customer",
                "email": "not-an-email",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "email" in response.json()["error"]["field_errors"]

    async def test_invalid_phone_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/companies",
            json={"code": "V-2", "name": "V2", "company_type": "customer", "phone": "123"},
            headers=headers,
        )
        assert response.status_code == 422
        assert "phone" in response.json()["error"]["field_errors"]

    async def test_invalid_gstin_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/companies",
            json={
                "code": "V-3",
                "name": "V3",
                "company_type": "customer",
                "gstin": "BADGSTIN",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "gstin" in response.json()["error"]["field_errors"]

    async def test_invalid_company_type_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/companies",
            json={"code": "V-4", "name": "V4", "company_type": "not-a-type"},
            headers=headers,
        )
        assert response.status_code == 422
        assert "company_type" in response.json()["error"]["field_errors"]

    async def test_negative_credit_limit_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/companies",
            json={
                "code": "V-5",
                "name": "V5",
                "company_type": "customer",
                "credit_limit": "-100.00",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "credit_limit" in response.json()["error"]["field_errors"]


class TestGetCompany:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/companies/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(f"/api/v1/companies/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_returns_the_company(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_company(client, headers)
        response = await client.get(f"/api/v1/companies/{created['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(f"/api/v1/companies/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "COMPANY_NOT_FOUND"

    async def test_soft_deleted_company_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_company(client, headers)
        await client.delete(f"/api/v1/companies/{created['id']}", headers=headers)
        response = await client.get(f"/api/v1/companies/{created['id']}", headers=headers)
        assert response.status_code == 404

    async def test_other_tenants_company_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_company(client, headers)

        other_tenant = Tenant(name="Other Co", slug=f"other-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_COMPANY_PERMISSIONS
        )

        response = await client.get(f"/api/v1/companies/{created['id']}", headers=other_headers)
        assert response.status_code == 404


class TestListCompanies:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/companies")
        assert response.status_code == 401

    async def test_default_response_shape(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_company(client, headers)
        response = await client.get("/api/v1/companies", headers=headers)
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

    async def test_search_matches_name_case_insensitively(self, client: AsyncClient) -> None:
        # Membership, not exact-list equality: the shared admin tenant used by
        # these API tests may carry other companies from prior test runs or
        # manual exploration - only this test's own two rows are asserted on.
        headers = await _admin_headers(client)
        marker = uuid.uuid4().hex[:8]
        await _create_company(client, headers, name=f"Special Ocean Traders {marker}")
        await _create_company(client, headers, name=f"Irrelevant Co {marker}")

        response = await client.get(
            "/api/v1/companies", params={"q": f"ocean traders {marker}".upper()}, headers=headers
        )
        names = [c["name"] for c in response.json()["data"]]
        assert names == [f"Special Ocean Traders {marker}"]

    async def test_filters_are_combinable(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        marker = uuid.uuid4().hex[:8]
        await _create_company(
            client, headers, city="Mumbai", company_type="customer", name=f"Match Co {marker}"
        )
        await _create_company(
            client,
            headers,
            city="Mumbai",
            company_type="supplier",
            name=f"Wrong Type Co {marker}",
        )
        await _create_company(
            client, headers, city="Kochi", company_type="customer", name=f"Wrong City Co {marker}"
        )

        response = await client.get(
            "/api/v1/companies",
            params={"city": "Mumbai", "company_type": "customer", "q": marker},
            headers=headers,
        )
        names = [c["name"] for c in response.json()["data"]]
        assert names == [f"Match Co {marker}"]

    async def test_sort_ascending_and_descending(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_company(client, headers, code="SORT-B", name="Bravo Sort")
        await _create_company(client, headers, code="SORT-A", name="Alpha Sort")

        asc = await client.get(
            "/api/v1/companies", params={"q": "Sort", "sort": "name"}, headers=headers
        )
        assert [c["name"] for c in asc.json()["data"]] == ["Alpha Sort", "Bravo Sort"]

        desc = await client.get(
            "/api/v1/companies", params={"q": "Sort", "sort": "-name"}, headers=headers
        )
        assert [c["name"] for c in desc.json()["data"]] == ["Bravo Sort", "Alpha Sort"]

    async def test_invalid_sort_field_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/companies", params={"sort": "not_a_field"}, headers=headers
        )
        assert response.status_code == 422

    async def test_pagination_meta_is_correct(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        marker = uuid.uuid4().hex[:8]
        for i in range(3):
            await _create_company(client, headers, code=f"PG-{marker}-{i}", name=f"Pg {marker} {i}")

        response = await client.get(
            "/api/v1/companies",
            params={"q": marker, "page": 1, "page_size": 2, "sort": "code"},
            headers=headers,
        )
        meta = response.json()["meta"]
        assert meta["total_records"] == 3
        assert meta["total_pages"] == 2
        assert meta["current_page"] == 1
        assert meta["page_size"] == 2
        assert meta["has_next"] is True
        assert meta["has_previous"] is False

        page2 = await client.get(
            "/api/v1/companies",
            params={"q": marker, "page": 2, "page_size": 2, "sort": "code"},
            headers=headers,
        )
        meta2 = page2.json()["meta"]
        assert meta2["has_next"] is False
        assert meta2["has_previous"] is True
        assert len(page2.json()["data"]) == 1

    async def test_deleted_companies_are_excluded(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_company(client, headers, name="To Be Deleted")
        await client.delete(f"/api/v1/companies/{created['id']}", headers=headers)

        response = await client.get(
            "/api/v1/companies", params={"q": "To Be Deleted"}, headers=headers
        )
        assert response.json()["data"] == []

    async def test_tenant_isolation_returns_only_own_companies(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        await _create_company(client, headers)

        other_tenant = Tenant(name="Isolated Co", slug=f"isolated-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_COMPANY_PERMISSIONS
        )

        response = await client.get("/api/v1/companies", headers=other_headers)
        assert response.json()["data"] == []


class TestUpdateCompany:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.put(f"/api/v1/companies/{uuid.uuid4()}", json={"name": "New Name"})
        assert response.status_code == 401

    async def test_requires_edit_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["company:view"])
        response = await client.put(
            f"/api/v1/companies/{uuid.uuid4()}", json={"name": "New Name"}, headers=headers
        )
        assert response.status_code == 403

    async def test_partial_update_only_changes_supplied_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_company(
            client, headers, name="Original Name", city="Mumbai", credit_limit="1000.00"
        )

        response = await client.put(
            f"/api/v1/companies/{created['id']}",
            json={"credit_limit": "2000.00"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["credit_limit"] == "2000.00"
        assert body["name"] == "Original Name"
        assert body["city"] == "Mumbai"

    async def test_renaming_to_another_companys_name_is_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_company(client, headers, name="Existing Name")
        target = await _create_company(client, headers, name="Renamable Co")

        response = await client.put(
            f"/api/v1/companies/{target['id']}",
            json={"name": "Existing Name"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DUPLICATE_COMPANY_NAME"

    async def test_renaming_to_its_own_current_name_is_not_a_conflict(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_company(client, headers, name="Stable Name")

        response = await client.put(
            f"/api/v1/companies/{created['id']}",
            json={"name": "Stable Name", "notes": "touched"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["notes"] == "touched"

    async def test_cannot_update_a_deleted_company(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_company(client, headers)
        await client.delete(f"/api/v1/companies/{created['id']}", headers=headers)

        response = await client.put(
            f"/api/v1/companies/{created['id']}",
            json={"name": "Should Not Apply"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "COMPANY_NOT_FOUND"

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            f"/api/v1/companies/{uuid.uuid4()}", json={"name": "X"}, headers=headers
        )
        assert response.status_code == 404

    async def test_invalid_email_on_update_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_company(client, headers)
        response = await client.put(
            f"/api/v1/companies/{created['id']}",
            json={"email": "not-an-email"},
            headers=headers,
        )
        assert response.status_code == 422


class TestDeleteCompany:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.delete(f"/api/v1/companies/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_delete_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["company:view", "company:edit"])
        response = await client.delete(f"/api/v1/companies/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_success_soft_deletes_and_sets_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_company(client, headers)

        response = await client.delete(f"/api/v1/companies/{created['id']}", headers=headers)
        assert response.status_code == 204
        assert response.content == b""

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(select(Company).where(Company.id == uuid.UUID(created["id"])))
        ).scalar_one()
        assert row.deleted_at is not None
        assert row.deleted_by == admin.id

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.delete(f"/api/v1/companies/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404

    async def test_deleting_twice_is_404_the_second_time(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_company(client, headers)
        first = await client.delete(f"/api/v1/companies/{created['id']}", headers=headers)
        second = await client.delete(f"/api/v1/companies/{created['id']}", headers=headers)
        assert first.status_code == 204
        assert second.status_code == 404

    async def test_cannot_delete_another_tenants_company(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_company(client, headers)

        other_tenant = Tenant(name="Other Deleter Co", slug=f"other-del-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_COMPANY_PERMISSIONS
        )

        response = await client.delete(f"/api/v1/companies/{created['id']}", headers=other_headers)
        assert response.status_code == 404

        still_there = await client.get(f"/api/v1/companies/{created['id']}", headers=headers)
        assert still_there.status_code == 200
