import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.trips.models import Trip

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

# _create_trip provisions a fresh owning boat (and that boat's owning
# company) via the API by default, so test users need enough boat/company
# access for that setup step to succeed too.
_ALL_TRIP_PERMISSIONS = [
    "trip:view",
    "trip:create",
    "trip:edit",
    "trip:delete",
    "boat:view",
    "boat:create",
    "company:view",
    "company:create",
]
_DEPARTURE = "2026-08-01T04:00:00Z"


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
        "code": f"TCO-{uuid.uuid4().hex[:8]}",
        "name": f"Trip Owner {uuid.uuid4().hex[:8]}",
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
        "code": f"TB-{uuid.uuid4().hex[:8]}",
        "name": f"Boat {uuid.uuid4().hex[:8]}",
        "registration_number": f"TREG-{uuid.uuid4().hex[:8]}",
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
        "trip_number": f"TRIP-{uuid.uuid4().hex[:8]}",
        "trip_type": "fishing",
        "departure_datetime": _DEPARTURE,
    }
    payload.update(overrides)
    response = await client.post("/api/v1/trips", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


class TestCreateTrip:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/trips",
            json={
                "boat_id": str(uuid.uuid4()),
                "trip_number": "X",
                "trip_type": "fishing",
                "departure_datetime": _DEPARTURE,
            },
        )
        assert response.status_code == 401

    async def test_requires_create_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["trip:view"])
        response = await client.post(
            "/api/v1/trips",
            json={
                "boat_id": str(uuid.uuid4()),
                "trip_number": "X",
                "trip_type": "fishing",
                "departure_datetime": _DEPARTURE,
            },
            headers=headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_success_returns_201_with_defaults_and_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        unique_number = f"TRIP-{uuid.uuid4().hex[:8]}"
        body = await _create_trip(client, headers, trip_number=unique_number)

        assert body["trip_number"] == unique_number
        assert body["status"] == "planned"
        assert body["is_active"] is True
        assert body["created_at"] == body["updated_at"]

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(select(Trip).where(Trip.id == uuid.UUID(body["id"])))
        ).scalar_one()
        assert row.created_by == admin.id
        assert row.updated_by == admin.id
        assert row.tenant_id == admin.tenant_id

    async def test_duplicate_trip_number_is_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_trip(client, headers, trip_number="DUP-TRIP")
        response = await client.post(
            "/api/v1/trips",
            json={
                "boat_id": (await _create_boat(client, headers))["id"],
                "trip_number": "DUP-TRIP",
                "trip_type": "fishing",
                "departure_datetime": _DEPARTURE,
            },
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DUPLICATE_TRIP_NUMBER"

    async def test_unknown_boat_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/trips",
            json={
                "boat_id": str(uuid.uuid4()),
                "trip_number": f"TRIP-{uuid.uuid4().hex[:8]}",
                "trip_type": "fishing",
                "departure_datetime": _DEPARTURE,
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRIP_BOAT_NOT_FOUND"

    async def test_cannot_assign_a_trip_to_another_tenants_boat(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)

        other_tenant = Tenant(
            name="Foreign Boat Owner", slug=f"foreign-boat-owner-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_TRIP_PERMISSIONS)
        foreign_boat = await _create_boat(client, other_headers)

        response = await client.post(
            "/api/v1/trips",
            json={
                "boat_id": foreign_boat["id"],
                "trip_number": f"TRIP-{uuid.uuid4().hex[:8]}",
                "trip_type": "fishing",
                "departure_datetime": _DEPARTURE,
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRIP_BOAT_NOT_FOUND"

    async def test_inactive_boat_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        boat = await _create_boat(client, headers, is_active=False)
        response = await client.post(
            "/api/v1/trips",
            json={
                "boat_id": boat["id"],
                "trip_number": f"TRIP-{uuid.uuid4().hex[:8]}",
                "trip_type": "fishing",
                "departure_datetime": _DEPARTURE,
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "TRIP_BOAT_NOT_ACTIVE"

    async def test_boat_already_has_an_active_trip_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        boat = await _create_boat(client, headers)
        await _create_trip(client, headers, boat_id=boat["id"])

        response = await client.post(
            "/api/v1/trips",
            json={
                "boat_id": boat["id"],
                "trip_number": f"TRIP-{uuid.uuid4().hex[:8]}",
                "trip_type": "fishing",
                "departure_datetime": _DEPARTURE,
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "TRIP_BOAT_ALREADY_ACTIVE"

    async def test_non_active_status_does_not_trigger_active_trip_rule(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        boat = await _create_boat(client, headers)
        await _create_trip(client, headers, boat_id=boat["id"])

        response = await client.post(
            "/api/v1/trips",
            json={
                "boat_id": boat["id"],
                "trip_number": f"TRIP-{uuid.uuid4().hex[:8]}",
                "trip_type": "fishing",
                "departure_datetime": _DEPARTURE,
                "status": "cancelled",
            },
            headers=headers,
        )
        assert response.status_code == 201

    async def test_actual_return_before_departure_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/trips",
            json={
                "boat_id": (await _create_boat(client, headers))["id"],
                "trip_number": f"TRIP-{uuid.uuid4().hex[:8]}",
                "trip_type": "fishing",
                "departure_datetime": "2026-08-05T04:00:00Z",
                "actual_return_datetime": "2026-08-04T04:00:00Z",
                "status": "returned",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "TRIP_INVALID_RETURN_DATETIME"

    async def test_missing_boat_id_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/trips",
            json={
                "trip_number": f"TRIP-{uuid.uuid4().hex[:8]}",
                "trip_type": "fishing",
                "departure_datetime": _DEPARTURE,
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "boat_id" in response.json()["error"]["field_errors"]

    async def test_missing_trip_type_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/trips",
            json={
                "boat_id": (await _create_boat(client, headers))["id"],
                "trip_number": f"TRIP-{uuid.uuid4().hex[:8]}",
                "departure_datetime": _DEPARTURE,
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "trip_type" in response.json()["error"]["field_errors"]

    async def test_blank_trip_number_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/trips",
            json={
                "boat_id": (await _create_boat(client, headers))["id"],
                "trip_number": "",
                "trip_type": "fishing",
                "departure_datetime": _DEPARTURE,
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "trip_number" in response.json()["error"]["field_errors"]


class TestGetTrip:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/trips/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(f"/api/v1/trips/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_returns_the_trip(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip(client, headers)
        response = await client.get(f"/api/v1/trips/{created['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(f"/api/v1/trips/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRIP_NOT_FOUND"

    async def test_soft_deleted_trip_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip(client, headers)
        await client.delete(f"/api/v1/trips/{created['id']}", headers=headers)
        response = await client.get(f"/api/v1/trips/{created['id']}", headers=headers)
        assert response.status_code == 404

    async def test_other_tenants_trip_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip(client, headers)

        other_tenant = Tenant(name="Other Trip Co", slug=f"other-trip-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_TRIP_PERMISSIONS)

        response = await client.get(f"/api/v1/trips/{created['id']}", headers=other_headers)
        assert response.status_code == 404


class TestListTrips:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/trips")
        assert response.status_code == 401

    async def test_default_response_shape(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_trip(client, headers)
        response = await client.get("/api/v1/trips", headers=headers)
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

    async def test_search_matches_trip_number_case_insensitively(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(name="Search Trip Tenant", slug=f"search-trip-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_TRIP_PERMISSIONS)

        marker = uuid.uuid4().hex[:8]
        await _create_trip(client, headers, trip_number=f"SPECIAL-{marker}")
        await _create_trip(client, headers, trip_number=f"IRRELEVANT-{marker}-X")

        response = await client.get(
            "/api/v1/trips", params={"q": f"special-{marker}"}, headers=headers
        )
        numbers = [t["trip_number"] for t in response.json()["data"]]
        assert numbers == [f"SPECIAL-{marker}"]

    async def test_search_matches_boat_name(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(name="Boat Search Tenant", slug=f"boat-search-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_TRIP_PERMISSIONS)

        marker = uuid.uuid4().hex[:8]
        matching_boat = await _create_boat(client, headers, name=f"Ocean Falcon {marker}")
        other_boat = await _create_boat(client, headers, name=f"Irrelevant Boat {marker}")
        target = await _create_trip(client, headers, boat_id=matching_boat["id"])
        await _create_trip(client, headers, boat_id=other_boat["id"])

        response = await client.get(
            "/api/v1/trips", params={"q": f"ocean falcon {marker}".upper()}, headers=headers
        )
        ids = [t["id"] for t in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_search_matches_captain_name(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Captain Trip Tenant", slug=f"captain-trip-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_TRIP_PERMISSIONS)

        marker = uuid.uuid4().hex[:8]
        await _create_trip(client, headers, captain_name=f"Suresh Patil {marker}")
        await _create_trip(client, headers, captain_name=f"Ramesh Yadav {marker}")

        response = await client.get(
            "/api/v1/trips", params={"q": f"Suresh Patil {marker}"}, headers=headers
        )
        captains = [t["captain_name"] for t in response.json()["data"]]
        assert captains == [f"Suresh Patil {marker}"]

    async def test_filters_by_boat_id(self, client: AsyncClient, db_session: AsyncSession) -> None:
        other_tenant = Tenant(name="Boat Filter Tenant", slug=f"boat-filter-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_TRIP_PERMISSIONS)

        boat_a = await _create_boat(client, headers)
        boat_b = await _create_boat(client, headers)
        target = await _create_trip(client, headers, boat_id=boat_a["id"])
        await _create_trip(client, headers, boat_id=boat_b["id"])

        response = await client.get(
            "/api/v1/trips", params={"boat_id": boat_a["id"]}, headers=headers
        )
        ids = [t["id"] for t in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_filters_by_status(self, client: AsyncClient, db_session: AsyncSession) -> None:
        other_tenant = Tenant(
            name="Status Filter Tenant", slug=f"status-filter-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_TRIP_PERMISSIONS)

        await _create_trip(client, headers)
        cancelled_boat = await _create_boat(client, headers)
        cancelled = await _create_trip(
            client, headers, boat_id=cancelled_boat["id"], status="cancelled"
        )

        response = await client.get(
            "/api/v1/trips", params={"status": "cancelled"}, headers=headers
        )
        ids = [t["id"] for t in response.json()["data"]]
        assert ids == [cancelled["id"]]

    async def test_filters_by_trip_type(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(name="Type Filter Tenant", slug=f"type-filter-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_TRIP_PERMISSIONS)

        await _create_trip(client, headers, trip_type="fishing")
        transport = await _create_trip(client, headers, trip_type="transport")

        response = await client.get(
            "/api/v1/trips", params={"trip_type": "transport"}, headers=headers
        )
        ids = [t["id"] for t in response.json()["data"]]
        assert ids == [transport["id"]]

    async def test_filters_by_departure_date_range(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Departure Filter Tenant", slug=f"dep-filter-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_TRIP_PERMISSIONS)

        in_range = await _create_trip(client, headers, departure_datetime="2026-08-15T04:00:00Z")
        await _create_trip(client, headers, departure_datetime="2026-09-15T04:00:00Z")

        response = await client.get(
            "/api/v1/trips",
            params={"departure_date_from": "2026-08-01", "departure_date_to": "2026-08-31"},
            headers=headers,
        )
        ids = [t["id"] for t in response.json()["data"]]
        assert ids == [in_range["id"]]

    async def test_sort_ascending_and_descending(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        marker = uuid.uuid4().hex[:8]
        await _create_trip(client, headers, trip_number=f"SORT-B-{marker}")
        await _create_trip(client, headers, trip_number=f"SORT-A-{marker}")

        asc = await client.get(
            "/api/v1/trips", params={"q": marker, "sort": "trip_number"}, headers=headers
        )
        assert [t["trip_number"] for t in asc.json()["data"]] == [
            f"SORT-A-{marker}",
            f"SORT-B-{marker}",
        ]

        desc = await client.get(
            "/api/v1/trips", params={"q": marker, "sort": "-trip_number"}, headers=headers
        )
        assert [t["trip_number"] for t in desc.json()["data"]] == [
            f"SORT-B-{marker}",
            f"SORT-A-{marker}",
        ]

    async def test_invalid_sort_field_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/trips", params={"sort": "not_a_field"}, headers=headers
        )
        assert response.status_code == 422

    async def test_default_sort_is_most_recent_first(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        marker = uuid.uuid4().hex[:8]
        first = await _create_trip(client, headers, trip_number=f"FIRST-{marker}")
        second = await _create_trip(client, headers, trip_number=f"SECOND-{marker}")

        response = await client.get("/api/v1/trips", params={"q": marker}, headers=headers)
        ids = [t["id"] for t in response.json()["data"]]
        assert ids == [second["id"], first["id"]]

    async def test_search_with_no_matches_returns_empty_page(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/trips", params={"q": f"no-such-trip-{uuid.uuid4().hex}"}, headers=headers
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
            await _create_trip(client, headers, trip_number=f"PG-{marker}-{i}")

        response = await client.get(
            "/api/v1/trips",
            params={"q": marker, "page": 1, "page_size": 2, "sort": "trip_number"},
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
            "/api/v1/trips",
            params={"q": marker, "page": 2, "page_size": 2, "sort": "trip_number"},
            headers=headers,
        )
        meta2 = page2.json()["meta"]
        assert meta2["has_next"] is False
        assert meta2["has_previous"] is True
        assert len(page2.json()["data"]) == 1

    async def test_invalid_page_size_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/trips", params={"page_size": 101}, headers=headers)
        assert response.status_code == 422

    async def test_deleted_trips_are_excluded(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Fresh List Trip Tenant", slug=f"fresh-trip-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        isolated_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_PERMISSIONS
        )

        created = await _create_trip(client, isolated_headers)
        await client.delete(f"/api/v1/trips/{created['id']}", headers=isolated_headers)

        response = await client.get("/api/v1/trips", headers=isolated_headers)
        assert response.json()["data"] == []
        assert response.json()["meta"]["total_records"] == 0

    async def test_tenant_isolation_returns_only_own_trips(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        await _create_trip(client, headers)

        other_tenant = Tenant(name="Isolated Trip Co", slug=f"isolated-trip-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_TRIP_PERMISSIONS)

        response = await client.get("/api/v1/trips", headers=other_headers)
        assert response.json()["data"] == []


class TestUpdateTrip:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.put(f"/api/v1/trips/{uuid.uuid4()}", json={"notes": "x"})
        assert response.status_code == 401

    async def test_requires_edit_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["trip:view"])
        response = await client.put(
            f"/api/v1/trips/{uuid.uuid4()}", json={"notes": "x"}, headers=headers
        )
        assert response.status_code == 403

    async def test_partial_update_only_changes_supplied_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip(
            client, headers, captain_name="Suresh", departure_port="Sassoon Dock"
        )

        response = await client.put(
            f"/api/v1/trips/{created['id']}",
            json={"captain_name": "Ramesh"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["captain_name"] == "Ramesh"
        assert body["departure_port"] == "Sassoon Dock"

    async def test_duplicate_trip_number_on_update_is_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_trip(client, headers, trip_number="EXISTING-NUM")
        target = await _create_trip(client, headers, trip_number="CHANGEABLE-NUM")

        response = await client.put(
            f"/api/v1/trips/{target['id']}",
            json={"trip_number": "EXISTING-NUM"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DUPLICATE_TRIP_NUMBER"

    async def test_renaming_to_its_own_current_number_is_not_a_conflict(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip(client, headers, trip_number="STABLE-NUM")

        response = await client.put(
            f"/api/v1/trips/{created['id']}",
            json={"trip_number": "STABLE-NUM", "notes": "touched"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["notes"] == "touched"

    async def test_reassigning_to_unknown_boat_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip(client, headers)

        response = await client.put(
            f"/api/v1/trips/{created['id']}",
            json={"boat_id": str(uuid.uuid4())},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRIP_BOAT_NOT_FOUND"

    async def test_reassigning_to_an_inactive_boat_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip(client, headers)
        inactive_boat = await _create_boat(client, headers, is_active=False)

        response = await client.put(
            f"/api/v1/trips/{created['id']}",
            json={"boat_id": inactive_boat["id"]},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "TRIP_BOAT_NOT_ACTIVE"

    async def test_reassigning_to_a_boat_with_an_active_trip_is_422(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        busy_boat = await _create_boat(client, headers)
        await _create_trip(client, headers, boat_id=busy_boat["id"])
        target = await _create_trip(client, headers)

        response = await client.put(
            f"/api/v1/trips/{target['id']}",
            json={"boat_id": busy_boat["id"]},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "TRIP_BOAT_ALREADY_ACTIVE"

    async def test_reassigning_boat_on_a_returned_trip_is_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip(client, headers)
        other_boat = await _create_boat(client, headers)

        returned = await client.put(
            f"/api/v1/trips/{created['id']}",
            json={"status": "returned", "actual_return_datetime": "2026-08-02T10:00:00Z"},
            headers=headers,
        )
        assert returned.status_code == 200

        response = await client.put(
            f"/api/v1/trips/{created['id']}",
            json={"boat_id": other_boat["id"]},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "TRIP_BOAT_CHANGE_NOT_ALLOWED"

    async def test_marking_returned_frees_the_boat_for_a_new_active_trip(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        boat = await _create_boat(client, headers)
        first = await _create_trip(client, headers, boat_id=boat["id"])

        await client.put(
            f"/api/v1/trips/{first['id']}",
            json={"status": "returned", "actual_return_datetime": "2026-08-02T10:00:00Z"},
            headers=headers,
        )

        response = await client.post(
            "/api/v1/trips",
            json={
                "boat_id": boat["id"],
                "trip_number": f"TRIP-{uuid.uuid4().hex[:8]}",
                "trip_type": "fishing",
                "departure_datetime": "2026-08-10T04:00:00Z",
            },
            headers=headers,
        )
        assert response.status_code == 201

    async def test_invalid_return_datetime_on_update_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip(client, headers, departure_datetime="2026-08-05T04:00:00Z")

        response = await client.put(
            f"/api/v1/trips/{created['id']}",
            json={"actual_return_datetime": "2026-08-01T04:00:00Z"},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "TRIP_INVALID_RETURN_DATETIME"

    async def test_update_bumps_updated_at_and_sets_updated_by(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip(client, headers)

        response = await client.put(
            f"/api/v1/trips/{created['id']}",
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
            await db_session.execute(select(Trip).where(Trip.id == uuid.UUID(created["id"])))
        ).scalar_one()
        assert row.updated_by == admin.id

    async def test_cannot_update_another_tenants_trip(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip(client, headers)

        other_tenant = Tenant(
            name="Other Trip Updater", slug=f"other-trip-upd-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_TRIP_PERMISSIONS)

        response = await client.put(
            f"/api/v1/trips/{created['id']}",
            json={"notes": "Hijacked"},
            headers=other_headers,
        )
        assert response.status_code == 404

        unchanged = await client.get(f"/api/v1/trips/{created['id']}", headers=headers)
        assert unchanged.json()["notes"] is None

    async def test_cannot_update_a_deleted_trip(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip(client, headers)
        await client.delete(f"/api/v1/trips/{created['id']}", headers=headers)

        response = await client.put(
            f"/api/v1/trips/{created['id']}",
            json={"notes": "Should Not Apply"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRIP_NOT_FOUND"

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            f"/api/v1/trips/{uuid.uuid4()}", json={"notes": "x"}, headers=headers
        )
        assert response.status_code == 404


class TestDeleteTrip:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.delete(f"/api/v1/trips/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_delete_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["trip:view", "trip:edit"])
        response = await client.delete(f"/api/v1/trips/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_success_soft_deletes_and_sets_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip(client, headers)

        response = await client.delete(f"/api/v1/trips/{created['id']}", headers=headers)
        assert response.status_code == 204
        assert response.content == b""

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(select(Trip).where(Trip.id == uuid.UUID(created["id"])))
        ).scalar_one()
        assert row.deleted_at is not None
        assert row.deleted_by == admin.id

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.delete(f"/api/v1/trips/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404

    async def test_deleting_twice_is_404_the_second_time(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip(client, headers)
        first = await client.delete(f"/api/v1/trips/{created['id']}", headers=headers)
        second = await client.delete(f"/api/v1/trips/{created['id']}", headers=headers)
        assert first.status_code == 204
        assert second.status_code == 404

    async def test_deleting_frees_the_boat_for_a_new_active_trip(self, client: AsyncClient) -> None:
        """A soft-deleted trip must not keep pinning its boat as busy."""
        headers = await _admin_headers(client)
        boat = await _create_boat(client, headers)
        created = await _create_trip(client, headers, boat_id=boat["id"])

        await client.delete(f"/api/v1/trips/{created['id']}", headers=headers)

        response = await client.post(
            "/api/v1/trips",
            json={
                "boat_id": boat["id"],
                "trip_number": f"TRIP-{uuid.uuid4().hex[:8]}",
                "trip_type": "fishing",
                "departure_datetime": "2026-08-10T04:00:00Z",
            },
            headers=headers,
        )
        assert response.status_code == 201

    async def test_cannot_delete_another_tenants_trip(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip(client, headers)

        other_tenant = Tenant(
            name="Other Trip Deleter", slug=f"other-trip-del-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_TRIP_PERMISSIONS)

        response = await client.delete(f"/api/v1/trips/{created['id']}", headers=other_headers)
        assert response.status_code == 404

        still_there = await client.get(f"/api/v1/trips/{created['id']}", headers=headers)
        assert still_there.status_code == 200
