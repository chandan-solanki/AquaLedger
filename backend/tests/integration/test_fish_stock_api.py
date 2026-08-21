import uuid
from decimal import Decimal
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

# _create_trip_catch/_issue_invoice provision a fresh RETURNED trip (and its
# boat), fish, and company via the API by default, so test users need the
# full chain's access, plus fish:view for the /fish-stock endpoints
# themselves (Session 2's documented permission decision).
_ALL_FISH_STOCK_PERMISSIONS = [
    "fish:view",
    "fish:manage",
    "trip_catch:view",
    "trip_catch:create",
    "trip:view",
    "trip:create",
    "trip:edit",
    "boat:view",
    "boat:create",
    "company:view",
    "company:create",
    "invoice:view",
    "invoice:create",
    "invoice:issue",
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


async def _create_boat(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": f"FSB-{uuid.uuid4().hex[:8]}",
        "name": f"Boat {uuid.uuid4().hex[:8]}",
        "registration_number": f"FSREG-{uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/boats", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_trip(
    client: AsyncClient, headers: dict[str, str], *, boat_id: str | None = None, **overrides: Any
) -> dict[str, Any]:
    if boat_id is None:
        boat_id = (await _create_boat(client, headers))["id"]
    payload: dict[str, Any] = {
        "boat_id": boat_id,
        "trip_number": f"FSTRIP-{uuid.uuid4().hex[:8]}",
        "trip_type": "fishing",
        "departure_datetime": _DEPARTURE,
    }
    payload.update(overrides)
    response = await client.post("/api/v1/trips", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_returned_trip(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    trip = await _create_trip(client, headers, **overrides)
    response = await client.put(
        f"/api/v1/trips/{trip['id']}",
        json={"status": "returned", "actual_return_datetime": _RETURN},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_fish(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": f"FSFISH-{uuid.uuid4().hex[:8]}",
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
        "quantity_caught": "100.000",
        "landing_date": _LANDING_DATE,
    }
    payload.update(overrides)
    response = await client.post("/api/v1/trip-catches", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_company(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": f"FSCO-{uuid.uuid4().hex[:8]}",
        "name": f"Fish Stock Buyer {uuid.uuid4().hex[:8]}",
        "company_type": "customer",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/companies", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_invoice(
    client: AsyncClient, headers: dict[str, str], *, company_id: str | None = None
) -> dict[str, Any]:
    if company_id is None:
        company_id = (await _create_company(client, headers))["id"]
    payload = {"company_id": company_id, "invoice_date": "2026-07-22"}
    response = await client.post("/api/v1/invoices", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _add_invoice_item(
    client: AsyncClient,
    headers: dict[str, str],
    invoice_id: str,
    *,
    trip_catch_id: str,
    fish_id: str,
    quantity: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "trip_catch_id": trip_catch_id,
        "fish_id": fish_id,
        "quantity": quantity,
        "unit": "kg",
        "rate": "100.0000",
    }
    payload.update(overrides)
    response = await client.post(
        f"/api/v1/invoices/{invoice_id}/items", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _issue_invoice(client: AsyncClient, headers: dict[str, str], invoice_id: str) -> Any:
    response = await client.post(f"/api/v1/invoices/{invoice_id}/issue", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


class TestListFishStockAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/fish-stock")
        assert response.status_code == 401

    async def test_requires_fish_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get("/api/v1/fish-stock", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"


class TestDetailFishStockAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/fish-stock/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_fish_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(f"/api/v1/fish-stock/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403


class TestListFishStock:
    async def test_default_response_shape(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_trip_catch(client, headers)

        response = await client.get("/api/v1/fish-stock", headers=headers)

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

    async def test_fish_never_caught_does_not_appear(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        fish = await _create_fish(client, headers)

        response = await client.get("/api/v1/fish-stock", headers=headers)

        ids = [row["fish_id"] for row in response.json()["data"]]
        assert fish["id"] not in ids

    async def test_row_reports_caught_sold_available_waste(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        catch = await _create_trip_catch(client, headers, quantity_caught="100.000")

        response = await client.get("/api/v1/fish-stock", params={"q": ""}, headers=headers)
        rows = {row["fish_id"]: row for row in response.json()["data"]}
        row = rows[catch["fish_id"]]

        assert row["total_caught"] == "100.000"
        assert row["total_sold"] == "0.000"
        assert row["total_available"] == "100.000"
        assert row["total_waste"] == "0.000"
        assert row["unit"] == "kg"

    async def test_multiple_trip_catches_for_same_fish_aggregate(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        fish = await _create_fish(client, headers)
        await _create_trip_catch(client, headers, fish_id=fish["id"], quantity_caught="60.000")
        await _create_trip_catch(client, headers, fish_id=fish["id"], quantity_caught="40.000")

        response = await client.get("/api/v1/fish-stock", headers=headers)
        rows = {row["fish_id"]: row for row in response.json()["data"]}

        assert rows[fish["id"]]["total_caught"] == "100.000"
        assert rows[fish["id"]]["total_available"] == "100.000"

    async def test_q_filters_by_fish_name(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        marker = uuid.uuid4().hex[:8]
        matching = await _create_fish(client, headers, name=f"Pomfret {marker}")
        other = await _create_fish(client, headers, name=f"Tuna {marker}")
        await _create_trip_catch(client, headers, fish_id=matching["id"])
        await _create_trip_catch(client, headers, fish_id=other["id"])

        response = await client.get(
            "/api/v1/fish-stock", params={"q": f"pomfret {marker}"}, headers=headers
        )
        ids = [row["fish_id"] for row in response.json()["data"]]
        assert ids == [matching["id"]]

    async def test_is_active_filters_out_inactive_fish(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        active = await _create_fish(client, headers)
        inactive = await _create_fish(client, headers, is_active=False)
        await _create_trip_catch(client, headers, fish_id=active["id"])
        await _create_trip_catch(client, headers, fish_id=inactive["id"])

        response = await client.get(
            "/api/v1/fish-stock", params={"is_active": True}, headers=headers
        )
        ids = [row["fish_id"] for row in response.json()["data"]]
        assert active["id"] in ids
        assert inactive["id"] not in ids

    async def test_soft_deleted_trip_catch_excluded_from_totals(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        fish = await _create_fish(client, headers)
        kept = await _create_trip_catch(
            client, headers, fish_id=fish["id"], quantity_caught="30.000"
        )
        deleted = await _create_trip_catch(
            client, headers, fish_id=fish["id"], quantity_caught="70.000"
        )
        delete_response = await client.delete(
            f"/api/v1/trip-catches/{deleted['id']}", headers=headers
        )
        assert delete_response.status_code == 204

        response = await client.get("/api/v1/fish-stock", headers=headers)
        rows = {row["fish_id"]: row for row in response.json()["data"]}

        assert rows[fish["id"]]["total_caught"] == "30.000"
        assert kept["fish_id"] == fish["id"]

    async def test_invalid_page_size_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/fish-stock", params={"page_size": 101}, headers=headers
        )
        assert response.status_code == 422

    async def test_tenant_isolation_never_shows_other_tenants_stock(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        await _create_trip_catch(client, headers)

        other_tenant = Tenant(
            name="Other Fish Stock Tenant", slug=f"other-fish-stock-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_FISH_STOCK_PERMISSIONS
        )

        response = await client.get("/api/v1/fish-stock", headers=other_headers)
        assert response.json()["data"] == []


class TestGetFishStockDetail:
    async def test_returns_totals_and_contributing_catches(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        fish = await _create_fish(client, headers)
        catch_a = await _create_trip_catch(
            client, headers, fish_id=fish["id"], quantity_caught="60.000"
        )
        catch_b = await _create_trip_catch(
            client, headers, fish_id=fish["id"], quantity_caught="40.000"
        )

        response = await client.get(f"/api/v1/fish-stock/{fish['id']}", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["fish_id"] == fish["id"]
        assert body["total_caught"] == "100.000"
        assert body["total_available"] == "100.000"
        catch_ids = {c["trip_catch_id"] for c in body["catches"]}
        assert catch_ids == {catch_a["id"], catch_b["id"]}
        for contributing in body["catches"]:
            assert contributing["trip_number"]

    async def test_unknown_fish_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(f"/api/v1/fish-stock/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "FISH_STOCK_FISH_NOT_FOUND"

    async def test_cross_tenant_fish_is_404_not_403(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        fish = await _create_fish(client, headers)

        other_tenant = Tenant(
            name="Other Fish Stock Detail Tenant",
            slug=f"other-fish-stock-detail-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_FISH_STOCK_PERMISSIONS
        )

        response = await client.get(f"/api/v1/fish-stock/{fish['id']}", headers=other_headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "FISH_STOCK_FISH_NOT_FOUND"

    async def test_soft_deleted_fish_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        fish = await _create_fish(client, headers)
        delete_response = await client.delete(f"/api/v1/fish/{fish['id']}", headers=headers)
        assert delete_response.status_code == 204

        response = await client.get(f"/api/v1/fish-stock/{fish['id']}", headers=headers)
        assert response.status_code == 404

    async def test_fish_with_no_catches_returns_zero_totals(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        fish = await _create_fish(client, headers)

        response = await client.get(f"/api/v1/fish-stock/{fish['id']}", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["total_caught"] == "0"
        assert body["catches"] == []

    async def test_soft_deleted_catch_excluded_from_detail(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        fish = await _create_fish(client, headers)
        kept = await _create_trip_catch(client, headers, fish_id=fish["id"])
        deleted = await _create_trip_catch(client, headers, fish_id=fish["id"])
        await client.delete(f"/api/v1/trip-catches/{deleted['id']}", headers=headers)

        response = await client.get(f"/api/v1/fish-stock/{fish['id']}", headers=headers)
        catch_ids = {c["trip_catch_id"] for c in response.json()["catches"]}
        assert catch_ids == {kept["id"]}


class TestFishStockInvariant:
    async def test_available_plus_sold_plus_waste_equals_caught_in_list(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        await _create_trip_catch(client, headers, quantity_caught="123.456")

        response = await client.get("/api/v1/fish-stock", headers=headers)
        for row in response.json()["data"]:
            total = (
                Decimal(row["total_available"])
                + Decimal(row["total_sold"])
                + Decimal(row["total_waste"])
            )
            assert total == Decimal(row["total_caught"])

    async def test_available_plus_sold_plus_waste_equals_caught_in_detail(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        catch = await _create_trip_catch(client, headers, quantity_caught="77.250")

        response = await client.get(f"/api/v1/fish-stock/{catch['fish_id']}", headers=headers)
        body = response.json()
        total = (
            Decimal(body["total_available"])
            + Decimal(body["total_sold"])
            + Decimal(body["total_waste"])
        )
        assert total == Decimal(body["total_caught"])


class TestFishStockReflectsInvoiceIssue:
    """The real scenario (Sprint 15 Session 2 spec): a trip catch's stock
    must move from available to sold through the *existing* invoice issue
    mechanism - deduct_available_quantity() - never anything this session
    adds. Fish Stock only reads the result."""

    async def test_issuing_an_invoice_moves_quantity_from_available_to_sold(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        fish = await _create_fish(client, headers, name=f"Pomfret {uuid.uuid4().hex[:8]}")
        catch = await _create_trip_catch(
            client, headers, fish_id=fish["id"], quantity_caught="100.000"
        )
        assert catch["available_quantity"] == "100.000"
        assert catch["sold_quantity"] == "0.000"

        before = await client.get(f"/api/v1/fish-stock/{fish['id']}", headers=headers)
        assert before.json()["total_caught"] == "100.000"
        assert before.json()["total_sold"] == "0.000"
        assert before.json()["total_available"] == "100.000"

        invoice = await _create_invoice(client, headers)
        await _add_invoice_item(
            client,
            headers,
            invoice["id"],
            trip_catch_id=catch["id"],
            fish_id=fish["id"],
            quantity="30.000",
        )
        await _issue_invoice(client, headers, invoice["id"])

        list_response = await client.get("/api/v1/fish-stock", headers=headers)
        rows = {row["fish_id"]: row for row in list_response.json()["data"]}
        row = rows[fish["id"]]
        assert row["total_caught"] == "100.000"
        assert row["total_sold"] == "30.000"
        assert row["total_available"] == "70.000"
        assert row["total_waste"] == "0.000"

        detail_response = await client.get(f"/api/v1/fish-stock/{fish['id']}", headers=headers)
        detail = detail_response.json()
        assert detail["total_caught"] == "100.000"
        assert detail["total_sold"] == "30.000"
        assert detail["total_available"] == "70.000"
        assert detail["total_waste"] == "0.000"
        assert len(detail["catches"]) == 1
        assert detail["catches"][0]["sold_quantity"] == "30.000"
        assert detail["catches"][0]["available_quantity"] == "70.000"

        # This endpoint is read-only - nothing about it should touch the
        # invoice's own financial fields.
        invoice_after = await client.get(f"/api/v1/invoices/{invoice['id']}", headers=headers)
        assert invoice_after.json()["status"] == "issued"
        assert invoice_after.json()["total_amount"] == "3000.00"
