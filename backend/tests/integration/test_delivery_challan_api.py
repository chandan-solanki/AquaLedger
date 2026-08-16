import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.delivery_challans.constants import DeliveryChallanStatus
from app.modules.delivery_challans.models import DeliveryChallan

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

# _create_delivery_challan provisions a fresh company/fish/boat/trip/
# trip_catch/invoice via the API by default, so test users need that whole
# chain's access too, plus delivery_challan:* itself.
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
    "invoice:edit",
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
        "code": f"DCCO-{uuid.uuid4().hex[:8]}",
        "name": f"DC Owner {uuid.uuid4().hex[:8]}",
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
        "code": f"DCFISH-{uuid.uuid4().hex[:8]}",
        "name": f"DC Fish {uuid.uuid4().hex[:8]}",
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
        "code": f"DCB-{uuid.uuid4().hex[:8]}",
        "name": f"DC Boat {uuid.uuid4().hex[:8]}",
        "registration_number": f"DCREG-{uuid.uuid4().hex[:8]}",
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
        "trip_number": f"DCTRIP-{uuid.uuid4().hex[:8]}",
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


async def _add_challan_item(
    client: AsyncClient, headers: dict[str, str], delivery_challan_id: str, **overrides: Any
) -> Any:
    payload: dict[str, Any] = dict(overrides)
    return await client.post(
        f"/api/v1/delivery-challans/{delivery_challan_id}/items", json=payload, headers=headers
    )


async def _set_challan_status(
    db_session: AsyncSession, delivery_challan_id: str, status: DeliveryChallanStatus
) -> None:
    row = (
        await db_session.execute(
            select(DeliveryChallan).where(DeliveryChallan.id == uuid.UUID(delivery_challan_id))
        )
    ).scalar_one()
    row.status = status
    await db_session.commit()


