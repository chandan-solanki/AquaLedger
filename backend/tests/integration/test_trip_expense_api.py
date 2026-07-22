import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.trip_expenses.models import TripExpense

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

# _create_trip_expense provisions a fresh trip (and that trip's boat and
# company) via the API by default, so test users need enough trip/boat/
# company access for that setup to succeed too.
_ALL_TRIP_EXPENSE_PERMISSIONS = [
    "trip_expense:view",
    "trip_expense:create",
    "trip_expense:edit",
    "trip_expense:delete",
    "trip:view",
    "trip:create",
    "trip:edit",
    "boat:view",
    "boat:create",
    "company:view",
    "company:create",
]
_DEPARTURE = "2026-06-01T04:00:00Z"
_RETURN = "2026-06-10T10:00:00Z"
_EXPENSE_DATE = "2026-06-05"


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
        "code": f"TECO-{uuid.uuid4().hex[:8]}",
        "name": f"Expense Owner {uuid.uuid4().hex[:8]}",
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
        "code": f"TEB-{uuid.uuid4().hex[:8]}",
        "name": f"Boat {uuid.uuid4().hex[:8]}",
        "registration_number": f"TEREG-{uuid.uuid4().hex[:8]}",
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
        "trip_number": f"TETRIP-{uuid.uuid4().hex[:8]}",
        "trip_type": "fishing",
        "departure_datetime": _DEPARTURE,
    }
    payload.update(overrides)
    response = await client.post("/api/v1/trips", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _update_trip(
    client: AsyncClient, headers: dict[str, str], trip_id: str, **fields: Any
) -> dict[str, Any]:
    response = await client.put(f"/api/v1/trips/{trip_id}", json=fields, headers=headers)
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_returned_trip(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    trip = await _create_trip(client, headers, **overrides)
    return await _update_trip(
        client, headers, trip["id"], status="returned", actual_return_datetime=_RETURN
    )


async def _create_cancelled_trip(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    trip = await _create_trip(client, headers, **overrides)
    return await _update_trip(client, headers, trip["id"], status="cancelled")


async def _create_trip_expense(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    trip_id: str | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    if trip_id is None:
        trip_id = (await _create_trip(client, headers))["id"]
    payload: dict[str, Any] = {
        "trip_id": trip_id,
        "expense_type": "diesel",
        "amount": "500.00",
        "expense_date": _EXPENSE_DATE,
    }
    payload.update(overrides)
    response = await client.post("/api/v1/trip-expenses", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


class TestCreateTripExpense:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/trip-expenses",
            json={
                "trip_id": str(uuid.uuid4()),
                "expense_type": "diesel",
                "amount": "100.00",
                "expense_date": _EXPENSE_DATE,
            },
        )
        assert response.status_code == 401

    async def test_requires_create_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["trip_expense:view"])
        response = await client.post(
            "/api/v1/trip-expenses",
            json={
                "trip_id": str(uuid.uuid4()),
                "expense_type": "diesel",
                "amount": "100.00",
                "expense_date": _EXPENSE_DATE,
            },
            headers=headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_success_sets_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        body = await _create_trip_expense(
            client, headers, vendor_name="Sassoon Dock Fuel Co", receipt_number="RCPT-1042"
        )

        assert body["vendor_name"] == "Sassoon Dock Fuel Co"
        assert body["receipt_number"] == "RCPT-1042"
        assert body["amount"] == "500.00"
        assert body["created_at"] == body["updated_at"]

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(
                select(TripExpense).where(TripExpense.id == uuid.UUID(body["id"]))
            )
        ).scalar_one()
        assert row.created_by == admin.id
        assert row.updated_by == admin.id
        assert row.tenant_id == admin.tenant_id

    async def test_unknown_trip_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/trip-expenses",
            json={
                "trip_id": str(uuid.uuid4()),
                "expense_type": "diesel",
                "amount": "100.00",
                "expense_date": _EXPENSE_DATE,
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRIP_EXPENSE_TRIP_NOT_FOUND"

    async def test_cancelled_trip_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        trip = await _create_cancelled_trip(client, headers)
        response = await client.post(
            "/api/v1/trip-expenses",
            json={
                "trip_id": trip["id"],
                "expense_type": "diesel",
                "amount": "100.00",
                "expense_date": _EXPENSE_DATE,
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "TRIP_EXPENSE_TRIP_CANCELLED"

    async def test_expense_date_before_departure_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        trip = await _create_trip(client, headers)  # departs 2026-06-01
        response = await client.post(
            "/api/v1/trip-expenses",
            json={
                "trip_id": trip["id"],
                "expense_type": "diesel",
                "amount": "100.00",
                "expense_date": "2026-05-30",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "TRIP_EXPENSE_DATE_BEFORE_DEPARTURE"

    async def test_expense_date_after_return_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        trip = await _create_returned_trip(client, headers)  # returns 2026-06-10
        response = await client.post(
            "/api/v1/trip-expenses",
            json={
                "trip_id": trip["id"],
                "expense_type": "diesel",
                "amount": "100.00",
                "expense_date": "2026-06-11",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "TRIP_EXPENSE_DATE_AFTER_RETURN"

    async def test_no_upper_bound_when_trip_has_not_returned(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        trip = await _create_trip(client, headers)  # still "planned", no return date
        response = await client.post(
            "/api/v1/trip-expenses",
            json={
                "trip_id": trip["id"],
                "expense_type": "diesel",
                "amount": "100.00",
                "expense_date": "2099-01-01",
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text

    async def test_zero_amount_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        trip = await _create_trip(client, headers)
        response = await client.post(
            "/api/v1/trip-expenses",
            json={
                "trip_id": trip["id"],
                "expense_type": "diesel",
                "amount": "0.00",
                "expense_date": _EXPENSE_DATE,
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "amount" in response.json()["error"]["field_errors"]

    async def test_negative_amount_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        trip = await _create_trip(client, headers)
        response = await client.post(
            "/api/v1/trip-expenses",
            json={
                "trip_id": trip["id"],
                "expense_type": "diesel",
                "amount": "-5.00",
                "expense_date": _EXPENSE_DATE,
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "amount" in response.json()["error"]["field_errors"]

    async def test_missing_trip_id_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/trip-expenses",
            json={"expense_type": "diesel", "amount": "100.00", "expense_date": _EXPENSE_DATE},
            headers=headers,
        )
        assert response.status_code == 422
        assert "trip_id" in response.json()["error"]["field_errors"]

    async def test_missing_expense_date_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        trip = await _create_trip(client, headers)
        response = await client.post(
            "/api/v1/trip-expenses",
            json={"trip_id": trip["id"], "expense_type": "diesel", "amount": "100.00"},
            headers=headers,
        )
        assert response.status_code == 422
        assert "expense_date" in response.json()["error"]["field_errors"]

    async def test_invalid_expense_type_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        trip = await _create_trip(client, headers)
        response = await client.post(
            "/api/v1/trip-expenses",
            json={
                "trip_id": trip["id"],
                "expense_type": "not-a-real-type",
                "amount": "100.00",
                "expense_date": _EXPENSE_DATE,
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "expense_type" in response.json()["error"]["field_errors"]

    async def test_cannot_use_another_tenants_trip(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)

        other_tenant = Tenant(
            name="Foreign Trip Owner", slug=f"foreign-trip-owner-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_EXPENSE_PERMISSIONS
        )
        foreign_trip = await _create_trip(client, other_headers)

        response = await client.post(
            "/api/v1/trip-expenses",
            json={
                "trip_id": foreign_trip["id"],
                "expense_type": "diesel",
                "amount": "100.00",
                "expense_date": _EXPENSE_DATE,
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRIP_EXPENSE_TRIP_NOT_FOUND"


class TestGetTripExpense:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/trip-expenses/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(f"/api/v1/trip-expenses/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_returns_the_trip_expense(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_expense(client, headers)
        response = await client.get(f"/api/v1/trip-expenses/{created['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(f"/api/v1/trip-expenses/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRIP_EXPENSE_NOT_FOUND"

    async def test_soft_deleted_trip_expense_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_expense(client, headers)
        await client.delete(f"/api/v1/trip-expenses/{created['id']}", headers=headers)
        response = await client.get(f"/api/v1/trip-expenses/{created['id']}", headers=headers)
        assert response.status_code == 404

    async def test_other_tenants_trip_expense_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_expense(client, headers)

        other_tenant = Tenant(
            name="Other Expense Co", slug=f"other-expense-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_EXPENSE_PERMISSIONS
        )

        response = await client.get(
            f"/api/v1/trip-expenses/{created['id']}", headers=other_headers
        )
        assert response.status_code == 404


class TestListTripExpenses:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/trip-expenses")
        assert response.status_code == 401

    async def test_default_response_shape(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_trip_expense(client, headers)
        response = await client.get("/api/v1/trip-expenses", headers=headers)
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

    async def test_search_matches_vendor_name(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Search Expense Vendor Tenant", slug=f"search-exp-vendor-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_EXPENSE_PERMISSIONS
        )

        marker = uuid.uuid4().hex[:8]
        target = await _create_trip_expense(
            client, headers, vendor_name=f"Special Fuel Co {marker}"
        )
        await _create_trip_expense(client, headers, vendor_name=f"Irrelevant {marker}")

        response = await client.get(
            "/api/v1/trip-expenses", params={"q": f"special fuel co {marker}"}, headers=headers
        )
        ids = [e["id"] for e in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_search_matches_receipt_number(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Search Expense Receipt Tenant", slug=f"search-exp-rcpt-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_EXPENSE_PERMISSIONS
        )

        marker = uuid.uuid4().hex[:8]
        target = await _create_trip_expense(
            client, headers, receipt_number=f"RCPT-{marker}"
        )
        await _create_trip_expense(client, headers, receipt_number=f"OTHER-{marker}-X")

        response = await client.get(
            "/api/v1/trip-expenses", params={"q": f"rcpt-{marker}".upper()}, headers=headers
        )
        ids = [e["id"] for e in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_filters_by_trip_id(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Trip Filter Expense Tenant", slug=f"trip-filter-exp-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_EXPENSE_PERMISSIONS
        )

        trip_a = await _create_trip(client, headers)
        trip_b = await _create_trip(client, headers)
        target = await _create_trip_expense(client, headers, trip_id=trip_a["id"])
        await _create_trip_expense(client, headers, trip_id=trip_b["id"])

        response = await client.get(
            "/api/v1/trip-expenses", params={"trip_id": trip_a["id"]}, headers=headers
        )
        ids = [e["id"] for e in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_filters_by_expense_type(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Type Filter Expense Tenant", slug=f"type-filter-exp-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_EXPENSE_PERMISSIONS
        )

        await _create_trip_expense(client, headers, expense_type="ice")
        harbour = await _create_trip_expense(client, headers, expense_type="harbour")

        response = await client.get(
            "/api/v1/trip-expenses", params={"expense_type": "harbour"}, headers=headers
        )
        ids = [e["id"] for e in response.json()["data"]]
        assert ids == [harbour["id"]]

    async def test_filters_by_expense_date_range(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Date Filter Expense Tenant", slug=f"date-filter-exp-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_EXPENSE_PERMISSIONS
        )

        in_range = await _create_trip_expense(client, headers, expense_date="2026-06-05")
        await _create_trip_expense(client, headers, expense_date="2099-01-01")

        response = await client.get(
            "/api/v1/trip-expenses",
            params={"expense_date_from": "2026-06-01", "expense_date_to": "2026-06-30"},
            headers=headers,
        )
        ids = [e["id"] for e in response.json()["data"]]
        assert ids == [in_range["id"]]

    async def test_sort_ascending_and_descending_by_expense_date(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Sort Date Expense Tenant", slug=f"sort-date-exp-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_EXPENSE_PERMISSIONS
        )

        trip = await _create_trip(client, headers)
        older = await _create_trip_expense(
            client, headers, trip_id=trip["id"], expense_date="2026-06-01"
        )
        newer = await _create_trip_expense(
            client, headers, trip_id=trip["id"], expense_date="2026-06-08"
        )

        asc = await client.get(
            "/api/v1/trip-expenses", params={"sort": "expense_date"}, headers=headers
        )
        assert [e["id"] for e in asc.json()["data"]] == [older["id"], newer["id"]]

        desc = await client.get(
            "/api/v1/trip-expenses", params={"sort": "-expense_date"}, headers=headers
        )
        assert [e["id"] for e in desc.json()["data"]] == [newer["id"], older["id"]]

    async def test_sort_by_amount(self, client: AsyncClient, db_session: AsyncSession) -> None:
        other_tenant = Tenant(
            name="Sort Amount Expense Tenant", slug=f"sort-amount-exp-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_EXPENSE_PERMISSIONS
        )

        small = await _create_trip_expense(client, headers, amount="10.00")
        large = await _create_trip_expense(client, headers, amount="90.00")

        response = await client.get(
            "/api/v1/trip-expenses", params={"sort": "amount"}, headers=headers
        )
        assert [e["id"] for e in response.json()["data"]] == [small["id"], large["id"]]

    async def test_invalid_sort_field_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/trip-expenses", params={"sort": "trip_id"}, headers=headers
        )
        assert response.status_code == 422

    async def test_default_sort_is_most_recent_first(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Default Sort Expense Tenant", slug=f"default-sort-exp-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_EXPENSE_PERMISSIONS
        )

        first = await _create_trip_expense(client, headers)
        second = await _create_trip_expense(client, headers)

        response = await client.get("/api/v1/trip-expenses", headers=headers)
        ids = [e["id"] for e in response.json()["data"]]
        assert ids == [second["id"], first["id"]]

    async def test_search_with_no_matches_returns_empty_page(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/trip-expenses",
            params={"q": f"no-such-expense-{uuid.uuid4().hex}"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert body["meta"]["total_records"] == 0
        assert body["meta"]["total_pages"] == 0

    async def test_pagination_meta_is_correct(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Pagination Expense Tenant", slug=f"pagination-exp-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_EXPENSE_PERMISSIONS
        )

        for _ in range(3):
            await _create_trip_expense(client, headers)

        response = await client.get(
            "/api/v1/trip-expenses",
            params={"page": 1, "page_size": 2, "sort": "-created_at"},
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
            "/api/v1/trip-expenses",
            params={"page": 2, "page_size": 2, "sort": "-created_at"},
            headers=headers,
        )
        meta2 = page2.json()["meta"]
        assert meta2["has_next"] is False
        assert meta2["has_previous"] is True
        assert len(page2.json()["data"]) == 1

    async def test_invalid_page_size_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/trip-expenses", params={"page_size": 101}, headers=headers
        )
        assert response.status_code == 422

    async def test_deleted_trip_expenses_are_excluded(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Fresh List Expense Tenant", slug=f"fresh-exp-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        isolated_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_EXPENSE_PERMISSIONS
        )

        created = await _create_trip_expense(client, isolated_headers)
        await client.delete(f"/api/v1/trip-expenses/{created['id']}", headers=isolated_headers)

        response = await client.get("/api/v1/trip-expenses", headers=isolated_headers)
        assert response.json()["data"] == []
        assert response.json()["meta"]["total_records"] == 0

    async def test_tenant_isolation_returns_only_own_trip_expenses(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        await _create_trip_expense(client, headers)

        other_tenant = Tenant(
            name="Isolated Expense Co", slug=f"isolated-expense-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_EXPENSE_PERMISSIONS
        )

        response = await client.get("/api/v1/trip-expenses", headers=other_headers)
        assert response.json()["data"] == []


class TestUpdateTripExpense:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.put(
            f"/api/v1/trip-expenses/{uuid.uuid4()}", json={"description": "x"}
        )
        assert response.status_code == 401

    async def test_requires_edit_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["trip_expense:view"])
        response = await client.put(
            f"/api/v1/trip-expenses/{uuid.uuid4()}",
            json={"description": "x"},
            headers=headers,
        )
        assert response.status_code == 403

    async def test_partial_update_only_changes_supplied_fields(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_expense(client, headers, vendor_name="Sassoon Dock Fuel Co")

        response = await client.put(
            f"/api/v1/trip-expenses/{created['id']}",
            json={"description": "Revised"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["description"] == "Revised"
        assert body["vendor_name"] == "Sassoon Dock Fuel Co"

    async def test_reassign_trip_to_unknown_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_expense(client, headers)

        response = await client.put(
            f"/api/v1/trip-expenses/{created['id']}",
            json={"trip_id": str(uuid.uuid4())},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRIP_EXPENSE_TRIP_NOT_FOUND"

    async def test_reassign_trip_to_cancelled_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_expense(client, headers)
        cancelled_trip = await _create_cancelled_trip(client, headers)

        response = await client.put(
            f"/api/v1/trip-expenses/{created['id']}",
            json={"trip_id": cancelled_trip["id"]},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "TRIP_EXPENSE_TRIP_CANCELLED"

    async def test_changing_expense_date_outside_trip_window_is_422(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        trip = await _create_returned_trip(client, headers)  # window: 06-01..06-10
        created = await _create_trip_expense(client, headers, trip_id=trip["id"])

        response = await client.put(
            f"/api/v1/trip-expenses/{created['id']}",
            json={"expense_date": "2026-06-11"},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "TRIP_EXPENSE_DATE_AFTER_RETURN"

    async def test_invalid_amount_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_expense(client, headers)

        response = await client.put(
            f"/api/v1/trip-expenses/{created['id']}",
            json={"amount": "-1"},
            headers=headers,
        )
        assert response.status_code == 422
        assert "amount" in response.json()["error"]["field_errors"]

    async def test_invalid_expense_type_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_expense(client, headers)

        response = await client.put(
            f"/api/v1/trip-expenses/{created['id']}",
            json={"expense_type": "not-a-real-type"},
            headers=headers,
        )
        assert response.status_code == 422
        assert "expense_type" in response.json()["error"]["field_errors"]

    async def test_update_bumps_updated_at_and_sets_updated_by(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_expense(client, headers)

        response = await client.put(
            f"/api/v1/trip-expenses/{created['id']}",
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
            await db_session.execute(
                select(TripExpense).where(TripExpense.id == uuid.UUID(created["id"]))
            )
        ).scalar_one()
        assert row.updated_by == admin.id

    async def test_cannot_update_another_tenants_trip_expense(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_expense(client, headers)

        other_tenant = Tenant(
            name="Other Expense Updater", slug=f"other-exp-upd-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_EXPENSE_PERMISSIONS
        )

        response = await client.put(
            f"/api/v1/trip-expenses/{created['id']}",
            json={"description": "Hijacked"},
            headers=other_headers,
        )
        assert response.status_code == 404

        unchanged = await client.get(f"/api/v1/trip-expenses/{created['id']}", headers=headers)
        assert unchanged.json()["description"] is None

    async def test_cannot_update_a_deleted_trip_expense(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_expense(client, headers)
        await client.delete(f"/api/v1/trip-expenses/{created['id']}", headers=headers)

        response = await client.put(
            f"/api/v1/trip-expenses/{created['id']}",
            json={"description": "Should Not Apply"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRIP_EXPENSE_NOT_FOUND"

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            f"/api/v1/trip-expenses/{uuid.uuid4()}",
            json={"description": "x"},
            headers=headers,
        )
        assert response.status_code == 404


class TestDeleteTripExpense:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.delete(f"/api/v1/trip-expenses/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_delete_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(
            db_session, tenant_id, ["trip_expense:view", "trip_expense:edit"]
        )
        response = await client.delete(f"/api/v1/trip-expenses/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_success_soft_deletes_and_sets_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_expense(client, headers)

        response = await client.delete(f"/api/v1/trip-expenses/{created['id']}", headers=headers)
        assert response.status_code == 204
        assert response.content == b""

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(
                select(TripExpense).where(TripExpense.id == uuid.UUID(created["id"]))
            )
        ).scalar_one()
        assert row.deleted_at is not None
        assert row.deleted_by == admin.id

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.delete(f"/api/v1/trip-expenses/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404

    async def test_deleting_twice_is_404_the_second_time(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_expense(client, headers)
        first = await client.delete(f"/api/v1/trip-expenses/{created['id']}", headers=headers)
        second = await client.delete(f"/api/v1/trip-expenses/{created['id']}", headers=headers)
        assert first.status_code == 204
        assert second.status_code == 404

    async def test_cannot_delete_another_tenants_trip_expense(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_trip_expense(client, headers)

        other_tenant = Tenant(
            name="Other Expense Deleter", slug=f"other-exp-del-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_TRIP_EXPENSE_PERMISSIONS
        )

        response = await client.delete(
            f"/api/v1/trip-expenses/{created['id']}", headers=other_headers
        )
        assert response.status_code == 404

        still_there = await client.get(f"/api/v1/trip-expenses/{created['id']}", headers=headers)
        assert still_there.status_code == 200
