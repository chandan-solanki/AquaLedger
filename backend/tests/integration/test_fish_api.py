import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.fish.models import Fish

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

_ALL_FISH_PERMISSIONS = ["fish:view", "fish:manage"]


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


async def _create_fish(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": f"F-{uuid.uuid4().hex[:8]}",
        "name": f"Fish {uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/fish", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


class TestCreateFish:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/fish", json={"code": "X", "name": "X"})
        assert response.status_code == 401

    async def test_requires_manage_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["fish:view"])
        response = await client.post(
            "/api/v1/fish", json={"code": "X", "name": "X"}, headers=headers
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_success_returns_201_with_defaults_and_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        unique_name = f"Pomfret {uuid.uuid4().hex[:8]}"
        body = await _create_fish(client, headers, name=unique_name)

        assert body["name"] == unique_name
        assert body["unit"] == "kg"
        assert body["is_active"] is True
        assert body["created_at"] == body["updated_at"]

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(select(Fish).where(Fish.id == uuid.UUID(body["id"])))
        ).scalar_one()
        assert row.created_by == admin.id
        assert row.updated_by == admin.id
        assert row.tenant_id == admin.tenant_id

    async def test_duplicate_code_is_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_fish(client, headers, code="DUP-CODE", name="First Fish")
        response = await client.post(
            "/api/v1/fish",
            json={"code": "DUP-CODE", "name": "Second Fish"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DUPLICATE_FISH_CODE"

    async def test_duplicate_name_is_409_case_insensitive(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_fish(client, headers, name="Unique Pomfret")
        response = await client.post(
            "/api/v1/fish",
            json={"code": "OTHER-CODE", "name": "unique pomfret"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DUPLICATE_FISH_NAME"

    async def test_invalid_hsn_code_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/fish",
            json={"code": "V-1", "name": "V1", "hsn_code": "bad"},
            headers=headers,
        )
        assert response.status_code == 422
        assert "hsn_code" in response.json()["error"]["field_errors"]

    async def test_invalid_unit_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/fish",
            json={"code": "V-2", "name": "V2", "unit": "not-a-unit"},
            headers=headers,
        )
        assert response.status_code == 422
        assert "unit" in response.json()["error"]["field_errors"]

    async def test_negative_sale_rate_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/fish",
            json={"code": "V-3", "name": "V3", "default_sale_rate": "-100.00"},
            headers=headers,
        )
        assert response.status_code == 422
        assert "default_sale_rate" in response.json()["error"]["field_errors"]

    async def test_blank_code_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/fish", json={"code": "", "name": "V4"}, headers=headers
        )
        assert response.status_code == 422
        assert "code" in response.json()["error"]["field_errors"]


class TestGetFish:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/fish/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(f"/api/v1/fish/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_returns_the_fish(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_fish(client, headers)
        response = await client.get(f"/api/v1/fish/{created['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(f"/api/v1/fish/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "FISH_NOT_FOUND"

    async def test_soft_deleted_fish_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_fish(client, headers)
        await client.delete(f"/api/v1/fish/{created['id']}", headers=headers)
        response = await client.get(f"/api/v1/fish/{created['id']}", headers=headers)
        assert response.status_code == 404

    async def test_other_tenants_fish_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_fish(client, headers)

        other_tenant = Tenant(name="Other Fish Co", slug=f"other-fish-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_FISH_PERMISSIONS)

        response = await client.get(f"/api/v1/fish/{created['id']}", headers=other_headers)
        assert response.status_code == 404


class TestListFish:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/fish")
        assert response.status_code == 401

    async def test_default_response_shape(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_fish(client, headers)
        response = await client.get("/api/v1/fish", headers=headers)
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
        # these API tests may carry other fish from prior test runs - only
        # this test's own two rows are asserted on.
        headers = await _admin_headers(client)
        marker = uuid.uuid4().hex[:8]
        await _create_fish(client, headers, name=f"Special Ocean Pomfret {marker}")
        await _create_fish(client, headers, name=f"Irrelevant Fish {marker}")

        response = await client.get(
            "/api/v1/fish", params={"q": f"ocean pomfret {marker}".upper()}, headers=headers
        )
        names = [f["name"] for f in response.json()["data"]]
        assert names == [f"Special Ocean Pomfret {marker}"]

    async def test_filters_are_combinable(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(name="Filter Test Tenant", slug=f"filter-test-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_FISH_PERMISSIONS)

        await _create_fish(client, headers, category="Whitefish", unit="kg", name="Match Fish")
        await _create_fish(
            client, headers, category="Whitefish", unit="box", name="Wrong Unit Fish"
        )
        await _create_fish(client, headers, category="Shellfish", unit="kg", name="Wrong Cat Fish")

        response = await client.get(
            "/api/v1/fish", params={"category": "Whitefish", "unit": "kg"}, headers=headers
        )
        names = [f["name"] for f in response.json()["data"]]
        assert names == ["Match Fish"]

    async def test_filters_by_is_active(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(name="Active Filter Tenant", slug=f"active-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_FISH_PERMISSIONS)

        await _create_fish(client, headers, is_active=True, name="Active Fish")
        await _create_fish(client, headers, is_active=False, name="Inactive Fish")

        response = await client.get("/api/v1/fish", params={"is_active": "false"}, headers=headers)
        names = [f["name"] for f in response.json()["data"]]
        assert names == ["Inactive Fish"]

    async def test_sort_ascending_and_descending(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        marker = uuid.uuid4().hex[:8]
        await _create_fish(client, headers, code=f"SORT-B-{marker}", name=f"Bravo Sort {marker}")
        await _create_fish(client, headers, code=f"SORT-A-{marker}", name=f"Alpha Sort {marker}")

        asc = await client.get(
            "/api/v1/fish", params={"q": f"Sort {marker}", "sort": "name"}, headers=headers
        )
        assert [f["name"] for f in asc.json()["data"]] == [
            f"Alpha Sort {marker}",
            f"Bravo Sort {marker}",
        ]

        desc = await client.get(
            "/api/v1/fish", params={"q": f"Sort {marker}", "sort": "-name"}, headers=headers
        )
        assert [f["name"] for f in desc.json()["data"]] == [
            f"Bravo Sort {marker}",
            f"Alpha Sort {marker}",
        ]

    async def test_invalid_sort_field_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/fish", params={"sort": "not_a_field"}, headers=headers)
        assert response.status_code == 422

    async def test_default_sort_is_most_recent_first(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        marker = uuid.uuid4().hex[:8]
        first = await _create_fish(client, headers, name=f"First {marker}")
        second = await _create_fish(client, headers, name=f"Second {marker}")

        response = await client.get("/api/v1/fish", params={"q": marker}, headers=headers)
        ids = [f["id"] for f in response.json()["data"]]
        assert ids == [second["id"], first["id"]]

    async def test_search_with_no_matches_returns_empty_page(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/fish", params={"q": f"no-such-fish-{uuid.uuid4().hex}"}, headers=headers
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
            await _create_fish(client, headers, code=f"PG-{marker}-{i}", name=f"Pg {marker} {i}")

        response = await client.get(
            "/api/v1/fish",
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
            "/api/v1/fish",
            params={"q": marker, "page": 2, "page_size": 2, "sort": "code"},
            headers=headers,
        )
        meta2 = page2.json()["meta"]
        assert meta2["has_next"] is False
        assert meta2["has_previous"] is True
        assert len(page2.json()["data"]) == 1

    async def test_invalid_page_size_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/fish", params={"page_size": 101}, headers=headers)
        assert response.status_code == 422

    async def test_deleted_fish_are_excluded(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # A fresh, isolated tenant so the count assertion can't be polluted by
        # other fish left behind by prior tests sharing the admin's tenant.
        other_tenant = Tenant(name="Fresh List Tenant", slug=f"fresh-list-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        isolated_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_FISH_PERMISSIONS
        )

        created = await _create_fish(client, isolated_headers, name="To Be Deleted")
        await client.delete(f"/api/v1/fish/{created['id']}", headers=isolated_headers)

        response = await client.get("/api/v1/fish", headers=isolated_headers)
        assert response.json()["data"] == []
        assert response.json()["meta"]["total_records"] == 0

    async def test_tenant_isolation_returns_only_own_fish(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        await _create_fish(client, headers)

        other_tenant = Tenant(name="Isolated Fish Co", slug=f"isolated-fish-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_FISH_PERMISSIONS)

        response = await client.get("/api/v1/fish", headers=other_headers)
        assert response.json()["data"] == []


class TestUpdateFish:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.put(f"/api/v1/fish/{uuid.uuid4()}", json={"name": "New Name"})
        assert response.status_code == 401

    async def test_requires_manage_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["fish:view"])
        response = await client.put(
            f"/api/v1/fish/{uuid.uuid4()}", json={"name": "New Name"}, headers=headers
        )
        assert response.status_code == 403

    async def test_partial_update_only_changes_supplied_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_fish(
            client,
            headers,
            name="Original Name",
            category="Whitefish",
            default_sale_rate="500.0000",
        )

        response = await client.put(
            f"/api/v1/fish/{created['id']}",
            json={"default_sale_rate": "600.0000"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["default_sale_rate"] == "600.0000"
        assert body["name"] == "Original Name"
        assert body["category"] == "Whitefish"

    async def test_renaming_to_another_fishs_name_is_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_fish(client, headers, name="Existing Name")
        target = await _create_fish(client, headers, name="Renamable Fish")

        response = await client.put(
            f"/api/v1/fish/{target['id']}",
            json={"name": "Existing Name"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DUPLICATE_FISH_NAME"

    async def test_recoding_to_another_fishs_code_is_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_fish(client, headers, code="EXISTING-CODE")
        target = await _create_fish(client, headers, code="RECODABLE")

        response = await client.put(
            f"/api/v1/fish/{target['id']}",
            json={"code": "EXISTING-CODE"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DUPLICATE_FISH_CODE"

    async def test_updates_category_unit_and_is_active(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_fish(
            client, headers, category="Shellfish", unit="piece", is_active=True
        )

        response = await client.put(
            f"/api/v1/fish/{created['id']}",
            json={"category": "Whitefish", "unit": "box", "is_active": False},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["category"] == "Whitefish"
        assert body["unit"] == "box"
        assert body["is_active"] is False

    async def test_update_bumps_updated_at_and_sets_updated_by(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_fish(client, headers)

        response = await client.put(
            f"/api/v1/fish/{created['id']}",
            json={"description": "revised"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["updated_at"] >= created["updated_at"]

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(select(Fish).where(Fish.id == uuid.UUID(created["id"])))
        ).scalar_one()
        assert row.updated_by == admin.id

    async def test_cannot_update_another_tenants_fish(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_fish(client, headers)

        other_tenant = Tenant(
            name="Other Fish Updater", slug=f"other-fish-upd-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_FISH_PERMISSIONS)

        response = await client.put(
            f"/api/v1/fish/{created['id']}",
            json={"name": "Hijacked Name"},
            headers=other_headers,
        )
        assert response.status_code == 404

        unchanged = await client.get(f"/api/v1/fish/{created['id']}", headers=headers)
        assert unchanged.json()["name"] == created["name"]

    async def test_renaming_to_its_own_current_name_is_not_a_conflict(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_fish(client, headers, name="Stable Name")

        response = await client.put(
            f"/api/v1/fish/{created['id']}",
            json={"name": "Stable Name", "description": "touched"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["description"] == "touched"

    async def test_cannot_update_a_deleted_fish(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_fish(client, headers)
        await client.delete(f"/api/v1/fish/{created['id']}", headers=headers)

        response = await client.put(
            f"/api/v1/fish/{created['id']}",
            json={"name": "Should Not Apply"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "FISH_NOT_FOUND"

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            f"/api/v1/fish/{uuid.uuid4()}", json={"name": "X"}, headers=headers
        )
        assert response.status_code == 404

    async def test_invalid_hsn_code_on_update_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_fish(client, headers)
        response = await client.put(
            f"/api/v1/fish/{created['id']}",
            json={"hsn_code": "bad"},
            headers=headers,
        )
        assert response.status_code == 422


class TestDeleteFish:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.delete(f"/api/v1/fish/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_manage_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["fish:view"])
        response = await client.delete(f"/api/v1/fish/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_success_soft_deletes_and_sets_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_fish(client, headers)

        response = await client.delete(f"/api/v1/fish/{created['id']}", headers=headers)
        assert response.status_code == 204
        assert response.content == b""

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(select(Fish).where(Fish.id == uuid.UUID(created["id"])))
        ).scalar_one()
        assert row.deleted_at is not None
        assert row.deleted_by == admin.id

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.delete(f"/api/v1/fish/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404

    async def test_deleting_twice_is_404_the_second_time(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_fish(client, headers)
        first = await client.delete(f"/api/v1/fish/{created['id']}", headers=headers)
        second = await client.delete(f"/api/v1/fish/{created['id']}", headers=headers)
        assert first.status_code == 204
        assert second.status_code == 404

    async def test_cannot_delete_another_tenants_fish(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_fish(client, headers)

        other_tenant = Tenant(
            name="Other Fish Deleter", slug=f"other-fish-del-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_FISH_PERMISSIONS)

        response = await client.delete(f"/api/v1/fish/{created['id']}", headers=other_headers)
        assert response.status_code == 404

        still_there = await client.get(f"/api/v1/fish/{created['id']}", headers=headers)
        assert still_there.status_code == 200
