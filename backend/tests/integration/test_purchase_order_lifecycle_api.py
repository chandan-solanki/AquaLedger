import uuid
from decimal import Decimal
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.suppliers.models import Supplier

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

# _create_purchase_order provisions a fresh supplier via the API by
# default, so test users need supplier:create access too for that setup to
# succeed, plus every lifecycle permission.
_ALL_LIFECYCLE_PERMISSIONS = [
    "purchase_order:view",
    "purchase_order:create",
    "purchase_order:edit",
    "purchase_order:delete",
    "purchase_order:confirm",
    "purchase_order:cancel",
    "purchase_order:fulfill",
    "supplier:view",
    "supplier:create",
]
_ORDER_DATE = "2026-08-15"


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


async def _create_supplier(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": f"LIFESUP-{uuid.uuid4().hex[:8]}",
        "name": f"Lifecycle Supplier {uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/suppliers", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_purchase_order(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    supplier_id: str | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    if supplier_id is None:
        supplier_id = (await _create_supplier(client, headers))["id"]
    payload: dict[str, Any] = {"supplier_id": supplier_id, "order_date": _ORDER_DATE}
    payload.update(overrides)
    response = await client.post("/api/v1/purchase-orders", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _add_item(
    client: AsyncClient, headers: dict[str, str], purchase_order_id: str, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "description": "Pomfret - Grade A",
        "quantity": "10.000",
        "unit": "KG",
        "rate": "100.0000",
    }
    payload.update(overrides)
    response = await client.post(
        f"/api/v1/purchase-orders/{purchase_order_id}/items", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _confirm(client: AsyncClient, headers: dict[str, str], order_id: str) -> Any:
    return await client.post(f"/api/v1/purchase-orders/{order_id}/confirm", headers=headers)


async def _cancel(client: AsyncClient, headers: dict[str, str], order_id: str) -> Any:
    return await client.post(f"/api/v1/purchase-orders/{order_id}/cancel", headers=headers)


async def _fulfill(client: AsyncClient, headers: dict[str, str], order_id: str) -> Any:
    return await client.post(f"/api/v1/purchase-orders/{order_id}/fulfill", headers=headers)


async def _draft_order_with_item(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    supplier_id: str | None = None,
    **item_overrides: Any,
) -> dict[str, Any]:
    order = await _create_purchase_order(client, headers, supplier_id=supplier_id)
    await _add_item(client, headers, order["id"], **item_overrides)
    return order


class TestConfirmEndpointAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(f"/api/v1/purchase-orders/{uuid.uuid4()}/confirm")
        assert response.status_code == 401

    async def test_requires_confirm_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """A user with every other purchase_order permission but not
        purchase_order:confirm must still be rejected - confirm is its own
        route-level permission, distinct from purchase_order:edit."""
        tenant_id = await _admin_tenant_id(client)
        admin_headers = await _admin_headers(client)
        order = await _draft_order_with_item(client, admin_headers)

        permissions_without_confirm = [
            p for p in _ALL_LIFECYCLE_PERMISSIONS if p != "purchase_order:confirm"
        ]
        limited_headers = await _make_user_headers(
            db_session, tenant_id, permissions_without_confirm
        )

        response = await _confirm(client, limited_headers, order["id"])
        assert response.status_code == 403


class TestSuccessfulConfirm:
    async def test_confirms_a_draft_purchase_order(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        order = await _draft_order_with_item(
            client, headers, quantity="20.000", rate="500.0000", tax_rate="5.00"
        )

        response = await _confirm(client, headers, order["id"])

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "confirmed"
        assert body["po_number"] is not None
        assert body["po_number"].startswith("PO/")
        assert body["confirmed_at"] is not None
        assert body["total_amount"] == "10500.00"

    async def test_confirmed_order_is_visible_via_get(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        order = await _draft_order_with_item(client, headers)
        await _confirm(client, headers, order["id"])

        response = await client.get(f"/api/v1/purchase-orders/{order['id']}", headers=headers)

        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

    async def test_returns_404_for_an_unknown_order(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await _confirm(client, headers, str(uuid.uuid4()))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_ORDER_NOT_FOUND"

    async def test_returns_404_for_a_soft_deleted_draft_order(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        order = await _create_purchase_order(client, headers)
        delete_response = await client.delete(
            f"/api/v1/purchase-orders/{order['id']}", headers=headers
        )
        assert delete_response.status_code == 204

        response = await _confirm(client, headers, order["id"])
        assert response.status_code == 404

    async def test_never_changes_supplier_outstanding(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The task's core business principle: confirming a PO must never
        increase supplier outstanding, unlike posting a purchase bill."""
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order = await _draft_order_with_item(
            client, headers, supplier_id=supplier["id"], quantity="10.000", rate="100.0000"
        )

        response = await _confirm(client, headers, order["id"])
        assert response.status_code == 200

        supplier_row = (
            await db_session.execute(
                select(Supplier).where(Supplier.id == uuid.UUID(supplier["id"]))
            )
        ).scalar_one()
        assert supplier_row.outstanding_amount == Decimal("0")


class TestConfirmTenantIsolation:
    async def test_returns_404_for_an_order_belonging_to_another_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Other Confirm Tenant", slug=f"other-confirm-tenant-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_LIFECYCLE_PERMISSIONS
        )
        other_order = await _draft_order_with_item(client, other_headers)

        admin_headers = await _admin_headers(client)
        response = await _confirm(client, admin_headers, other_order["id"])
        assert response.status_code == 404


class TestConfirmBusinessRuleFailures:
    async def test_confirming_twice_returns_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        order = await _draft_order_with_item(client, headers)
        first = await _confirm(client, headers, order["id"])
        assert first.status_code == 200

        second = await _confirm(client, headers, order["id"])
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "PURCHASE_ORDER_NOT_DRAFT"

    async def test_empty_order_returns_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        order = await _create_purchase_order(client, headers)

        response = await _confirm(client, headers, order["id"])
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PURCHASE_ORDER_EMPTY"


class TestImmutabilityAfterConfirm:
    async def test_confirmed_order_cannot_be_updated(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        order = await _draft_order_with_item(client, headers)
        await _confirm(client, headers, order["id"])

        response = await client.put(
            f"/api/v1/purchase-orders/{order['id']}",
            json={"remarks": "Trying to edit a confirmed order"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PURCHASE_ORDER_NOT_DRAFT"

    async def test_confirmed_order_cannot_be_deleted(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        order = await _draft_order_with_item(client, headers)
        await _confirm(client, headers, order["id"])

        response = await client.delete(f"/api/v1/purchase-orders/{order['id']}", headers=headers)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PURCHASE_ORDER_NOT_DRAFT"

    async def test_cannot_add_an_item_to_a_confirmed_order(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        order = await _draft_order_with_item(client, headers)
        await _confirm(client, headers, order["id"])

        response = await client.post(
            f"/api/v1/purchase-orders/{order['id']}/items",
            json={"description": "New", "quantity": "1.000", "unit": "KG", "rate": "1.0000"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PURCHASE_ORDER_NOT_DRAFT"


class TestCancelEndpointAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(f"/api/v1/purchase-orders/{uuid.uuid4()}/cancel")
        assert response.status_code == 401

    async def test_requires_cancel_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        admin_headers = await _admin_headers(client)
        order = await _create_purchase_order(client, admin_headers)

        permissions_without_cancel = [
            p for p in _ALL_LIFECYCLE_PERMISSIONS if p != "purchase_order:cancel"
        ]
        limited_headers = await _make_user_headers(
            db_session, tenant_id, permissions_without_cancel
        )

        response = await _cancel(client, limited_headers, order["id"])
        assert response.status_code == 403


class TestSuccessfulCancel:
    async def test_cancels_a_draft_order(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        order = await _create_purchase_order(client, headers)

        response = await _cancel(client, headers, order["id"])
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    async def test_cancels_a_confirmed_order(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        order = await _draft_order_with_item(client, headers)
        await _confirm(client, headers, order["id"])

        response = await _cancel(client, headers, order["id"])
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    async def test_returns_404_for_an_unknown_order(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await _cancel(client, headers, str(uuid.uuid4()))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_ORDER_NOT_FOUND"

    async def test_never_changes_supplier_outstanding(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order = await _draft_order_with_item(client, headers, supplier_id=supplier["id"])
        await _confirm(client, headers, order["id"])

        response = await _cancel(client, headers, order["id"])
        assert response.status_code == 200

        supplier_row = (
            await db_session.execute(
                select(Supplier).where(Supplier.id == uuid.UUID(supplier["id"]))
            )
        ).scalar_one()
        assert supplier_row.outstanding_amount == Decimal("0")


class TestCancelTenantIsolation:
    async def test_returns_404_for_an_order_belonging_to_another_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Other Cancel Tenant", slug=f"other-cancel-tenant-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_LIFECYCLE_PERMISSIONS
        )
        other_order = await _create_purchase_order(client, other_headers)

        admin_headers = await _admin_headers(client)
        response = await _cancel(client, admin_headers, other_order["id"])
        assert response.status_code == 404


class TestCancelBusinessRuleFailures:
    async def test_cancelling_a_fulfilled_order_returns_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        order = await _draft_order_with_item(client, headers)
        await _confirm(client, headers, order["id"])
        await _fulfill(client, headers, order["id"])

        response = await _cancel(client, headers, order["id"])
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PURCHASE_ORDER_INVALID_TRANSITION"

    async def test_cancelling_twice_returns_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        order = await _create_purchase_order(client, headers)
        first = await _cancel(client, headers, order["id"])
        assert first.status_code == 200

        second = await _cancel(client, headers, order["id"])
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "PURCHASE_ORDER_INVALID_TRANSITION"


class TestFulfillEndpointAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(f"/api/v1/purchase-orders/{uuid.uuid4()}/fulfill")
        assert response.status_code == 401

    async def test_requires_fulfill_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        admin_headers = await _admin_headers(client)
        order = await _draft_order_with_item(client, admin_headers)
        await _confirm(client, admin_headers, order["id"])

        permissions_without_fulfill = [
            p for p in _ALL_LIFECYCLE_PERMISSIONS if p != "purchase_order:fulfill"
        ]
        limited_headers = await _make_user_headers(
            db_session, tenant_id, permissions_without_fulfill
        )

        response = await _fulfill(client, limited_headers, order["id"])
        assert response.status_code == 403


class TestSuccessfulFulfill:
    async def test_fulfills_a_confirmed_order(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        order = await _draft_order_with_item(client, headers)
        await _confirm(client, headers, order["id"])

        response = await _fulfill(client, headers, order["id"])
        assert response.status_code == 200
        assert response.json()["status"] == "fulfilled"

    async def test_returns_404_for_an_unknown_order(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await _fulfill(client, headers, str(uuid.uuid4()))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_ORDER_NOT_FOUND"

    async def test_never_changes_supplier_outstanding(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order = await _draft_order_with_item(client, headers, supplier_id=supplier["id"])
        await _confirm(client, headers, order["id"])

        response = await _fulfill(client, headers, order["id"])
        assert response.status_code == 200

        supplier_row = (
            await db_session.execute(
                select(Supplier).where(Supplier.id == uuid.UUID(supplier["id"]))
            )
        ).scalar_one()
        assert supplier_row.outstanding_amount == Decimal("0")


class TestFulfillTenantIsolation:
    async def test_returns_404_for_an_order_belonging_to_another_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Other Fulfill Tenant", slug=f"other-fulfill-tenant-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_LIFECYCLE_PERMISSIONS
        )
        other_order = await _draft_order_with_item(client, other_headers)
        await _confirm(client, other_headers, other_order["id"])

        admin_headers = await _admin_headers(client)
        response = await _fulfill(client, admin_headers, other_order["id"])
        assert response.status_code == 404


class TestFulfillBusinessRuleFailures:
    async def test_fulfilling_a_draft_order_returns_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        order = await _create_purchase_order(client, headers)

        response = await _fulfill(client, headers, order["id"])
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PURCHASE_ORDER_INVALID_TRANSITION"

    async def test_fulfilling_twice_returns_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        order = await _draft_order_with_item(client, headers)
        await _confirm(client, headers, order["id"])
        first = await _fulfill(client, headers, order["id"])
        assert first.status_code == 200

        second = await _fulfill(client, headers, order["id"])
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "PURCHASE_ORDER_INVALID_TRANSITION"

    async def test_fulfilling_a_cancelled_order_returns_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        order = await _create_purchase_order(client, headers)
        await _cancel(client, headers, order["id"])

        response = await _fulfill(client, headers, order["id"])
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PURCHASE_ORDER_INVALID_TRANSITION"
