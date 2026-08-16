"""Integration tests for the Purchase Order -> Purchase Bill linkage
(Sprint 12 Session 12): the optional `purchase_order_id` header link and
`purchase_order_item_id` item link, multi-bill partial billing, item-level
over-billing rejection, and the derived billing summary exposed on
GET /api/v1/purchase-orders/{id} and .../items.

Mirrors test_purchase_bill_document_api.py's and test_purchase_posting_api.py's
helper style - fresh supplier/PO/bill chains are provisioned per test via
the real API. Assertions on financial invariants (supplier outstanding)
read the row back directly via db_session, the same pattern
test_purchase_posting_api.py already uses.
"""

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

_ALL_PERMISSIONS = [
    "purchase_order:view",
    "purchase_order:create",
    "purchase_order:edit",
    "purchase_order:delete",
    "purchase_order:confirm",
    "purchase_order:cancel",
    "purchase_order:fulfill",
    "purchase:view",
    "purchase:create",
    "purchase:edit",
    "purchase:delete",
    "purchase:post",
    "supplier:view",
    "supplier:create",
]
_ORDER_DATE = "2026-07-22"
_BILL_DATE = "2026-07-23"


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
        "code": f"LINKSUP-{uuid.uuid4().hex[:8]}",
        "name": f"Link Supplier {uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/suppliers", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_purchase_order(
    client: AsyncClient, headers: dict[str, str], *, supplier_id: str, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"supplier_id": supplier_id, "order_date": _ORDER_DATE}
    payload.update(overrides)
    response = await client.post("/api/v1/purchase-orders", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _add_po_item(
    client: AsyncClient, headers: dict[str, str], purchase_order_id: str, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "description": "Pomfret - Grade A",
        "quantity": "100.000",
        "unit": "KG",
        "rate": "200.0000",
    }
    payload.update(overrides)
    response = await client.post(
        f"/api/v1/purchase-orders/{purchase_order_id}/items", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _confirmed_po_with_item(
    client: AsyncClient, headers: dict[str, str], *, supplier_id: str, **item_overrides: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    order = await _create_purchase_order(client, headers, supplier_id=supplier_id)
    item = await _add_po_item(client, headers, order["id"], **item_overrides)
    response = await client.post(f"/api/v1/purchase-orders/{order['id']}/confirm", headers=headers)
    assert response.status_code == 200, response.text
    confirmed: dict[str, Any] = response.json()
    return confirmed, item


async def _create_purchase_bill(
    client: AsyncClient, headers: dict[str, str], *, supplier_id: str, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"supplier_id": supplier_id, "bill_date": _BILL_DATE}
    payload.update(overrides)
    response = await client.post("/api/v1/purchase", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _add_bill_item(
    client: AsyncClient, headers: dict[str, str], purchase_bill_id: str, **overrides: Any
) -> Any:
    payload: dict[str, Any] = {
        "description": "Pomfret - Grade A",
        "quantity": "10.000",
        "unit": "KG",
        "rate": "100.0000",
    }
    payload.update(overrides)
    return await client.post(
        f"/api/v1/purchase/{purchase_bill_id}/items", json=payload, headers=headers
    )


class TestStandaloneFlowsUnaffected:
    """Section 30 items 1-2: neither side of the relationship is mandatory."""

    async def test_purchase_order_can_exist_without_any_bills(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order, _ = await _confirmed_po_with_item(client, headers, supplier_id=supplier["id"])

        # confirm()'s own response is the plain PurchaseOrderResponse (no
        # billing fields) - only GET /{id} returns the extended
        # PurchaseOrderDetailResponse.
        detail_response = await client.get(
            f"/api/v1/purchase-orders/{order['id']}", headers=headers
        )
        assert detail_response.json()["billing_status"] == "not_billed"

    async def test_purchase_bill_can_be_created_without_a_purchase_order(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        bill = await _create_purchase_bill(client, headers, supplier_id=supplier["id"])
        assert bill["purchase_order_id"] is None

        item_response = await _add_bill_item(client, headers, bill["id"])
        assert item_response.status_code == 201, item_response.text
        assert item_response.json()["purchase_order_item_id"] is None

        post_response = await client.post(f"/api/v1/purchase/{bill['id']}/post", headers=headers)
        assert post_response.status_code == 200, post_response.text


class TestHeaderLinkValidation:
    async def test_bill_can_link_to_a_confirmed_purchase_order(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order, _ = await _confirmed_po_with_item(client, headers, supplier_id=supplier["id"])

        bill = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], purchase_order_id=order["id"]
        )
        assert bill["purchase_order_id"] == order["id"]

    async def test_bill_can_link_to_a_fulfilled_purchase_order(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order, _ = await _confirmed_po_with_item(client, headers, supplier_id=supplier["id"])
        fulfill_response = await client.post(
            f"/api/v1/purchase-orders/{order['id']}/fulfill", headers=headers
        )
        assert fulfill_response.status_code == 200, fulfill_response.text

        bill = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], purchase_order_id=order["id"]
        )
        assert bill["purchase_order_id"] == order["id"]

    async def test_rejects_linking_a_draft_purchase_order(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        draft_order = await _create_purchase_order(client, headers, supplier_id=supplier["id"])

        response = await client.post(
            "/api/v1/purchase",
            json={
                "supplier_id": supplier["id"],
                "bill_date": _BILL_DATE,
                "purchase_order_id": draft_order["id"],
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PURCHASE_BILL_PURCHASE_ORDER_NOT_BILLABLE"

    async def test_rejects_linking_a_cancelled_purchase_order(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order, _ = await _confirmed_po_with_item(client, headers, supplier_id=supplier["id"])
        cancel_response = await client.post(
            f"/api/v1/purchase-orders/{order['id']}/cancel", headers=headers
        )
        assert cancel_response.status_code == 200, cancel_response.text

        response = await client.post(
            "/api/v1/purchase",
            json={
                "supplier_id": supplier["id"],
                "bill_date": _BILL_DATE,
                "purchase_order_id": order["id"],
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PURCHASE_BILL_PURCHASE_ORDER_NOT_BILLABLE"

    async def test_rejects_linking_a_purchase_order_with_a_different_supplier(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        supplier_a = await _create_supplier(client, headers)
        supplier_b = await _create_supplier(client, headers)
        order, _ = await _confirmed_po_with_item(client, headers, supplier_id=supplier_a["id"])

        response = await client.post(
            "/api/v1/purchase",
            json={
                "supplier_id": supplier_b["id"],
                "bill_date": _BILL_DATE,
                "purchase_order_id": order["id"],
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PURCHASE_BILL_SUPPLIER_MISMATCH"

    async def test_rejects_linking_an_unknown_purchase_order(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)

        response = await client.post(
            "/api/v1/purchase",
            json={
                "supplier_id": supplier["id"],
                "bill_date": _BILL_DATE,
                "purchase_order_id": str(uuid.uuid4()),
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_BILL_PURCHASE_ORDER_NOT_FOUND"

    async def test_rejects_linking_a_purchase_order_from_another_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Other Linkage Tenant",
            slug=f"other-linkage-tenant-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_PERMISSIONS)
        other_supplier = await _create_supplier(client, other_headers)
        other_order, _ = await _confirmed_po_with_item(
            client, other_headers, supplier_id=other_supplier["id"]
        )

        admin_headers = await _admin_headers(client)
        admin_supplier = await _create_supplier(client, admin_headers)
        response = await client.post(
            "/api/v1/purchase",
            json={
                "supplier_id": admin_supplier["id"],
                "bill_date": _BILL_DATE,
                "purchase_order_id": other_order["id"],
            },
            headers=admin_headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_BILL_PURCHASE_ORDER_NOT_FOUND"


class TestPartialBillingAndOverBilling:
    """Section 30 items 10-18: multiple bills against one PO item,
    cumulative remaining tracking, and hard over-billing rejection."""

    async def test_full_partial_billing_sequence_across_three_separate_bills(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order, po_item = await _confirmed_po_with_item(
            client, headers, supplier_id=supplier["id"], quantity="100.000", rate="200.0000"
        )

        # Bill #1: 40 KG -> remaining 60.
        bill_1 = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], purchase_order_id=order["id"]
        )
        response_1 = await _add_bill_item(
            client,
            headers,
            bill_1["id"],
            quantity="40.000",
            purchase_order_item_id=po_item["id"],
        )
        assert response_1.status_code == 201, response_1.text

        items_after_1 = await client.get(
            f"/api/v1/purchase-orders/{order['id']}/items", headers=headers
        )
        item_1 = items_after_1.json()[0]
        assert item_1["billed_quantity"] == "40.000"
        assert item_1["remaining_quantity"] == "60.000"

        po_after_1 = await client.get(f"/api/v1/purchase-orders/{order['id']}", headers=headers)
        assert po_after_1.json()["billing_status"] == "partially_billed"

        # Bill #2: 30 KG more -> remaining 30.
        bill_2 = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], purchase_order_id=order["id"]
        )
        response_2 = await _add_bill_item(
            client,
            headers,
            bill_2["id"],
            quantity="30.000",
            purchase_order_item_id=po_item["id"],
        )
        assert response_2.status_code == 201, response_2.text

        items_after_2 = await client.get(
            f"/api/v1/purchase-orders/{order['id']}/items", headers=headers
        )
        assert items_after_2.json()[0]["billed_quantity"] == "70.000"
        assert items_after_2.json()[0]["remaining_quantity"] == "30.000"

        # Bill #3: 30 KG more -> remaining 0, fully billed.
        bill_3 = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], purchase_order_id=order["id"]
        )
        response_3 = await _add_bill_item(
            client,
            headers,
            bill_3["id"],
            quantity="30.000",
            purchase_order_item_id=po_item["id"],
        )
        assert response_3.status_code == 201, response_3.text

        items_after_3 = await client.get(
            f"/api/v1/purchase-orders/{order['id']}/items", headers=headers
        )
        assert items_after_3.json()[0]["billed_quantity"] == "100.000"
        assert items_after_3.json()[0]["remaining_quantity"] == "0.000"
        po_after_3 = await client.get(f"/api/v1/purchase-orders/{order['id']}", headers=headers)
        assert po_after_3.json()["billing_status"] == "fully_billed"

        # Bill #4: 1 KG more -> rejected, nothing left to bill.
        bill_4 = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], purchase_order_id=order["id"]
        )
        response_4 = await _add_bill_item(
            client,
            headers,
            bill_4["id"],
            quantity="1.000",
            purchase_order_item_id=po_item["id"],
        )
        assert response_4.status_code == 422
        assert response_4.json()["error"]["code"] == "PURCHASE_BILL_OVER_BILLING"

    async def test_single_bill_over_billing_in_one_shot_is_rejected(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order, po_item = await _confirmed_po_with_item(
            client, headers, supplier_id=supplier["id"], quantity="100.000"
        )
        bill = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], purchase_order_id=order["id"]
        )
        response = await _add_bill_item(
            client, headers, bill["id"], quantity="150.000", purchase_order_item_id=po_item["id"]
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PURCHASE_BILL_OVER_BILLING"

    async def test_updating_item_quantity_within_remaining_succeeds(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order, po_item = await _confirmed_po_with_item(
            client, headers, supplier_id=supplier["id"], quantity="100.000"
        )
        bill = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], purchase_order_id=order["id"]
        )
        add_response = await _add_bill_item(
            client, headers, bill["id"], quantity="40.000", purchase_order_item_id=po_item["id"]
        )
        bill_item = add_response.json()

        update_response = await client.put(
            f"/api/v1/purchase/{bill['id']}/items/{bill_item['id']}",
            json={"quantity": "90.000"},
            headers=headers,
        )
        assert update_response.status_code == 200, update_response.text
        assert update_response.json()["quantity"] == "90.000"

    async def test_updating_item_quantity_beyond_remaining_is_rejected(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order, po_item = await _confirmed_po_with_item(
            client, headers, supplier_id=supplier["id"], quantity="100.000"
        )
        bill = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], purchase_order_id=order["id"]
        )
        add_response = await _add_bill_item(
            client, headers, bill["id"], quantity="40.000", purchase_order_item_id=po_item["id"]
        )
        bill_item = add_response.json()

        update_response = await client.put(
            f"/api/v1/purchase/{bill['id']}/items/{bill_item['id']}",
            json={"quantity": "101.000"},
            headers=headers,
        )
        assert update_response.status_code == 422
        assert update_response.json()["error"]["code"] == "PURCHASE_BILL_OVER_BILLING"

    async def test_deleting_a_draft_bill_item_frees_its_reserved_quantity(
        self, client: AsyncClient
    ) -> None:
        """Confirms the "reservation" design: an abandoned draft item's
        quantity is only ever a live aggregate, never a stored counter -
        deleting it immediately frees the quantity for a different bill."""
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order, po_item = await _confirmed_po_with_item(
            client, headers, supplier_id=supplier["id"], quantity="100.000"
        )
        bill_1 = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], purchase_order_id=order["id"]
        )
        add_response = await _add_bill_item(
            client, headers, bill_1["id"], quantity="90.000", purchase_order_item_id=po_item["id"]
        )
        bill_1_item = add_response.json()

        # A second bill trying to also claim 50 KG would exceed remaining
        # (100 - 90 = 10) while bill_1's item still exists.
        bill_2 = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], purchase_order_id=order["id"]
        )
        blocked_response = await _add_bill_item(
            client, headers, bill_2["id"], quantity="50.000", purchase_order_item_id=po_item["id"]
        )
        assert blocked_response.status_code == 422

        delete_response = await client.delete(
            f"/api/v1/purchase/{bill_1['id']}/items/{bill_1_item['id']}", headers=headers
        )
        assert delete_response.status_code == 204

        now_succeeds = await _add_bill_item(
            client, headers, bill_2["id"], quantity="50.000", purchase_order_item_id=po_item["id"]
        )
        assert now_succeeds.status_code == 201, now_succeeds.text

    async def test_item_link_requires_bill_header_to_be_linked(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order, po_item = await _confirmed_po_with_item(client, headers, supplier_id=supplier["id"])
        # Bill created WITHOUT a purchase_order_id.
        bill = await _create_purchase_bill(client, headers, supplier_id=supplier["id"])

        response = await _add_bill_item(
            client, headers, bill["id"], purchase_order_item_id=po_item["id"]
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_LINKED_TO_PURCHASE_ORDER"

    async def test_item_link_rejects_an_item_from_a_different_purchase_order(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order_a, _ = await _confirmed_po_with_item(client, headers, supplier_id=supplier["id"])
        order_b, item_b = await _confirmed_po_with_item(client, headers, supplier_id=supplier["id"])
        bill = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], purchase_order_id=order_a["id"]
        )

        response = await _add_bill_item(
            client, headers, bill["id"], purchase_order_item_id=item_b["id"]
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_BILL_PURCHASE_ORDER_ITEM_NOT_FOUND"

    async def test_multiple_items_on_one_po_bill_independently(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order = await _create_purchase_order(client, headers, supplier_id=supplier["id"])
        item_a = await _add_po_item(
            client, headers, order["id"], description="Pomfret", quantity="100.000"
        )
        item_b = await _add_po_item(
            client, headers, order["id"], description="Surmai", quantity="50.000"
        )
        confirm_response = await client.post(
            f"/api/v1/purchase-orders/{order['id']}/confirm", headers=headers
        )
        assert confirm_response.status_code == 200, confirm_response.text

        bill = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], purchase_order_id=order["id"]
        )
        response_a = await _add_bill_item(
            client, headers, bill["id"], quantity="60.000", purchase_order_item_id=item_a["id"]
        )
        assert response_a.status_code == 201, response_a.text
        response_b = await _add_bill_item(
            client, headers, bill["id"], quantity="50.000", purchase_order_item_id=item_b["id"]
        )
        assert response_b.status_code == 201, response_b.text

        items = (
            await client.get(f"/api/v1/purchase-orders/{order['id']}/items", headers=headers)
        ).json()
        by_id = {item["id"]: item for item in items}
        assert by_id[item_a["id"]]["billed_quantity"] == "60.000"
        assert by_id[item_a["id"]]["remaining_quantity"] == "40.000"
        assert by_id[item_b["id"]]["billed_quantity"] == "50.000"
        assert by_id[item_b["id"]]["remaining_quantity"] == "0.000"


class TestFinancialInvariants:
    """Section 30 items 19-26 and the brief's own hard invariant: the PO
    never owns supplier outstanding, only PurchaseBill.post() does,
    exactly once."""

    async def test_po_creation_confirmation_and_fulfillment_never_touch_outstanding(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        supplier_row = (
            await db_session.execute(
                select(Supplier).where(Supplier.id == uuid.UUID(supplier["id"]))
            )
        ).scalar_one()
        assert supplier_row.outstanding_amount == 0

        order, _ = await _confirmed_po_with_item(client, headers, supplier_id=supplier["id"])
        await db_session.refresh(supplier_row)
        assert supplier_row.outstanding_amount == 0

        fulfill_response = await client.post(
            f"/api/v1/purchase-orders/{order['id']}/fulfill", headers=headers
        )
        assert fulfill_response.status_code == 200, fulfill_response.text
        await db_session.refresh(supplier_row)
        assert supplier_row.outstanding_amount == 0

    async def test_linked_draft_bill_item_creation_does_not_affect_outstanding(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order, po_item = await _confirmed_po_with_item(client, headers, supplier_id=supplier["id"])
        bill = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], purchase_order_id=order["id"]
        )
        add_response = await _add_bill_item(
            client, headers, bill["id"], quantity="40.000", purchase_order_item_id=po_item["id"]
        )
        assert add_response.status_code == 201, add_response.text

        supplier_row = (
            await db_session.execute(
                select(Supplier).where(Supplier.id == uuid.UUID(supplier["id"]))
            )
        ).scalar_one()
        assert supplier_row.outstanding_amount == 0

    async def test_posting_the_linked_bill_increases_outstanding_exactly_once(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order, po_item = await _confirmed_po_with_item(client, headers, supplier_id=supplier["id"])
        bill = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], purchase_order_id=order["id"]
        )
        await _add_bill_item(
            client,
            headers,
            bill["id"],
            quantity="40.000",
            rate="200.0000",
            purchase_order_item_id=po_item["id"],
        )

        post_response = await client.post(f"/api/v1/purchase/{bill['id']}/post", headers=headers)
        assert post_response.status_code == 200, post_response.text
        posted_bill = post_response.json()

        supplier_row = (
            await db_session.execute(
                select(Supplier).where(Supplier.id == uuid.UUID(supplier["id"]))
            )
        ).scalar_one()
        assert supplier_row.outstanding_amount == Decimal(posted_bill["balance_amount"])
        assert supplier_row.outstanding_amount != 0

        # The PO's own status is untouched by billing/posting - no
        # automatic fulfillment.
        po_after_post = await client.get(f"/api/v1/purchase-orders/{order['id']}", headers=headers)
        assert po_after_post.json()["status"] == "confirmed"
        assert po_after_post.json()["billing_status"] == "partially_billed"


class TestPurchaseBillReflectsPurchaseOrderReference:
    async def test_bill_response_includes_purchase_order_id_when_linked(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order, _ = await _confirmed_po_with_item(client, headers, supplier_id=supplier["id"])
        bill = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], purchase_order_id=order["id"]
        )
        get_response = await client.get(f"/api/v1/purchase/{bill['id']}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["purchase_order_id"] == order["id"]

    async def test_po_document_generation_still_works_after_linkage_exists(
        self, client: AsyncClient
    ) -> None:
        """Session 11's PDF/Document Center integration must be entirely
        unaffected by this session's linkage feature."""
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order, _ = await _confirmed_po_with_item(client, headers, supplier_id=supplier["id"])
        await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], purchase_order_id=order["id"]
        )

        document_response = await client.get(
            f"/api/v1/purchase-orders/{order['id']}/document", headers=headers
        )
        assert document_response.status_code == 200
        assert document_response.content.startswith(b"%PDF-")

        documents_list = await client.get(
            "/api/v1/documents", params={"q": order["po_number"]}, headers=headers
        )
        assert documents_list.status_code == 200
        assert len(documents_list.json()["data"]) == 1


class TestLinkedPurchaseBillsEndpoint:
    """GET /purchase-orders/{id}/purchase-bills (Sprint 12 Session 13) - the
    "Purchase Bills" list on the Purchase Order Detail page."""

    async def test_empty_when_no_bills_linked(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order, _ = await _confirmed_po_with_item(client, headers, supplier_id=supplier["id"])

        response = await client.get(
            f"/api/v1/purchase-orders/{order['id']}/purchase-bills", headers=headers
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_linked_bills_most_recent_bill_date_first(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order, _ = await _confirmed_po_with_item(
            client, headers, supplier_id=supplier["id"], quantity="100.000"
        )
        older = await _create_purchase_bill(
            client,
            headers,
            supplier_id=supplier["id"],
            purchase_order_id=order["id"],
            bill_date="2026-07-10",
        )
        newer = await _create_purchase_bill(
            client,
            headers,
            supplier_id=supplier["id"],
            purchase_order_id=order["id"],
            bill_date="2026-07-20",
        )
        # An unrelated standalone bill for the same supplier must not appear.
        await _create_purchase_bill(client, headers, supplier_id=supplier["id"])

        response = await client.get(
            f"/api/v1/purchase-orders/{order['id']}/purchase-bills", headers=headers
        )
        assert response.status_code == 200
        ids = [bill["id"] for bill in response.json()]
        assert ids == [newer["id"], older["id"]]

    async def test_bill_fields_shown(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order, po_item = await _confirmed_po_with_item(
            client, headers, supplier_id=supplier["id"], quantity="100.000"
        )
        bill = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], purchase_order_id=order["id"]
        )
        await _add_bill_item(
            client,
            headers,
            bill["id"],
            quantity="40.000",
            rate="200.0000",
            purchase_order_item_id=po_item["id"],
        )
        await client.post(f"/api/v1/purchase/{bill['id']}/post", headers=headers)

        response = await client.get(
            f"/api/v1/purchase-orders/{order['id']}/purchase-bills", headers=headers
        )
        assert response.status_code == 200
        [linked] = response.json()
        assert linked["id"] == bill["id"]
        assert linked["bill_number"] is not None
        assert linked["status"] == "posted"
        assert linked["total_amount"] == "8000.00"
        assert linked["balance_amount"] == "8000.00"

    async def test_unknown_purchase_order_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/purchase-orders/{uuid.uuid4()}/purchase-bills", headers=headers
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_ORDER_NOT_FOUND"

    async def test_requires_purchase_order_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(
            f"/api/v1/purchase-orders/{uuid.uuid4()}/purchase-bills", headers=headers
        )
        assert response.status_code == 403

    async def test_tenant_isolation(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        order, _ = await _confirmed_po_with_item(client, headers, supplier_id=supplier["id"])

        other_tenant = Tenant(
            name="Other Linked Bills Tenant",
            slug=f"other-linked-bills-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_PERMISSIONS)

        response = await client.get(
            f"/api/v1/purchase-orders/{order['id']}/purchase-bills", headers=other_headers
        )
        assert response.status_code == 404
