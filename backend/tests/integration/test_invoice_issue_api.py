import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

# _create_invoice_item provisions a fresh trip catch (and that trip catch's
# fish, trip, boat and company) via the API by default, so a user needs the
# full chain's access for that setup to succeed, plus invoice:issue itself.
_ALL_ISSUE_PERMISSIONS = [
    "invoice:view",
    "invoice:create",
    "invoice:edit",
    "invoice:delete",
    "invoice:issue",
    "company:view",
    "company:create",
    "company:edit",
    "fish:view",
    "fish:manage",
    "boat:view",
    "boat:create",
    "trip:view",
    "trip:create",
    "trip:edit",
    "trip_catch:view",
    "trip_catch:create",
]
_INVOICE_DATE = "2026-07-22"
_DEPARTURE = "2026-06-01T04:00:00Z"
_RETURN = "2026-06-10T10:00:00Z"
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
        "code": f"ISSCO-{uuid.uuid4().hex[:8]}",
        "name": f"Issue Owner {uuid.uuid4().hex[:8]}",
        "company_type": "customer",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/companies", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _update_company(
    client: AsyncClient, headers: dict[str, str], company_id: str, **fields: Any
) -> dict[str, Any]:
    response = await client.put(f"/api/v1/companies/{company_id}", json=fields, headers=headers)
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_invoice(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    company_id: str | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    if company_id is None:
        company_id = (await _create_company(client, headers))["id"]
    payload: dict[str, Any] = {
        "company_id": company_id,
        "invoice_date": _INVOICE_DATE,
    }
    payload.update(overrides)
    response = await client.post("/api/v1/invoices", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_fish(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": f"ISSFISH-{uuid.uuid4().hex[:8]}",
        "name": f"Issue Fish {uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/fish", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_boat(
    client: AsyncClient, headers: dict[str, str], *, company_id: str | None = None, **overrides: Any
) -> dict[str, Any]:
    if company_id is None:
        company_id = (await _create_company(client, headers))["id"]
    payload: dict[str, Any] = {
        "company_id": company_id,
        "code": f"ISSB-{uuid.uuid4().hex[:8]}",
        "name": f"Issue Boat {uuid.uuid4().hex[:8]}",
        "registration_number": f"ISSREG-{uuid.uuid4().hex[:8]}",
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
        "trip_number": f"ISSTRIP-{uuid.uuid4().hex[:8]}",
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


async def _create_invoice_item(
    client: AsyncClient,
    headers: dict[str, str],
    invoice_id: str,
    *,
    trip_catch: dict[str, Any] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    if trip_catch is None:
        trip_catch = await _create_trip_catch(client, headers)
    payload: dict[str, Any] = {
        "trip_catch_id": trip_catch["id"],
        "fish_id": trip_catch["fish_id"],
        "quantity": "10.000",
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
    return await client.post(f"/api/v1/invoices/{invoice_id}/issue", headers=headers)


async def _draft_invoice_with_item(
    client: AsyncClient, headers: dict[str, str], **item_overrides: Any
) -> dict[str, Any]:
    invoice = await _create_invoice(client, headers)
    await _create_invoice_item(client, headers, invoice["id"], **item_overrides)
    return invoice


class TestIssueEndpointAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(f"/api/v1/invoices/{uuid.uuid4()}/issue")
        assert response.status_code == 401

    async def test_requires_issue_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """A user with every other invoice permission (view/create/edit/
        delete) but not invoice:issue must still be rejected - issue is its
        own route-level permission, distinct from invoice:edit, since issued
        invoices can never be reached through the edit path."""
        tenant_id = await _admin_tenant_id(client)
        admin_headers = await _admin_headers(client)
        invoice = await _draft_invoice_with_item(client, admin_headers)

        permissions_without_issue = [p for p in _ALL_ISSUE_PERMISSIONS if p != "invoice:issue"]
        limited_headers = await _make_user_headers(db_session, tenant_id, permissions_without_issue)

        response = await _issue_invoice(client, limited_headers, invoice["id"])
        assert response.status_code == 403


class TestSuccessfulIssue:
    async def test_issues_a_draft_invoice(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _draft_invoice_with_item(
            client, headers, quantity="20.000", rate="500.0000", tax_rate="5.00"
        )

        response = await _issue_invoice(client, headers, invoice["id"])

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "issued"
        assert body["invoice_number"] is not None
        assert body["invoice_number"].startswith("INV/")
        assert body["issued_at"] is not None
        assert body["total_amount"] == "10500.00"
        assert body["balance_amount"] == "10500.00"

    async def test_issued_invoice_is_visible_via_get(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _draft_invoice_with_item(client, headers)
        await _issue_invoice(client, headers, invoice["id"])

        response = await client.get(f"/api/v1/invoices/{invoice['id']}", headers=headers)

        assert response.status_code == 200
        assert response.json()["status"] == "issued"

    async def test_returns_404_for_an_unknown_invoice(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await _issue_invoice(client, headers, str(uuid.uuid4()))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVOICE_NOT_FOUND"

    async def test_returns_404_for_a_soft_deleted_draft_invoice(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        delete_response = await client.delete(f"/api/v1/invoices/{invoice['id']}", headers=headers)
        assert delete_response.status_code == 204

        response = await _issue_invoice(client, headers, invoice["id"])
        assert response.status_code == 404


class TestTenantIsolation:
    async def test_returns_404_for_an_invoice_belonging_to_another_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Other Issue Tenant", slug=f"other-issue-tenant-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_ISSUE_PERMISSIONS
        )
        other_invoice = await _draft_invoice_with_item(client, other_headers)

        admin_headers = await _admin_headers(client)
        response = await _issue_invoice(client, admin_headers, other_invoice["id"])
        assert response.status_code == 404


class TestBusinessRuleFailures:
    async def test_issuing_twice_returns_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _draft_invoice_with_item(client, headers)
        first = await _issue_invoice(client, headers, invoice["id"])
        assert first.status_code == 200

        second = await _issue_invoice(client, headers, invoice["id"])
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "INVOICE_NOT_DRAFT"

    async def test_empty_invoice_returns_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)

        response = await _issue_invoice(client, headers, invoice["id"])
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVOICE_EMPTY"

    async def test_inactive_company_returns_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        invoice = await _create_invoice(client, headers, company_id=company["id"])
        await _create_invoice_item(client, headers, invoice["id"])
        await _update_company(client, headers, company["id"], status="inactive")

        response = await _issue_invoice(client, headers, invoice["id"])
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVOICE_COMPANY_INACTIVE"

    async def test_insufficient_inventory_at_issue_time_returns_422(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        trip_catch = await _create_trip_catch(client, headers, quantity_caught="60.000")

        invoice_a = await _create_invoice(client, headers)
        await _create_invoice_item(
            client, headers, invoice_a["id"], trip_catch=trip_catch, quantity="60.000"
        )
        invoice_b = await _create_invoice(client, headers)
        await _create_invoice_item(
            client, headers, invoice_b["id"], trip_catch=trip_catch, quantity="60.000"
        )

        first = await _issue_invoice(client, headers, invoice_a["id"])
        assert first.status_code == 200

        second = await _issue_invoice(client, headers, invoice_b["id"])
        assert second.status_code == 422
        assert second.json()["error"]["code"] == "INVOICE_INSUFFICIENT_INVENTORY"


class TestImmutabilityAfterIssue:
    async def test_issued_invoice_cannot_be_updated(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _draft_invoice_with_item(client, headers)
        await _issue_invoice(client, headers, invoice["id"])

        response = await client.put(
            f"/api/v1/invoices/{invoice['id']}",
            json={"remarks": "Trying to edit an issued invoice"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVOICE_NOT_DRAFT"

    async def test_issued_invoice_cannot_be_deleted(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _draft_invoice_with_item(client, headers)
        await _issue_invoice(client, headers, invoice["id"])

        response = await client.delete(f"/api/v1/invoices/{invoice['id']}", headers=headers)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVOICE_NOT_DRAFT"

    async def test_cannot_add_an_item_to_an_issued_invoice(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        trip_catch = await _create_trip_catch(client, headers)
        invoice = await _draft_invoice_with_item(client, headers, trip_catch=trip_catch)
        await _issue_invoice(client, headers, invoice["id"])

        response = await client.post(
            f"/api/v1/invoices/{invoice['id']}/items",
            json={
                "trip_catch_id": trip_catch["id"],
                "fish_id": trip_catch["fish_id"],
                "quantity": "1.000",
                "unit": "kg",
                "rate": "1.0000",
            },
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVOICE_NOT_DRAFT"

    async def test_cannot_update_an_item_on_an_issued_invoice(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item = await _create_invoice_item(client, headers, invoice["id"])
        await _issue_invoice(client, headers, invoice["id"])

        response = await client.put(
            f"/api/v1/invoices/{invoice['id']}/items/{item['id']}",
            json={"quantity": "1.000"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVOICE_NOT_DRAFT"

    async def test_cannot_delete_an_item_on_an_issued_invoice(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item = await _create_invoice_item(client, headers, invoice["id"])
        await _issue_invoice(client, headers, invoice["id"])

        response = await client.delete(
            f"/api/v1/invoices/{invoice['id']}/items/{item['id']}", headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVOICE_NOT_DRAFT"
