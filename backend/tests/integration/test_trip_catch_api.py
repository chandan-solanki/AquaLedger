import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.trip_catches.models import TripCatch

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

# _create_trip_catch provisions a fresh RETURNED trip (and that trip's boat
# and company) plus a fresh fish via the API by default, so test users need
# enough trip/boat/company/fish access for that setup to succeed too.
_ALL_TRIP_CATCH_PERMISSIONS = [
    "trip_catch:view",
    "trip_catch:create",
    "trip_catch:edit",
    "trip_catch:delete",
    "trip:view",
    "trip:create",
    "trip:edit",
    "boat:view",
    "boat:create",
    "company:view",
    "company:create",
    "fish:view",
    "fish:manage",
]
_DEPARTURE = "2026-06-01T04:00:00Z"
_RETURN = "2026-06-05T10:00:00Z"
_LANDING_DATE = "2026-06-05"


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
        "code": f"TCCO-{uuid.uuid4().hex[:8]}",
        "name": f"Catch Owner {uuid.uuid4().hex[:8]}",
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
        "code": f"TCB-{uuid.uuid4().hex[:8]}",
        "name": f"Boat {uuid.uuid4().hex[:8]}",
        "registration_number": f"TCREG-{uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/boats", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_trip(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    boat_id: str | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    if boat_id is None:
        boat = await _create_boat(client, headers)
        boat_id = boat["id"]
    payload: dict[str, Any] = {
        "boat_id": boat_id,
        "trip_number": f"TCTRIP-{uuid.uuid4().hex[:8]}",
        "trip_type": "fishing",
        "departure_datetime": _DEPARTURE,
    }
    payload.update(overrides)
    response = await client.post("/api/v1/trips", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _return_trip(
    client: AsyncClient, headers: dict[str, str], trip_id: str
) -> dict[str, Any]:
    response = await client.put(
        f"/api/v1/trips/{trip_id}",
        json={"status": "returned", "actual_return_datetime": _RETURN},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_returned_trip(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    trip = await _create_trip(client, headers, **overrides)
    return await _return_trip(client, headers, trip["id"])


async def _create_fish(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": f"TCFISH-{uuid.uuid4().hex[:8]}",
        "name": f"Fish {uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/fish", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_trip_catch(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    trip_id: str | None = None,
    fish_id: str | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    if trip_id is None:
        trip_id = (await _create_returned_trip(client, headers))["id"]
    if fish_id is None:
        fish_id = (await _create_fish(client, headers))["id"]
    payload: dict[str, Any] = {
        "trip_id": trip_id,
        "fish_id": fish_id,
        "quantity_caught": "100.500",
        "landing_date": _LANDING_DATE,
    }
    payload.update(overrides)
    response = await client.post("/api/v1/trip-catches", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


class TestCreateTripCatch:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/trip-catches",
            json={
                "trip_id": str(uuid.uuid4()),
                "fish_id": str(uuid.uuid4()),
                "quantity_caught": "10",
                "landing_date": _LANDING_DATE,
            },
        )
        assert response.status_code == 401

    async def test_requires_create_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["trip_catch:view"])
        response = await client.post(
            "/api/v1/trip-catches",
            json={
                "trip_id": str(uuid.uuid4()),
                "fish_id": str(uuid.uuid4()),
                "quantity_caught": "10",
                "landing_date": _LANDING_DATE,
            },
            headers=headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_success_forces_quantities_and_sets_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        body = await _create_trip_catch(client, headers, grade="A")

        assert body["grade"] == "A"
        assert body["quantity_caught"] == "100.500"
        assert body["available_quantity"] == "100.500"
        assert body["sold_quantity"] == "0.000"
        assert body["waste_quantity"] == "0.000"
        assert body["created_at"] == body["updated_at"]

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(select(TripCatch).where(TripCatch.id == uuid.UUID(body["id"])))
        ).scalar_one()
        assert row.created_by == admin.id
        assert row.updated_by == admin.id
        assert row.tenant_id == admin.tenant_id

    async def test_client_supplied_available_sold_waste_quantity_is_ignored(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        body = await _create_trip_catch(
            client,
            headers,
            available_quantity="1",
            sold_quantity="1",
            waste_quantity="1",
        )
        assert body["available_quantity"] == "100.500"
        assert body["sold_quantity"] == "0.000"
        assert body["waste_quantity"] == "0.000"

    async def test_unknown_trip_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        fish = await _create_fish(client, headers)
        response = await client.post(
            "/api/v1/trip-catches",
            json={
                "trip_id": str(uuid.uuid4()),
                "fish_id": fish["id"],
                "quantity_caught": "10",
                "landing_date": _LANDING_DATE,
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRIP_CATCH_TRIP_NOT_FOUND"

    async def test_trip_not_returned_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        trip = await _create_trip(client, headers)  # status defaults to "planned"
        fish = await _create_fish(client, headers)
        response = await client.post(
            "/api/v1/trip-catches",
            json={
                "trip_id": trip["id"],
                "fish_id": fish["id"],
                "quantity_caught": "10",
                "landing_date": _LANDING_DATE,
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "TRIP_CATCH_TRIP_NOT_RETURNED"

    async def test_unknown_fish_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        trip = await _create_returned_trip(client, headers)
        response = await client.post(
            "/api/v1/trip-catches",
            json={
                "trip_id": trip["id"],
                "fish_id": str(uuid.uuid4()),
                "quantity_caught": "10",
                "landing_date": _LANDING_DATE,
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRIP_CATCH_FISH_NOT_FOUND"

    async def test_cannot_use_another_tenants_trip(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        fish = await _create_fish(client, headers)

        other_tenant = Tenant(
            name="Foreign Trip Owner", slug=f"foreign-trip-owner-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_CATCH_PERMISSIONS
        )
        foreign_trip = await _create_returned_trip(client, other_headers)

        response = await client.post(
            "/api/v1/trip-catches",
            json={
                "trip_id": foreign_trip["id"],
                "fish_id": fish["id"],
                "quantity_caught": "10",
                "landing_date": _LANDING_DATE,
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRIP_CATCH_TRIP_NOT_FOUND"

    async def test_cannot_use_another_tenants_fish(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        trip = await _create_returned_trip(client, headers)

        other_tenant = Tenant(
            name="Foreign Fish Owner", slug=f"foreign-fish-owner-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_CATCH_PERMISSIONS
        )
        foreign_fish = await _create_fish(client, other_headers)

        response = await client.post(
            "/api/v1/trip-catches",
            json={
                "trip_id": trip["id"],
                "fish_id": foreign_fish["id"],
                "quantity_caught": "10",
                "landing_date": _LANDING_DATE,
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRIP_CATCH_FISH_NOT_FOUND"

    async def test_zero_quantity_caught_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        trip = await _create_returned_trip(client, headers)
        fish = await _create_fish(client, headers)
        response = await client.post(
            "/api/v1/trip-catches",
            json={
                "trip_id": trip["id"],
                "fish_id": fish["id"],
                "quantity_caught": "0",
                "landing_date": _LANDING_DATE,
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "quantity_caught" in response.json()["error"]["field_errors"]

    async def test_negative_quantity_caught_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        trip = await _create_returned_trip(client, headers)
        fish = await _create_fish(client, headers)
        response = await client.post(
            "/api/v1/trip-catches",
            json={
                "trip_id": trip["id"],
                "fish_id": fish["id"],
                "quantity_caught": "-5",
                "landing_date": _LANDING_DATE,
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "quantity_caught" in response.json()["error"]["field_errors"]

    async def test_missing_trip_id_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        fish = await _create_fish(client, headers)
        response = await client.post(
            "/api/v1/trip-catches",
            json={"fish_id": fish["id"], "quantity_caught": "10", "landing_date": _LANDING_DATE},
            headers=headers,
        )
        assert response.status_code == 422
        assert "trip_id" in response.json()["error"]["field_errors"]

    async def test_missing_landing_date_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        trip = await _create_returned_trip(client, headers)
        fish = await _create_fish(client, headers)
        response = await client.post(
            "/api/v1/trip-catches",
            json={"trip_id": trip["id"], "fish_id": fish["id"], "quantity_caught": "10"},
            headers=headers,
        )
        assert response.status_code == 422
        assert "landing_date" in response.json()["error"]["field_errors"]

    async def test_invalid_grade_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        trip = await _create_returned_trip(client, headers)
        fish = await _create_fish(client, headers)
        response = await client.post(
            "/api/v1/trip-catches",
            json={
                "trip_id": trip["id"],
                "fish_id": fish["id"],
                "grade": "Z",
                "quantity_caught": "10",
                "landing_date": _LANDING_DATE,
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "grade" in response.json()["error"]["field_errors"]


class TestGetTripCatch:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/trip-catches/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(f"/api/v1/trip-catches/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_returns_the_trip_catch(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_catch(client, headers)
        response = await client.get(f"/api/v1/trip-catches/{created['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(f"/api/v1/trip-catches/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRIP_CATCH_NOT_FOUND"

    async def test_soft_deleted_trip_catch_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_catch(client, headers)
        await client.delete(f"/api/v1/trip-catches/{created['id']}", headers=headers)
        response = await client.get(f"/api/v1/trip-catches/{created['id']}", headers=headers)
        assert response.status_code == 404

    async def test_other_tenants_trip_catch_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_catch(client, headers)

        other_tenant = Tenant(name="Other Catch Co", slug=f"other-catch-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_CATCH_PERMISSIONS
        )

        response = await client.get(f"/api/v1/trip-catches/{created['id']}", headers=other_headers)
        assert response.status_code == 404


class TestListTripCatches:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/trip-catches")
        assert response.status_code == 401

    async def test_default_response_shape(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_trip_catch(client, headers)
        response = await client.get("/api/v1/trip-catches", headers=headers)
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

    async def test_search_matches_trip_number(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Search Catch Trip Tenant", slug=f"search-catch-trip-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_TRIP_CATCH_PERMISSIONS)

        marker = uuid.uuid4().hex[:8]
        matching_trip = await _create_returned_trip(
            client, headers, trip_number=f"SPECIAL-{marker}"
        )
        other_trip = await _create_returned_trip(
            client, headers, trip_number=f"IRRELEVANT-{marker}-X"
        )
        target = await _create_trip_catch(client, headers, trip_id=matching_trip["id"])
        await _create_trip_catch(client, headers, trip_id=other_trip["id"])

        response = await client.get(
            "/api/v1/trip-catches", params={"q": f"special-{marker}"}, headers=headers
        )
        ids = [c["id"] for c in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_search_matches_fish_name(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Search Catch Fish Tenant", slug=f"search-catch-fish-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_TRIP_CATCH_PERMISSIONS)

        marker = uuid.uuid4().hex[:8]
        matching_fish = await _create_fish(client, headers, name=f"Mackerel {marker}")
        other_fish = await _create_fish(client, headers, name=f"Irrelevant Fish {marker}")
        target = await _create_trip_catch(client, headers, fish_id=matching_fish["id"])
        await _create_trip_catch(client, headers, fish_id=other_fish["id"])

        response = await client.get(
            "/api/v1/trip-catches", params={"q": f"mackerel {marker}".upper()}, headers=headers
        )
        ids = [c["id"] for c in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_filters_by_trip_id(self, client: AsyncClient, db_session: AsyncSession) -> None:
        other_tenant = Tenant(
            name="Trip Filter Catch Tenant", slug=f"trip-filter-catch-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_TRIP_CATCH_PERMISSIONS)

        trip_a = await _create_returned_trip(client, headers)
        trip_b = await _create_returned_trip(client, headers)
        target = await _create_trip_catch(client, headers, trip_id=trip_a["id"])
        await _create_trip_catch(client, headers, trip_id=trip_b["id"])

        response = await client.get(
            "/api/v1/trip-catches", params={"trip_id": trip_a["id"]}, headers=headers
        )
        ids = [c["id"] for c in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_filters_by_fish_id(self, client: AsyncClient, db_session: AsyncSession) -> None:
        other_tenant = Tenant(
            name="Fish Filter Catch Tenant", slug=f"fish-filter-catch-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_TRIP_CATCH_PERMISSIONS)

        fish_a = await _create_fish(client, headers)
        fish_b = await _create_fish(client, headers)
        target = await _create_trip_catch(client, headers, fish_id=fish_a["id"])
        await _create_trip_catch(client, headers, fish_id=fish_b["id"])

        response = await client.get(
            "/api/v1/trip-catches", params={"fish_id": fish_a["id"]}, headers=headers
        )
        ids = [c["id"] for c in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_filters_by_grade(self, client: AsyncClient, db_session: AsyncSession) -> None:
        other_tenant = Tenant(
            name="Grade Filter Catch Tenant", slug=f"grade-filter-catch-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_TRIP_CATCH_PERMISSIONS)

        await _create_trip_catch(client, headers, grade="A")
        graded_b = await _create_trip_catch(client, headers, grade="B")

        response = await client.get("/api/v1/trip-catches", params={"grade": "B"}, headers=headers)
        ids = [c["id"] for c in response.json()["data"]]
        assert ids == [graded_b["id"]]

    async def test_filters_by_landing_date_range(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Landing Filter Catch Tenant", slug=f"landing-filter-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_TRIP_CATCH_PERMISSIONS)

        in_range = await _create_trip_catch(client, headers, landing_date="2026-06-05")
        await _create_trip_catch(client, headers, landing_date="2026-09-15")

        response = await client.get(
            "/api/v1/trip-catches",
            params={"landing_date_from": "2026-06-01", "landing_date_to": "2026-06-30"},
            headers=headers,
        )
        ids = [c["id"] for c in response.json()["data"]]
        assert ids == [in_range["id"]]

    async def test_sort_ascending_and_descending_by_landing_date(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        marker = uuid.uuid4().hex[:8]
        fish = await _create_fish(client, headers, name=f"Sort Fish {marker}")
        older = await _create_trip_catch(
            client, headers, fish_id=fish["id"], landing_date="2026-06-01"
        )
        newer = await _create_trip_catch(
            client, headers, fish_id=fish["id"], landing_date="2026-06-20"
        )

        asc = await client.get(
            "/api/v1/trip-catches",
            params={"fish_id": fish["id"], "sort": "landing_date"},
            headers=headers,
        )
        assert [c["id"] for c in asc.json()["data"]] == [older["id"], newer["id"]]

        desc = await client.get(
            "/api/v1/trip-catches",
            params={"fish_id": fish["id"], "sort": "-landing_date"},
            headers=headers,
        )
        assert [c["id"] for c in desc.json()["data"]] == [newer["id"], older["id"]]

    async def test_sort_by_quantity_caught(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        fish = await _create_fish(client, headers)
        small = await _create_trip_catch(
            client, headers, fish_id=fish["id"], quantity_caught="10.000"
        )
        large = await _create_trip_catch(
            client, headers, fish_id=fish["id"], quantity_caught="90.000"
        )

        response = await client.get(
            "/api/v1/trip-catches",
            params={"fish_id": fish["id"], "sort": "quantity_caught"},
            headers=headers,
        )
        assert [c["id"] for c in response.json()["data"]] == [small["id"], large["id"]]

    async def test_invalid_sort_field_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/trip-catches", params={"sort": "trip_id"}, headers=headers
        )
        assert response.status_code == 422

    async def test_default_sort_is_most_recent_first(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        fish = await _create_fish(client, headers)
        first = await _create_trip_catch(client, headers, fish_id=fish["id"])
        second = await _create_trip_catch(client, headers, fish_id=fish["id"])

        response = await client.get(
            "/api/v1/trip-catches", params={"fish_id": fish["id"]}, headers=headers
        )
        ids = [c["id"] for c in response.json()["data"]]
        assert ids == [second["id"], first["id"]]

    async def test_search_with_no_matches_returns_empty_page(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/trip-catches",
            params={"q": f"no-such-catch-{uuid.uuid4().hex}"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert body["meta"]["total_records"] == 0
        assert body["meta"]["total_pages"] == 0

    async def test_pagination_meta_is_correct(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        fish = await _create_fish(client, headers)
        for _ in range(3):
            await _create_trip_catch(client, headers, fish_id=fish["id"])

        response = await client.get(
            "/api/v1/trip-catches",
            params={"fish_id": fish["id"], "page": 1, "page_size": 2, "sort": "-created_at"},
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
            "/api/v1/trip-catches",
            params={"fish_id": fish["id"], "page": 2, "page_size": 2, "sort": "-created_at"},
            headers=headers,
        )
        meta2 = page2.json()["meta"]
        assert meta2["has_next"] is False
        assert meta2["has_previous"] is True
        assert len(page2.json()["data"]) == 1

    async def test_invalid_page_size_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/trip-catches", params={"page_size": 101}, headers=headers
        )
        assert response.status_code == 422

    async def test_deleted_trip_catches_are_excluded(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Fresh List Catch Tenant", slug=f"fresh-catch-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        isolated_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_CATCH_PERMISSIONS
        )

        created = await _create_trip_catch(client, isolated_headers)
        await client.delete(f"/api/v1/trip-catches/{created['id']}", headers=isolated_headers)

        response = await client.get("/api/v1/trip-catches", headers=isolated_headers)
        assert response.json()["data"] == []
        assert response.json()["meta"]["total_records"] == 0

    async def test_tenant_isolation_returns_only_own_trip_catches(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        await _create_trip_catch(client, headers)

        other_tenant = Tenant(
            name="Isolated Catch Co", slug=f"isolated-catch-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_CATCH_PERMISSIONS
        )

        response = await client.get("/api/v1/trip-catches", headers=other_headers)
        assert response.json()["data"] == []


class TestUpdateTripCatch:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.put(f"/api/v1/trip-catches/{uuid.uuid4()}", json={"remarks": "x"})
        assert response.status_code == 401

    async def test_requires_edit_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["trip_catch:view"])
        response = await client.put(
            f"/api/v1/trip-catches/{uuid.uuid4()}", json={"remarks": "x"}, headers=headers
        )
        assert response.status_code == 403

    async def test_partial_update_only_changes_supplied_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_catch(client, headers, landing_port="Sassoon Dock")

        response = await client.put(
            f"/api/v1/trip-catches/{created['id']}",
            json={"remarks": "Partial sale"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["remarks"] == "Partial sale"
        assert body["landing_port"] == "Sassoon Dock"

    async def test_valid_quantity_reallocation_succeeds(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_catch(client, headers, quantity_caught="100.000")

        response = await client.put(
            f"/api/v1/trip-catches/{created['id']}",
            json={"sold_quantity": "40.000", "available_quantity": "60.000"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["sold_quantity"] == "40.000"
        assert body["available_quantity"] == "60.000"
        assert body["waste_quantity"] == "0.000"

    async def test_quantity_invariant_violation_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_catch(client, headers, quantity_caught="100.000")

        response = await client.put(
            f"/api/v1/trip-catches/{created['id']}",
            json={"sold_quantity": "200.000"},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "TRIP_CATCH_QUANTITY_INVARIANT_VIOLATION"

    async def test_second_update_must_account_for_the_first_committed_change(
        self, client: AsyncClient
    ) -> None:
        """Documents the scenario the SELECT ... FOR UPDATE lock in
        TripCatchService.update() exists for: a second writer must merge
        against the *latest committed* row, not whatever it read before the
        first writer committed. Sequentially here (this suite can't drive
        two genuinely concurrent transactions - see
        TestGetByIdForUpdate's docstring in test_trip_catch_repository.py),
        but the merge-against-current-state logic under test is identical
        to what runs when two requests race for real."""
        headers = await _admin_headers(client)
        created = await _create_trip_catch(client, headers, quantity_caught="100.000")

        first = await client.put(
            f"/api/v1/trip-catches/{created['id']}",
            json={"sold_quantity": "40.000", "available_quantity": "60.000"},
            headers=headers,
        )
        assert first.status_code == 200

        # A second writer that only intended to record 10 units of wastage,
        # unaware sold_quantity is now 40 (not the 0 it was when this writer
        # last read the row) - 60 (unchanged) + 40 (first writer's
        # committed change) + 10 = 110 != 100.
        second = await client.put(
            f"/api/v1/trip-catches/{created['id']}",
            json={"waste_quantity": "10.000"},
            headers=headers,
        )
        assert second.status_code == 422
        assert second.json()["error"]["code"] == "TRIP_CATCH_QUANTITY_INVARIANT_VIOLATION"

        unchanged = await client.get(f"/api/v1/trip-catches/{created['id']}", headers=headers)
        body = unchanged.json()
        assert body["sold_quantity"] == "40.000"
        assert body["available_quantity"] == "60.000"
        assert body["waste_quantity"] == "0.000"

    async def test_negative_sold_quantity_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_catch(client, headers)

        response = await client.put(
            f"/api/v1/trip-catches/{created['id']}",
            json={"sold_quantity": "-1"},
            headers=headers,
        )
        assert response.status_code == 422
        assert "sold_quantity" in response.json()["error"]["field_errors"]

    async def test_reassign_trip_to_unknown_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_catch(client, headers)

        response = await client.put(
            f"/api/v1/trip-catches/{created['id']}",
            json={"trip_id": str(uuid.uuid4())},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRIP_CATCH_TRIP_NOT_FOUND"

    async def test_reassign_trip_not_returned_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_catch(client, headers)
        not_returned_trip = await _create_trip(client, headers)  # still "planned"

        response = await client.put(
            f"/api/v1/trip-catches/{created['id']}",
            json={"trip_id": not_returned_trip["id"]},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "TRIP_CATCH_TRIP_NOT_RETURNED"

    async def test_reassign_fish_to_unknown_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_catch(client, headers)

        response = await client.put(
            f"/api/v1/trip-catches/{created['id']}",
            json={"fish_id": str(uuid.uuid4())},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRIP_CATCH_FISH_NOT_FOUND"

    async def test_invalid_grade_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_catch(client, headers)

        response = await client.put(
            f"/api/v1/trip-catches/{created['id']}",
            json={"grade": "Z"},
            headers=headers,
        )
        assert response.status_code == 422
        assert "grade" in response.json()["error"]["field_errors"]

    async def test_update_bumps_updated_at_and_sets_updated_by(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_catch(client, headers)

        response = await client.put(
            f"/api/v1/trip-catches/{created['id']}",
            json={"remarks": "revised"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["updated_at"] >= created["updated_at"]

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(
                select(TripCatch).where(TripCatch.id == uuid.UUID(created["id"]))
            )
        ).scalar_one()
        assert row.updated_by == admin.id

    async def test_cannot_update_another_tenants_trip_catch(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_catch(client, headers)

        other_tenant = Tenant(
            name="Other Catch Updater", slug=f"other-catch-upd-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_CATCH_PERMISSIONS
        )

        response = await client.put(
            f"/api/v1/trip-catches/{created['id']}",
            json={"remarks": "Hijacked"},
            headers=other_headers,
        )
        assert response.status_code == 404

        unchanged = await client.get(f"/api/v1/trip-catches/{created['id']}", headers=headers)
        assert unchanged.json()["remarks"] is None

    async def test_cannot_update_a_deleted_trip_catch(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_catch(client, headers)
        await client.delete(f"/api/v1/trip-catches/{created['id']}", headers=headers)

        response = await client.put(
            f"/api/v1/trip-catches/{created['id']}",
            json={"remarks": "Should Not Apply"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRIP_CATCH_NOT_FOUND"

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            f"/api/v1/trip-catches/{uuid.uuid4()}", json={"remarks": "x"}, headers=headers
        )
        assert response.status_code == 404


class TestDeleteTripCatch:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.delete(f"/api/v1/trip-catches/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_delete_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(
            db_session, tenant_id, ["trip_catch:view", "trip_catch:edit"]
        )
        response = await client.delete(f"/api/v1/trip-catches/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_success_soft_deletes_and_sets_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_catch(client, headers)

        response = await client.delete(f"/api/v1/trip-catches/{created['id']}", headers=headers)
        assert response.status_code == 204
        assert response.content == b""

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(
                select(TripCatch).where(TripCatch.id == uuid.UUID(created["id"]))
            )
        ).scalar_one()
        assert row.deleted_at is not None
        assert row.deleted_by == admin.id

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.delete(f"/api/v1/trip-catches/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404

    async def test_deleting_twice_is_404_the_second_time(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_catch(client, headers)
        first = await client.delete(f"/api/v1/trip-catches/{created['id']}", headers=headers)
        second = await client.delete(f"/api/v1/trip-catches/{created['id']}", headers=headers)
        assert first.status_code == 204
        assert second.status_code == 404

    async def test_cannot_delete_another_tenants_trip_catch(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_catch(client, headers)

        other_tenant = Tenant(
            name="Other Catch Deleter", slug=f"other-catch-del-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_CATCH_PERMISSIONS
        )

        response = await client.delete(
            f"/api/v1/trip-catches/{created['id']}", headers=other_headers
        )
        assert response.status_code == 404

        still_there = await client.get(f"/api/v1/trip-catches/{created['id']}", headers=headers)
        assert still_there.status_code == 200
