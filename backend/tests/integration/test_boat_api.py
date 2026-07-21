import uuid
from datetime import date, timedelta
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.boats.models import Boat

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

# Includes company:view/create too - _create_boat provisions a fresh owning
# company via the API on behalf of these test users, so they need enough
# company-module access for that setup step to succeed.
_ALL_BOAT_PERMISSIONS = [
    "boat:view",
    "boat:create",
    "boat:edit",
    "boat:delete",
    "company:view",
    "company:create",
]
_PAST = (date.today() - timedelta(days=30)).isoformat()
_FUTURE = (date.today() + timedelta(days=30)).isoformat()


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
        "code": f"BCO-{uuid.uuid4().hex[:8]}",
        "name": f"Boat Owner {uuid.uuid4().hex[:8]}",
        "company_type": "customer",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/companies", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_boat(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    company_id: str | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    if company_id is None:
        company = await _create_company(client, headers)
        company_id = company["id"]
    payload: dict[str, Any] = {
        "company_id": company_id,
        "code": f"B-{uuid.uuid4().hex[:8]}",
        "name": f"Boat {uuid.uuid4().hex[:8]}",
        "registration_number": f"REG-{uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/boats", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


class TestCreateBoat:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/boats",
            json={
                "company_id": str(uuid.uuid4()),
                "code": "X",
                "name": "X",
                "registration_number": "X",
            },
        )
        assert response.status_code == 401

    async def test_requires_create_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["boat:view"])
        response = await client.post(
            "/api/v1/boats",
            json={
                "company_id": str(uuid.uuid4()),
                "code": "X",
                "name": "X",
                "registration_number": "X",
            },
            headers=headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_success_returns_201_with_defaults_and_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        unique_name = f"Sea Falcon {uuid.uuid4().hex[:8]}"
        body = await _create_boat(client, headers, name=unique_name)

        assert body["name"] == unique_name
        assert body["is_active"] is True
        assert body["created_at"] == body["updated_at"]

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(select(Boat).where(Boat.id == uuid.UUID(body["id"])))
        ).scalar_one()
        assert row.created_by == admin.id
        assert row.updated_by == admin.id
        assert row.tenant_id == admin.tenant_id

    async def test_duplicate_code_is_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        await _create_boat(client, headers, company_id=company["id"], code="DUP-CODE")
        response = await client.post(
            "/api/v1/boats",
            json={
                "company_id": company["id"],
                "code": "DUP-CODE",
                "name": "Second Boat",
                "registration_number": f"REG-{uuid.uuid4().hex[:8]}",
            },
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DUPLICATE_BOAT_CODE"

    async def test_duplicate_registration_number_is_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        await _create_boat(
            client, headers, company_id=company["id"], registration_number="DUP-REG"
        )
        response = await client.post(
            "/api/v1/boats",
            json={
                "company_id": company["id"],
                "code": f"B-{uuid.uuid4().hex[:8]}",
                "name": "Second Boat",
                "registration_number": "DUP-REG",
            },
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DUPLICATE_BOAT_REGISTRATION_NUMBER"

    async def test_cannot_assign_a_boat_to_another_tenants_company(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """A company id that is real but belongs to a different tenant must
        be rejected exactly like an unknown one - otherwise company_id would
        be a side-channel to probe or attach to other tenants' data."""
        headers = await _admin_headers(client)

        other_tenant = Tenant(
            name="Foreign Owner Co", slug=f"foreign-owner-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_BOAT_PERMISSIONS)
        foreign_company = await _create_company(client, other_headers)

        response = await client.post(
            "/api/v1/boats",
            json={
                "company_id": foreign_company["id"],
                "code": f"B-{uuid.uuid4().hex[:8]}",
                "name": "Cross Tenant Boat",
                "registration_number": f"REG-{uuid.uuid4().hex[:8]}",
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "BOAT_COMPANY_NOT_FOUND"

    async def test_unknown_company_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/boats",
            json={
                "company_id": str(uuid.uuid4()),
                "code": f"B-{uuid.uuid4().hex[:8]}",
                "name": "Orphan Boat",
                "registration_number": f"REG-{uuid.uuid4().hex[:8]}",
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "BOAT_COMPANY_NOT_FOUND"

    async def test_invalid_captain_phone_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        response = await client.post(
            "/api/v1/boats",
            json={
                "company_id": company["id"],
                "code": f"B-{uuid.uuid4().hex[:8]}",
                "name": "V1",
                "registration_number": f"REG-{uuid.uuid4().hex[:8]}",
                "captain_phone": "bad",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "captain_phone" in response.json()["error"]["field_errors"]

    async def test_blank_code_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        response = await client.post(
            "/api/v1/boats",
            json={
                "company_id": company["id"],
                "code": "",
                "name": "V2",
                "registration_number": f"REG-{uuid.uuid4().hex[:8]}",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "code" in response.json()["error"]["field_errors"]

    async def test_blank_registration_number_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        response = await client.post(
            "/api/v1/boats",
            json={
                "company_id": company["id"],
                "code": f"B-{uuid.uuid4().hex[:8]}",
                "name": "V3",
                "registration_number": "",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "registration_number" in response.json()["error"]["field_errors"]

    async def test_missing_company_id_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/boats",
            json={
                "code": f"B-{uuid.uuid4().hex[:8]}",
                "name": "V4",
                "registration_number": f"REG-{uuid.uuid4().hex[:8]}",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "company_id" in response.json()["error"]["field_errors"]


class TestGetBoat:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/boats/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(f"/api/v1/boats/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_returns_the_boat(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_boat(client, headers)
        response = await client.get(f"/api/v1/boats/{created['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(f"/api/v1/boats/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "BOAT_NOT_FOUND"

    async def test_soft_deleted_boat_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_boat(client, headers)
        await client.delete(f"/api/v1/boats/{created['id']}", headers=headers)
        response = await client.get(f"/api/v1/boats/{created['id']}", headers=headers)
        assert response.status_code == 404

    async def test_other_tenants_boat_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_boat(client, headers)

        other_tenant = Tenant(name="Other Boat Co", slug=f"other-boat-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_BOAT_PERMISSIONS)

        response = await client.get(f"/api/v1/boats/{created['id']}", headers=other_headers)
        assert response.status_code == 404


class TestListBoats:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/boats")
        assert response.status_code == 401

    async def test_default_response_shape(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_boat(client, headers)
        response = await client.get("/api/v1/boats", headers=headers)
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

    async def test_search_matches_name_case_insensitively(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(name="Search Boat Tenant", slug=f"search-boat-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_BOAT_PERMISSIONS)

        marker = uuid.uuid4().hex[:8]
        await _create_boat(client, headers, name=f"Special Ocean Falcon {marker}")
        await _create_boat(client, headers, name=f"Irrelevant Boat {marker}")

        response = await client.get(
            "/api/v1/boats", params={"q": f"ocean falcon {marker}".upper()}, headers=headers
        )
        names = [b["name"] for b in response.json()["data"]]
        assert names == [f"Special Ocean Falcon {marker}"]

    async def test_search_matches_captain_name(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Captain Boat Tenant", slug=f"captain-boat-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_BOAT_PERMISSIONS)

        marker = uuid.uuid4().hex[:8]
        await _create_boat(client, headers, captain_name=f"Suresh Patil {marker}")
        await _create_boat(client, headers, captain_name=f"Ramesh Yadav {marker}")

        response = await client.get(
            "/api/v1/boats", params={"q": f"Suresh Patil {marker}"}, headers=headers
        )
        captains = [b["captain_name"] for b in response.json()["data"]]
        assert captains == [f"Suresh Patil {marker}"]

    async def test_filters_are_combinable(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(name="Filter Boat Tenant", slug=f"filter-boat-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_BOAT_PERMISSIONS)

        await _create_boat(
            client, headers, boat_type="trawler", is_active=True, name="Match Boat"
        )
        await _create_boat(
            client, headers, boat_type="trawler", is_active=False, name="Inactive Boat"
        )
        await _create_boat(
            client, headers, boat_type="gillnetter", is_active=True, name="Wrong Type Boat"
        )

        response = await client.get(
            "/api/v1/boats",
            params={"boat_type": "trawler", "is_active": "true"},
            headers=headers,
        )
        names = [b["name"] for b in response.json()["data"]]
        assert names == ["Match Boat"]

    async def test_filters_by_company_id(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Company Filter Tenant", slug=f"co-filter-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_BOAT_PERMISSIONS)

        company_a = await _create_company(client, headers)
        company_b = await _create_company(client, headers)
        target = await _create_boat(client, headers, company_id=company_a["id"], name="Boat A")
        await _create_boat(client, headers, company_id=company_b["id"], name="Boat B")

        response = await client.get(
            "/api/v1/boats", params={"company_id": company_a["id"]}, headers=headers
        )
        ids = [b["id"] for b in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_filters_by_insurance_expired(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Insurance Filter Tenant", slug=f"ins-filter-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_BOAT_PERMISSIONS)

        expired = await _create_boat(client, headers, insurance_expiry=_PAST, name="Expired Boat")
        await _create_boat(client, headers, insurance_expiry=_FUTURE, name="Valid Boat")

        response = await client.get(
            "/api/v1/boats", params={"insurance_expired": "true"}, headers=headers
        )
        ids = [b["id"] for b in response.json()["data"]]
        assert ids == [expired["id"]]

    async def test_sort_ascending_and_descending(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        marker = uuid.uuid4().hex[:8]
        await _create_boat(client, headers, code=f"SORT-B-{marker}", name=f"Bravo Sort {marker}")
        await _create_boat(client, headers, code=f"SORT-A-{marker}", name=f"Alpha Sort {marker}")

        asc = await client.get(
            "/api/v1/boats", params={"q": f"Sort {marker}", "sort": "name"}, headers=headers
        )
        assert [b["name"] for b in asc.json()["data"]] == [
            f"Alpha Sort {marker}",
            f"Bravo Sort {marker}",
        ]

        desc = await client.get(
            "/api/v1/boats", params={"q": f"Sort {marker}", "sort": "-name"}, headers=headers
        )
        assert [b["name"] for b in desc.json()["data"]] == [
            f"Bravo Sort {marker}",
            f"Alpha Sort {marker}",
        ]

    async def test_invalid_sort_field_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/boats", params={"sort": "not_a_field"}, headers=headers
        )
        assert response.status_code == 422

    async def test_default_sort_is_most_recent_first(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        marker = uuid.uuid4().hex[:8]
        first = await _create_boat(client, headers, name=f"First {marker}")
        second = await _create_boat(client, headers, name=f"Second {marker}")

        response = await client.get("/api/v1/boats", params={"q": marker}, headers=headers)
        ids = [b["id"] for b in response.json()["data"]]
        assert ids == [second["id"], first["id"]]

    async def test_search_with_no_matches_returns_empty_page(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/boats", params={"q": f"no-such-boat-{uuid.uuid4().hex}"}, headers=headers
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert body["meta"]["total_records"] == 0
        assert body["meta"]["total_pages"] == 0

    async def test_pagination_meta_is_correct(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        marker = uuid.uuid4().hex[:8]
        for i in range(3):
            await _create_boat(client, headers, code=f"PG-{marker}-{i}", name=f"Pg {marker} {i}")

        response = await client.get(
            "/api/v1/boats",
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
            "/api/v1/boats",
            params={"q": marker, "page": 2, "page_size": 2, "sort": "code"},
            headers=headers,
        )
        meta2 = page2.json()["meta"]
        assert meta2["has_next"] is False
        assert meta2["has_previous"] is True
        assert len(page2.json()["data"]) == 1

    async def test_invalid_page_size_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/boats", params={"page_size": 101}, headers=headers)
        assert response.status_code == 422

    async def test_deleted_boats_are_excluded(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Fresh List Boat Tenant", slug=f"fresh-boat-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        isolated_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_BOAT_PERMISSIONS
        )

        created = await _create_boat(client, isolated_headers, name="To Be Deleted")
        await client.delete(f"/api/v1/boats/{created['id']}", headers=isolated_headers)

        response = await client.get("/api/v1/boats", headers=isolated_headers)
        assert response.json()["data"] == []
        assert response.json()["meta"]["total_records"] == 0

    async def test_tenant_isolation_returns_only_own_boats(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        await _create_boat(client, headers)

        other_tenant = Tenant(name="Isolated Boat Co", slug=f"isolated-boat-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_BOAT_PERMISSIONS)

        response = await client.get("/api/v1/boats", headers=other_headers)
        assert response.json()["data"] == []


class TestUpdateBoat:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.put(f"/api/v1/boats/{uuid.uuid4()}", json={"name": "New Name"})
        assert response.status_code == 401

    async def test_requires_edit_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["boat:view"])
        response = await client.put(
            f"/api/v1/boats/{uuid.uuid4()}", json={"name": "New Name"}, headers=headers
        )
        assert response.status_code == 403

    async def test_partial_update_only_changes_supplied_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_boat(
            client, headers, name="Original Name", boat_type="trawler", captain_name="Suresh"
        )

        response = await client.put(
            f"/api/v1/boats/{created['id']}",
            json={"captain_name": "Ramesh"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["captain_name"] == "Ramesh"
        assert body["name"] == "Original Name"
        assert body["boat_type"] == "trawler"

    async def test_recoding_to_another_boats_code_is_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        await _create_boat(client, headers, company_id=company["id"], code="EXISTING-CODE")
        target = await _create_boat(client, headers, company_id=company["id"], code="RECODABLE")

        response = await client.put(
            f"/api/v1/boats/{target['id']}",
            json={"code": "EXISTING-CODE"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DUPLICATE_BOAT_CODE"

    async def test_reregistering_to_another_boats_registration_number_is_409(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        await _create_boat(
            client, headers, company_id=company["id"], registration_number="EXISTING-REG"
        )
        target = await _create_boat(
            client, headers, company_id=company["id"], registration_number="CHANGEABLE-REG"
        )

        response = await client.put(
            f"/api/v1/boats/{target['id']}",
            json={"registration_number": "EXISTING-REG"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DUPLICATE_BOAT_REGISTRATION_NUMBER"

    async def test_reassigning_to_unknown_company_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_boat(client, headers)

        response = await client.put(
            f"/api/v1/boats/{created['id']}",
            json={"company_id": str(uuid.uuid4())},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "BOAT_COMPANY_NOT_FOUND"

    async def test_reassigning_to_an_existing_company_succeeds(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_boat(client, headers)
        new_company = await _create_company(client, headers)

        response = await client.put(
            f"/api/v1/boats/{created['id']}",
            json={"company_id": new_company["id"]},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["company_id"] == new_company["id"]

    async def test_update_bumps_updated_at_and_sets_updated_by(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_boat(client, headers)

        response = await client.put(
            f"/api/v1/boats/{created['id']}",
            json={"notes": "revised"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["updated_at"] >= created["updated_at"]

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(select(Boat).where(Boat.id == uuid.UUID(created["id"])))
        ).scalar_one()
        assert row.updated_by == admin.id

    async def test_cannot_update_another_tenants_boat(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_boat(client, headers)

        other_tenant = Tenant(
            name="Other Boat Updater", slug=f"other-boat-upd-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_BOAT_PERMISSIONS)

        response = await client.put(
            f"/api/v1/boats/{created['id']}",
            json={"name": "Hijacked Name"},
            headers=other_headers,
        )
        assert response.status_code == 404

        unchanged = await client.get(f"/api/v1/boats/{created['id']}", headers=headers)
        assert unchanged.json()["name"] == created["name"]

    async def test_renaming_to_its_own_current_code_is_not_a_conflict(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_boat(client, headers, code="STABLE-CODE")

        response = await client.put(
            f"/api/v1/boats/{created['id']}",
            json={"code": "STABLE-CODE", "notes": "touched"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["notes"] == "touched"

    async def test_cannot_update_a_deleted_boat(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_boat(client, headers)
        await client.delete(f"/api/v1/boats/{created['id']}", headers=headers)

        response = await client.put(
            f"/api/v1/boats/{created['id']}",
            json={"name": "Should Not Apply"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "BOAT_NOT_FOUND"

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            f"/api/v1/boats/{uuid.uuid4()}", json={"name": "X"}, headers=headers
        )
        assert response.status_code == 404

    async def test_invalid_captain_phone_on_update_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_boat(client, headers)
        response = await client.put(
            f"/api/v1/boats/{created['id']}",
            json={"captain_phone": "bad"},
            headers=headers,
        )
        assert response.status_code == 422


class TestDeleteBoat:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.delete(f"/api/v1/boats/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_delete_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["boat:view", "boat:edit"])
        response = await client.delete(f"/api/v1/boats/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_success_soft_deletes_and_sets_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_boat(client, headers)

        response = await client.delete(f"/api/v1/boats/{created['id']}", headers=headers)
        assert response.status_code == 204
        assert response.content == b""

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(select(Boat).where(Boat.id == uuid.UUID(created["id"])))
        ).scalar_one()
        assert row.deleted_at is not None
        assert row.deleted_by == admin.id

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.delete(f"/api/v1/boats/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404

    async def test_deleting_twice_is_404_the_second_time(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_boat(client, headers)
        first = await client.delete(f"/api/v1/boats/{created['id']}", headers=headers)
        second = await client.delete(f"/api/v1/boats/{created['id']}", headers=headers)
        assert first.status_code == 204
        assert second.status_code == 404

    async def test_cannot_delete_another_tenants_boat(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_boat(client, headers)

        other_tenant = Tenant(
            name="Other Boat Deleter", slug=f"other-boat-del-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_BOAT_PERMISSIONS)

        response = await client.delete(f"/api/v1/boats/{created['id']}", headers=other_headers)
        assert response.status_code == 404

        still_there = await client.get(f"/api/v1/boats/{created['id']}", headers=headers)
        assert still_there.status_code == 200