class TestCreateDeliveryChallan:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/delivery-challans",
            json={"invoice_id": str(uuid.uuid4()), "challan_date": _CHALLAN_DATE},
        )
        assert response.status_code == 401

    async def test_requires_create_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["delivery_challan:view"])
        response = await client.post(
            "/api/v1/delivery-challans",
            json={"invoice_id": str(uuid.uuid4()), "challan_date": _CHALLAN_DATE},
            headers=headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_success_is_draft_with_server_owned_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_item(client, headers)
        body = await _create_delivery_challan(
            client, headers, invoice_id=invoice["id"], remarks="First delivery"
        )

        assert body["status"] == "draft"
        assert body["challan_number"] is None
        assert body["dispatched_at"] is None
        assert body["delivered_at"] is None
        assert body["remarks"] == "First delivery"
        assert body["invoice_id"] == invoice["id"]
        assert "company_id" not in body
        assert "total_amount" not in body

    async def test_unknown_invoice_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/delivery-challans",
            json={"invoice_id": str(uuid.uuid4()), "challan_date": _CHALLAN_DATE},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_INVOICE_NOT_FOUND"

    async def test_draft_invoice_is_not_deliverable(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        draft_invoice = await _create_invoice(client, headers)
        response = await client.post(
            "/api/v1/delivery-challans",
            json={"invoice_id": draft_invoice["id"], "challan_date": _CHALLAN_DATE},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_INVOICE_NOT_DELIVERABLE"

    async def test_cannot_use_another_tenants_invoice(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)

        other_tenant = Tenant(
            name="Foreign DC Invoice Owner", slug=f"foreign-dc-inv-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_DC_PERMISSIONS)
        foreign_invoice, _ = await _issued_invoice_with_item(client, other_headers)

        response = await client.post(
            "/api/v1/delivery-challans",
            json={"invoice_id": foreign_invoice["id"], "challan_date": _CHALLAN_DATE},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_INVOICE_NOT_FOUND"


class TestGetDeliveryChallan:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/delivery-challans/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(f"/api/v1/delivery-challans/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_returns_the_challan(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_item(client, headers)
        created = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        response = await client.get(f"/api/v1/delivery-challans/{created['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(f"/api/v1/delivery-challans/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_NOT_FOUND"

    async def test_soft_deleted_challan_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_item(client, headers)
        created = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        await client.delete(f"/api/v1/delivery-challans/{created['id']}", headers=headers)
        response = await client.get(f"/api/v1/delivery-challans/{created['id']}", headers=headers)
        assert response.status_code == 404

    async def test_other_tenants_challan_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_item(client, headers)
        created = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])

        other_tenant = Tenant(name="Other DC Co", slug=f"other-dc-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_DC_PERMISSIONS)

        response = await client.get(
            f"/api/v1/delivery-challans/{created['id']}", headers=other_headers
        )
        assert response.status_code == 404


class TestListDeliveryChallans:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/delivery-challans")
        assert response.status_code == 401

    async def test_default_response_shape(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_item(client, headers)
        await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        response = await client.get("/api/v1/delivery-challans", headers=headers)
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

    async def test_filters_by_invoice_id(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice_a, _ = await _issued_invoice_with_item(client, headers)
        invoice_b, _ = await _issued_invoice_with_item(client, headers)
        target = await _create_delivery_challan(client, headers, invoice_id=invoice_a["id"])
        await _create_delivery_challan(client, headers, invoice_id=invoice_b["id"])

        response = await client.get(
            "/api/v1/delivery-challans", params={"invoice_id": invoice_a["id"]}, headers=headers
        )
        ids = [d["id"] for d in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_filters_by_status(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_item(client, headers)
        draft = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        dispatched = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        await _set_challan_status(db_session, dispatched["id"], DeliveryChallanStatus.DISPATCHED)

        response = await client.get(
            "/api/v1/delivery-challans",
            params={"status": "dispatched", "invoice_id": invoice["id"]},
            headers=headers,
        )
        ids = [d["id"] for d in response.json()["data"]]
        assert ids == [dispatched["id"]]
        assert draft["id"] not in ids

    async def test_invalid_sort_field_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/delivery-challans", params={"sort": "not_a_field"}, headers=headers
        )
        assert response.status_code == 422

    async def test_pagination_meta_is_correct(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_item(client, headers)
        for _ in range(3):
            await _create_delivery_challan(client, headers, invoice_id=invoice["id"])

        response = await client.get(
            "/api/v1/delivery-challans",
            params={"invoice_id": invoice["id"], "page": 1, "page_size": 2},
            headers=headers,
        )
        meta = response.json()["meta"]
        assert meta["total_records"] == 3
        assert meta["total_pages"] == 2
        assert meta["has_next"] is True
        assert meta["has_previous"] is False

    async def test_deleted_challans_are_excluded(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_item(client, headers)
        created = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        await client.delete(f"/api/v1/delivery-challans/{created['id']}", headers=headers)

        response = await client.get(
            "/api/v1/delivery-challans", params={"invoice_id": invoice["id"]}, headers=headers
        )
        assert response.json()["data"] == []

    async def test_tenant_isolation_returns_only_own_challans(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_item(client, headers)
        mine = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])

        other_tenant = Tenant(name="Other DC List Co", slug=f"other-dc-list-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_DC_PERMISSIONS)
        other_invoice, _ = await _issued_invoice_with_item(client, other_headers)
        await _create_delivery_challan(client, other_headers, invoice_id=other_invoice["id"])

        response = await client.get("/api/v1/delivery-challans", headers=headers)
        ids = [d["id"] for d in response.json()["data"]]
        assert mine["id"] in ids
        assert all(d["invoice_id"] != other_invoice["id"] for d in response.json()["data"])


class TestUpdateDeliveryChallan:
    async def test_requires_edit_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["delivery_challan:view"])
        response = await client.put(
            f"/api/v1/delivery-challans/{uuid.uuid4()}", json={"remarks": "x"}, headers=headers
        )
        assert response.status_code == 403

    async def test_success_updates_remarks(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_item(client, headers)
        created = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        response = await client.put(
            f"/api/v1/delivery-challans/{created['id']}",
            json={"remarks": "Updated"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["remarks"] == "Updated"

    async def test_rejects_update_on_non_draft(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_item(client, headers)
        created = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        await _set_challan_status(db_session, created["id"], DeliveryChallanStatus.DISPATCHED)

        response = await client.put(
            f"/api/v1/delivery-challans/{created['id']}", json={"remarks": "x"}, headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_NOT_DRAFT"

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            f"/api/v1/delivery-challans/{uuid.uuid4()}", json={"remarks": "x"}, headers=headers
        )
        assert response.status_code == 404


class TestDeleteDeliveryChallan:
    async def test_requires_delete_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["delivery_challan:view"])
        response = await client.delete(f"/api/v1/delivery-challans/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_success_soft_deletes(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_item(client, headers)
        created = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        response = await client.delete(
            f"/api/v1/delivery-challans/{created['id']}", headers=headers
        )
        assert response.status_code == 204

        get_response = await client.get(
            f"/api/v1/delivery-challans/{created['id']}", headers=headers
        )
        assert get_response.status_code == 404

    async def test_rejects_delete_on_non_draft(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_item(client, headers)
        created = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        await _set_challan_status(db_session, created["id"], DeliveryChallanStatus.DISPATCHED)

        response = await client.delete(
            f"/api/v1/delivery-challans/{created['id']}", headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_NOT_DRAFT"

    async def test_cannot_delete_another_tenants_challan(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_item(client, headers)
        created = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])

        other_tenant = Tenant(name="Other DC Deleter", slug=f"other-dc-del-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_DC_PERMISSIONS)

        response = await client.delete(
            f"/api/v1/delivery-challans/{created['id']}", headers=other_headers
        )
        assert response.status_code == 404

        still_there = await client.get(
            f"/api/v1/delivery-challans/{created['id']}", headers=headers
        )
        assert still_there.status_code == 200


class TestDeliveryChallanItemCrud:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            f"/api/v1/delivery-challans/{uuid.uuid4()}/items",
            json={"invoice_item_id": str(uuid.uuid4()), "quantity": "1.000"},
        )
        assert response.status_code == 401

    async def test_add_item_success_derives_unit_and_line_number(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice, item = await _issued_invoice_with_item(client, headers, unit="kg")
        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])

        response = await _add_challan_item(
            client, headers, challan["id"], invoice_item_id=item["id"], quantity="40.000"
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["line_number"] == 1
        assert body["quantity"] == "40.000"
        assert body["unit"] == "kg"
        assert body["invoice_item_id"] == item["id"]

    async def test_add_item_rejects_on_non_draft_challan(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice, item = await _issued_invoice_with_item(client, headers)
        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        await _set_challan_status(db_session, challan["id"], DeliveryChallanStatus.DISPATCHED)

        response = await _add_challan_item(
            client, headers, challan["id"], invoice_item_id=item["id"], quantity="10.000"
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_NOT_DRAFT"

    async def test_add_item_rejects_invoice_item_from_a_different_invoice(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        invoice_a, _ = await _issued_invoice_with_item(client, headers)
        invoice_b, item_b = await _issued_invoice_with_item(client, headers)
        challan = await _create_delivery_challan(client, headers, invoice_id=invoice_a["id"])

        response = await _add_challan_item(
            client, headers, challan["id"], invoice_item_id=item_b["id"], quantity="10.000"
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_INVOICE_ITEM_NOT_FOUND"

    async def test_add_item_over_delivery_in_one_shot_is_rejected(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        invoice, item = await _issued_invoice_with_item(client, headers, quantity="100.000")
        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])

        response = await _add_challan_item(
            client, headers, challan["id"], invoice_item_id=item["id"], quantity="150.000"
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_OVER_DELIVERY"

    async def test_list_items_ordered_by_line_number(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice, item = await _issued_invoice_with_item(client, headers, quantity="100.000")
        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        await _add_challan_item(
            client, headers, challan["id"], invoice_item_id=item["id"], quantity="10.000"
        )
        await _add_challan_item(
            client, headers, challan["id"], invoice_item_id=item["id"], quantity="20.000"
        )

        response = await client.get(
            f"/api/v1/delivery-challans/{challan['id']}/items", headers=headers
        )
        assert response.status_code == 200
        line_numbers = [i["line_number"] for i in response.json()]
        assert line_numbers == [1, 2]

    async def test_update_item_quantity_within_remaining_succeeds(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        invoice, item = await _issued_invoice_with_item(client, headers, quantity="100.000")
        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        add_response = await _add_challan_item(
            client, headers, challan["id"], invoice_item_id=item["id"], quantity="40.000"
        )
        challan_item = add_response.json()

        update_response = await client.put(
            f"/api/v1/delivery-challans/{challan['id']}/items/{challan_item['id']}",
            json={"quantity": "90.000"},
            headers=headers,
        )
        assert update_response.status_code == 200, update_response.text
        assert update_response.json()["quantity"] == "90.000"

    async def test_update_item_quantity_beyond_remaining_is_rejected(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        invoice, item = await _issued_invoice_with_item(client, headers, quantity="100.000")
        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        add_response = await _add_challan_item(
            client, headers, challan["id"], invoice_item_id=item["id"], quantity="40.000"
        )
        challan_item = add_response.json()

        update_response = await client.put(
            f"/api/v1/delivery-challans/{challan['id']}/items/{challan_item['id']}",
            json={"quantity": "101.000"},
            headers=headers,
        )
        assert update_response.status_code == 422
        assert update_response.json()["error"]["code"] == "DELIVERY_CHALLAN_OVER_DELIVERY"

    async def test_delete_item_frees_reserved_quantity(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice, item = await _issued_invoice_with_item(client, headers, quantity="100.000")
        challan_1 = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        add_response = await _add_challan_item(
            client, headers, challan_1["id"], invoice_item_id=item["id"], quantity="90.000"
        )
        challan_1_item = add_response.json()

        challan_2 = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        blocked = await _add_challan_item(
            client, headers, challan_2["id"], invoice_item_id=item["id"], quantity="50.000"
        )
        assert blocked.status_code == 422

        delete_response = await client.delete(
            f"/api/v1/delivery-challans/{challan_1['id']}/items/{challan_1_item['id']}",
            headers=headers,
        )
        assert delete_response.status_code == 204

        now_succeeds = await _add_challan_item(
            client, headers, challan_2["id"], invoice_item_id=item["id"], quantity="50.000"
        )
        assert now_succeeds.status_code == 201, now_succeeds.text

    async def test_delete_item_rejects_on_non_draft_challan(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice, item = await _issued_invoice_with_item(client, headers)
        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        add_response = await _add_challan_item(
            client, headers, challan["id"], invoice_item_id=item["id"], quantity="10.000"
        )
        challan_item = add_response.json()
        await _set_challan_status(db_session, challan["id"], DeliveryChallanStatus.DISPATCHED)

        response = await client.delete(
            f"/api/v1/delivery-challans/{challan['id']}/items/{challan_item['id']}",
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_NOT_DRAFT"
