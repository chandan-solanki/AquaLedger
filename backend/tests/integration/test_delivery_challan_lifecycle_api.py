"""Integration tests for the Delivery Challan lifecycle (Sprint 12 Session
14): draft -> dispatched -> delivered, with cancel reachable from draft or
dispatched. Mirrors test_purchase_order_lifecycle_api.py's helper style."""

import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

_ALL_DC_PERMISSIONS = [
    "delivery_challan:view",
    "delivery_challan:create",
    "delivery_challan:edit",
    "delivery_challan:delete",
    "delivery_challan:dispatch",
    "delivery_challan:deliver",
    "delivery_challan:cancel",
    "invoice:view",
    "invoice:create",
    "invoice:issue",
    "company:view",
    "company:create",
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
_CHALLAN_DATE = "2026-08-16"
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
        "code": f"LCCO-{uuid.uuid4().hex[:8]}",
        "name": f"Lifecycle Owner {uuid.uuid4().hex[:8]}",
        "company_type": "customer",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/companies", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_fish(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": f"LCFISH-{uuid.uuid4().hex[:8]}",
        "name": f"Lifecycle Fish {uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/fish", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_boat(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": f"LCB-{uuid.uuid4().hex[:8]}",
        "name": f"Lifecycle Boat {uuid.uuid4().hex[:8]}",
        "registration_number": f"LCREG-{uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/boats", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_returned_trip(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    boat = await _create_boat(client, headers)
    payload: dict[str, Any] = {
        "boat_id": boat["id"],
        "trip_number": f"LCTRIP-{uuid.uuid4().hex[:8]}",
        "trip_type": "fishing",
        "departure_datetime": _DEPARTURE,
    }
    payload.update(overrides)
    response = await client.post("/api/v1/trips", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    trip: dict[str, Any] = response.json()
    update_response = await client.put(
        f"/api/v1/trips/{trip['id']}",
        json={"status": "returned", "actual_return_datetime": _RETURN},
        headers=headers,
    )
    assert update_response.status_code == 200, update_response.text
    result: dict[str, Any] = update_response.json()
    return result


async def _create_trip_catch(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    trip = await _create_returned_trip(client, headers)
    fish = await _create_fish(client, headers)
    payload: dict[str, Any] = {
        "trip_id": trip["id"],
        "fish_id": fish["id"],
        "quantity_caught": "100.000",
        "landing_date": _LANDING_DATE,
    }
    payload.update(overrides)
    response = await client.post("/api/v1/trip-catches", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_invoice(
    client: AsyncClient, headers: dict[str, str], *, company_id: str | None = None, **overrides: Any
) -> dict[str, Any]:
    if company_id is None:
        company_id = (await _create_company(client, headers))["id"]
    payload: dict[str, Any] = {"company_id": company_id, "invoice_date": _INVOICE_DATE}
    payload.update(overrides)
    response = await client.post("/api/v1/invoices", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_invoice_item(
    client: AsyncClient, headers: dict[str, str], invoice_id: str, **overrides: Any
) -> dict[str, Any]:
    trip_catch = await _create_trip_catch(client, headers)
    payload: dict[str, Any] = {
        "trip_catch_id": trip_catch["id"],
        "fish_id": trip_catch["fish_id"],
        "quantity": "100.000",
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


async def _issued_invoice_with_item(
    client: AsyncClient, headers: dict[str, str], **item_overrides: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    invoice = await _create_invoice(client, headers)
    item = await _create_invoice_item(client, headers, invoice["id"], **item_overrides)
    issue_response = await client.post(f"/api/v1/invoices/{invoice['id']}/issue", headers=headers)
    assert issue_response.status_code == 200, issue_response.text
    issued: dict[str, Any] = issue_response.json()
    return issued, item


async def _create_delivery_challan(
    client: AsyncClient, headers: dict[str, str], *, invoice_id: str, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"invoice_id": invoice_id, "challan_date": _CHALLAN_DATE}
    payload.update(overrides)
    response = await client.post("/api/v1/delivery-challans", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _dispatchable_challan(
    client: AsyncClient, headers: dict[str, str], **item_overrides: Any
) -> dict[str, Any]:
    """A draft challan with one item - the minimum needed to dispatch."""
    invoice, item = await _issued_invoice_with_item(client, headers, quantity="100.000")
    challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
    add_response = await client.post(
        f"/api/v1/delivery-challans/{challan['id']}/items",
        json={"invoice_item_id": item["id"], "quantity": "40.000", **item_overrides},
        headers=headers,
    )
    assert add_response.status_code == 201, add_response.text
    return challan


class TestDispatchEndpoint:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(f"/api/v1/delivery-challans/{uuid.uuid4()}/dispatch")
        assert response.status_code == 401

    async def test_requires_dispatch_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(
            db_session, tenant_id, ["delivery_challan:view", "delivery_challan:create"]
        )
        response = await client.post(
            f"/api/v1/delivery-challans/{uuid.uuid4()}/dispatch", headers=headers
        )
        assert response.status_code == 403

    async def test_success_assigns_number_and_stamps_dispatched_at(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        challan = await _dispatchable_challan(client, headers)

        response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/dispatch", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "dispatched"
        assert body["challan_number"] is not None
        assert body["challan_number"].startswith("DC/")
        assert body["dispatched_at"] is not None

    async def test_rejects_dispatch_of_an_empty_challan(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_item(client, headers)
        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])

        response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/dispatch", headers=headers
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_EMPTY"

    async def test_rejects_dispatching_an_already_dispatched_challan(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        challan = await _dispatchable_challan(client, headers)
        await client.post(f"/api/v1/delivery-challans/{challan['id']}/dispatch", headers=headers)

        response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/dispatch", headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_INVALID_TRANSITION"

    async def test_immutable_after_dispatch(self, client: AsyncClient) -> None:
        """Once dispatched, edit/delete/item-CRUD are all rejected the same
        way DRAFT-only mutation is enforced everywhere else."""
        headers = await _admin_headers(client)
        challan = await _dispatchable_challan(client, headers)
        await client.post(f"/api/v1/delivery-challans/{challan['id']}/dispatch", headers=headers)

        edit_response = await client.put(
            f"/api/v1/delivery-challans/{challan['id']}", json={"remarks": "x"}, headers=headers
        )
        assert edit_response.status_code == 409
        assert edit_response.json()["error"]["code"] == "DELIVERY_CHALLAN_NOT_DRAFT"

        delete_response = await client.delete(
            f"/api/v1/delivery-challans/{challan['id']}", headers=headers
        )
        assert delete_response.status_code == 409

    async def test_tenant_isolation(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _admin_headers(client)
        challan = await _dispatchable_challan(client, headers)

        other_tenant = Tenant(
            name="Other Dispatch Tenant", slug=f"other-dispatch-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_DC_PERMISSIONS)

        response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/dispatch", headers=other_headers
        )
        assert response.status_code == 404


class TestDeliverEndpoint:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(f"/api/v1/delivery-challans/{uuid.uuid4()}/deliver")
        assert response.status_code == 401

    async def test_requires_deliver_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["delivery_challan:view"])
        response = await client.post(
            f"/api/v1/delivery-challans/{uuid.uuid4()}/deliver", headers=headers
        )
        assert response.status_code == 403

    async def test_success_stamps_delivered_at(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        challan = await _dispatchable_challan(client, headers)
        await client.post(f"/api/v1/delivery-challans/{challan['id']}/dispatch", headers=headers)

        response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/deliver", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "delivered"
        assert body["delivered_at"] is not None

    async def test_rejects_delivering_a_still_draft_challan(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        challan = await _dispatchable_challan(client, headers)

        response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/deliver", headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_INVALID_TRANSITION"

    async def test_rejects_delivering_an_already_delivered_challan(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        challan = await _dispatchable_challan(client, headers)
        await client.post(f"/api/v1/delivery-challans/{challan['id']}/dispatch", headers=headers)
        await client.post(f"/api/v1/delivery-challans/{challan['id']}/deliver", headers=headers)

        response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/deliver", headers=headers
        )
        assert response.status_code == 409

    async def test_tenant_isolation(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _admin_headers(client)
        challan = await _dispatchable_challan(client, headers)
        await client.post(f"/api/v1/delivery-challans/{challan['id']}/dispatch", headers=headers)

        other_tenant = Tenant(
            name="Other Deliver Tenant", slug=f"other-deliver-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_DC_PERMISSIONS)

        response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/deliver", headers=other_headers
        )
        assert response.status_code == 404


class TestCancelEndpoint:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(f"/api/v1/delivery-challans/{uuid.uuid4()}/cancel")
        assert response.status_code == 401

    async def test_requires_cancel_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["delivery_challan:view"])
        response = await client.post(
            f"/api/v1/delivery-challans/{uuid.uuid4()}/cancel", headers=headers
        )
        assert response.status_code == 403

    async def test_can_cancel_from_draft(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_item(client, headers)
        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])

        response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/cancel", headers=headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    async def test_can_cancel_from_dispatched(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        challan = await _dispatchable_challan(client, headers)
        await client.post(f"/api/v1/delivery-challans/{challan['id']}/dispatch", headers=headers)

        response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/cancel", headers=headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    async def test_rejects_cancelling_an_already_delivered_challan(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        challan = await _dispatchable_challan(client, headers)
        await client.post(f"/api/v1/delivery-challans/{challan['id']}/dispatch", headers=headers)
        await client.post(f"/api/v1/delivery-challans/{challan['id']}/deliver", headers=headers)

        response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/cancel", headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_INVALID_TRANSITION"

    async def test_rejects_cancelling_an_already_cancelled_challan(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_item(client, headers)
        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        await client.post(f"/api/v1/delivery-challans/{challan['id']}/cancel", headers=headers)

        response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/cancel", headers=headers
        )
        assert response.status_code == 409

    async def test_tenant_isolation(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_item(client, headers)
        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])

        other_tenant = Tenant(
            name="Other Cancel Tenant", slug=f"other-cancel-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_DC_PERMISSIONS)

        response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/cancel", headers=other_headers
        )
        assert response.status_code == 404
