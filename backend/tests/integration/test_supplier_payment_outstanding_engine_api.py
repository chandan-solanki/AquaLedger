import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

_ALL_OUTSTANDING_PERMISSIONS = [
    "supplier_payment:view",
    "supplier_payment:create",
    "supplier_payment:edit",
    "supplier_payment:delete",
    "supplier:view",
    "supplier:create",
    "purchase:view",
    "purchase:create",
    "purchase:edit",
    "purchase:post",
]
_PAYMENT_DATE = "2026-07-23"
_BILL_DATE = "2026-07-22"


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


async def _make_tenant_headers(
    db_session: AsyncSession, *, name_hint: str
) -> tuple[dict[str, str], uuid.UUID]:
    """A fresh tenant with a full-access user - the outstanding engine
    touches suppliers, purchase bills and supplier payments together, so a
    dedicated tenant per test keeps supplier.outstanding_amount assertions
    from being polluted by other tests' data. Mirrors
    test_payment_outstanding_engine_api.py's own helper on the buy side."""
    tenant = Tenant(
        name=name_hint, slug=f"{name_hint.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
    )
    db_session.add(tenant)
    await db_session.commit()
    headers = await _make_user_headers(db_session, tenant.id, _ALL_OUTSTANDING_PERMISSIONS)
    return headers, tenant.id


async def _create_supplier(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": f"OUTSUP-{uuid.uuid4().hex[:8]}",
        "name": f"Outstanding Supplier {uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/suppliers", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _get_supplier(
    client: AsyncClient, headers: dict[str, str], supplier_id: str
) -> dict[str, Any]:
    response = await client.get(f"/api/v1/suppliers/{supplier_id}", headers=headers)
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_supplier_payment(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    supplier_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "supplier_id": supplier_id,
        "payment_date": _PAYMENT_DATE,
        "payment_method": "cheque",
        "amount": "1000.00",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/supplier-payments", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_purchase_bill(
    client: AsyncClient, headers: dict[str, str], *, supplier_id: str, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"supplier_id": supplier_id, "bill_date": _BILL_DATE}
    payload.update(overrides)
    response = await client.post("/api/v1/purchase", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _add_purchase_bill_item(
    client: AsyncClient, headers: dict[str, str], purchase_bill_id: str, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "description": "Pomfret - Grade A",
        "quantity": "10.000",
        "unit": "KG",
        "rate": "100.0000",
    }
    payload.update(overrides)
    response = await client.post(
        f"/api/v1/purchase/{purchase_bill_id}/items", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _get_purchase_bill(
    client: AsyncClient, headers: dict[str, str], purchase_bill_id: str
) -> dict[str, Any]:
    response = await client.get(f"/api/v1/purchase/{purchase_bill_id}", headers=headers)
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_posted_purchase_bill(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    supplier_id: str,
    quantity: str = "10.000",
    rate: str = "100.0000",
) -> dict[str, Any]:
    """A fully posted purchase bill with a known balance_amount (quantity x
    rate, no tax/discount) - the default 10 x 100 = 1000.00 matches
    _create_supplier_payment's default amount."""
    bill = await _create_purchase_bill(client, headers, supplier_id=supplier_id)
    await _add_purchase_bill_item(client, headers, bill["id"], quantity=quantity, rate=rate)
    posted = await client.post(f"/api/v1/purchase/{bill['id']}/post", headers=headers)
    assert posted.status_code == 200, posted.text
    result: dict[str, Any] = posted.json()
    return result


async def _create_allocation(
    client: AsyncClient,
    headers: dict[str, str],
    supplier_payment_id: str,
    purchase_bill_id: str,
    allocated_amount: str,
) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/supplier-payments/{supplier_payment_id}/allocations",
        json={"purchase_bill_id": purchase_bill_id, "allocated_amount": allocated_amount},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


class TestPurchaseBillStatusTransitions:
    """POSTED -> PARTIALLY_PAID -> PAID -> back down, driven purely by
    allocation create/update/delete (TASKS.md Sprint 12 Session 4)."""

    async def test_partial_allocation_moves_posted_to_partially_paid(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(db_session, name_hint="Status Partial Tenant")
        supplier = await _create_supplier(client, headers)
        bill = await _create_posted_purchase_bill(client, headers, supplier_id=supplier["id"])
        payment = await _create_supplier_payment(client, headers, supplier_id=supplier["id"])

        await _create_allocation(client, headers, payment["id"], bill["id"], "400.00")

        after = await _get_purchase_bill(client, headers, bill["id"])
        assert after["status"] == "partially_paid"
        assert after["paid_amount"] == "400.00"
        assert after["balance_amount"] == "600.00"

    async def test_full_allocation_moves_to_paid(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(db_session, name_hint="Status Full Tenant")
        supplier = await _create_supplier(client, headers)
        bill = await _create_posted_purchase_bill(client, headers, supplier_id=supplier["id"])
        payment = await _create_supplier_payment(client, headers, supplier_id=supplier["id"])

        await _create_allocation(client, headers, payment["id"], bill["id"], "1000.00")

        after = await _get_purchase_bill(client, headers, bill["id"])
        assert after["status"] == "paid"
        assert after["paid_amount"] == "1000.00"
        assert after["balance_amount"] == "0.00"

    async def test_two_partial_allocations_from_different_payments_reach_paid(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(db_session, name_hint="Status Multi Payment Tenant")
        supplier = await _create_supplier(client, headers)
        bill = await _create_posted_purchase_bill(client, headers, supplier_id=supplier["id"])
        payment_a = await _create_supplier_payment(
            client, headers, supplier_id=supplier["id"], amount="600.00"
        )
        payment_b = await _create_supplier_payment(
            client, headers, supplier_id=supplier["id"], amount="400.00"
        )

        await _create_allocation(client, headers, payment_a["id"], bill["id"], "600.00")
        mid = await _get_purchase_bill(client, headers, bill["id"])
        assert mid["status"] == "partially_paid"

        await _create_allocation(client, headers, payment_b["id"], bill["id"], "400.00")
        after = await _get_purchase_bill(client, headers, bill["id"])
        assert after["status"] == "paid"
        assert after["balance_amount"] == "0.00"

    async def test_updating_allocation_amount_up_moves_partially_paid_to_paid(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(db_session, name_hint="Status Update Up Tenant")
        supplier = await _create_supplier(client, headers)
        bill = await _create_posted_purchase_bill(client, headers, supplier_id=supplier["id"])
        payment = await _create_supplier_payment(client, headers, supplier_id=supplier["id"])
        allocation = await _create_allocation(client, headers, payment["id"], bill["id"], "400.00")

        response = await client.put(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            json={"allocated_amount": "1000.00"},
            headers=headers,
        )
        assert response.status_code == 200, response.text

        after = await _get_purchase_bill(client, headers, bill["id"])
        assert after["status"] == "paid"
        assert after["balance_amount"] == "0.00"

    async def test_updating_allocation_amount_down_on_a_paid_bill_moves_back_to_partially_paid(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The edge case that motivated allow_paid on
        _ensure_purchase_bill_allocatable: the bill is PAID *because of*
        this allocation, and reducing it must still be permitted."""
        headers, _ = await _make_tenant_headers(db_session, name_hint="Status Update Down Tenant")
        supplier = await _create_supplier(client, headers)
        bill = await _create_posted_purchase_bill(client, headers, supplier_id=supplier["id"])
        payment = await _create_supplier_payment(client, headers, supplier_id=supplier["id"])
        allocation = await _create_allocation(client, headers, payment["id"], bill["id"], "1000.00")
        mid = await _get_purchase_bill(client, headers, bill["id"])
        assert mid["status"] == "paid"

        response = await client.put(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            json={"allocated_amount": "300.00"},
            headers=headers,
        )
        assert response.status_code == 200, response.text

        after = await _get_purchase_bill(client, headers, bill["id"])
        assert after["status"] == "partially_paid"
        assert after["paid_amount"] == "300.00"
        assert after["balance_amount"] == "700.00"

    async def test_deleting_the_only_allocation_moves_paid_back_to_posted(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(db_session, name_hint="Status Delete Tenant")
        supplier = await _create_supplier(client, headers)
        bill = await _create_posted_purchase_bill(client, headers, supplier_id=supplier["id"])
        payment = await _create_supplier_payment(client, headers, supplier_id=supplier["id"])
        allocation = await _create_allocation(client, headers, payment["id"], bill["id"], "1000.00")
        mid = await _get_purchase_bill(client, headers, bill["id"])
        assert mid["status"] == "paid"

        response = await client.delete(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            headers=headers,
        )
        assert response.status_code == 204, response.text

        after = await _get_purchase_bill(client, headers, bill["id"])
        assert after["status"] == "posted"
        assert after["paid_amount"] == "0.00"
        assert after["balance_amount"] == "1000.00"

    async def test_deleting_one_of_two_allocations_moves_paid_to_partially_paid(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(
            db_session, name_hint="Status Delete Partial Tenant"
        )
        supplier = await _create_supplier(client, headers)
        bill = await _create_posted_purchase_bill(client, headers, supplier_id=supplier["id"])
        payment_a = await _create_supplier_payment(
            client, headers, supplier_id=supplier["id"], amount="600.00"
        )
        payment_b = await _create_supplier_payment(
            client, headers, supplier_id=supplier["id"], amount="400.00"
        )
        await _create_allocation(client, headers, payment_a["id"], bill["id"], "600.00")
        allocation_b = await _create_allocation(
            client, headers, payment_b["id"], bill["id"], "400.00"
        )
        mid = await _get_purchase_bill(client, headers, bill["id"])
        assert mid["status"] == "paid"

        response = await client.delete(
            f"/api/v1/supplier-payments/{payment_b['id']}/allocations/{allocation_b['id']}",
            headers=headers,
        )
        assert response.status_code == 204, response.text

        after = await _get_purchase_bill(client, headers, bill["id"])
        assert after["status"] == "partially_paid"
        assert after["paid_amount"] == "600.00"
        assert after["balance_amount"] == "400.00"

    async def test_reassigning_a_paid_allocation_to_a_different_bill_recalculates_both(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(db_session, name_hint="Status Reassign Tenant")
        supplier = await _create_supplier(client, headers)
        bill_a = await _create_posted_purchase_bill(client, headers, supplier_id=supplier["id"])
        bill_b = await _create_posted_purchase_bill(client, headers, supplier_id=supplier["id"])
        payment = await _create_supplier_payment(client, headers, supplier_id=supplier["id"])
        allocation = await _create_allocation(
            client, headers, payment["id"], bill_a["id"], "1000.00"
        )
        mid = await _get_purchase_bill(client, headers, bill_a["id"])
        assert mid["status"] == "paid"

        response = await client.put(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            json={"purchase_bill_id": bill_b["id"]},
            headers=headers,
        )
        assert response.status_code == 200, response.text

        a_after = await _get_purchase_bill(client, headers, bill_a["id"])
        b_after = await _get_purchase_bill(client, headers, bill_b["id"])
        assert a_after["status"] == "posted"
        assert a_after["balance_amount"] == "1000.00"
        assert b_after["status"] == "paid"
        assert b_after["balance_amount"] == "0.00"


class TestSupplierOutstandingAmount:
    """Supplier.outstanding_amount recomputed from the sum of every open
    purchase bill's balance_amount - never incremented (TASKS.md)."""

    async def test_zero_after_full_allocation(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(db_session, name_hint="Outstanding Zero Tenant")
        supplier = await _create_supplier(client, headers)
        bill = await _create_posted_purchase_bill(client, headers, supplier_id=supplier["id"])
        after_post = await _get_supplier(client, headers, supplier["id"])
        assert after_post["outstanding_amount"] == "1000.00"

        payment = await _create_supplier_payment(client, headers, supplier_id=supplier["id"])
        await _create_allocation(client, headers, payment["id"], bill["id"], "1000.00")

        after_allocation = await _get_supplier(client, headers, supplier["id"])
        assert after_allocation["outstanding_amount"] == "0.00"

    async def test_reflects_partial_payment(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(db_session, name_hint="Outstanding Partial Tenant")
        supplier = await _create_supplier(client, headers)
        bill = await _create_posted_purchase_bill(client, headers, supplier_id=supplier["id"])
        payment = await _create_supplier_payment(client, headers, supplier_id=supplier["id"])

        await _create_allocation(client, headers, payment["id"], bill["id"], "400.00")

        after = await _get_supplier(client, headers, supplier["id"])
        assert after["outstanding_amount"] == "600.00"

    async def test_sums_multiple_open_purchase_bills_for_the_same_supplier(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(
            db_session, name_hint="Outstanding Multi Bill Tenant"
        )
        supplier = await _create_supplier(client, headers)
        bill_a = await _create_posted_purchase_bill(client, headers, supplier_id=supplier["id"])
        bill_b = await _create_posted_purchase_bill(client, headers, supplier_id=supplier["id"])
        # 2000.00 total outstanding after both are posted.
        payment = await _create_supplier_payment(
            client, headers, supplier_id=supplier["id"], amount="300.00"
        )

        await _create_allocation(client, headers, payment["id"], bill_a["id"], "300.00")

        after = await _get_supplier(client, headers, supplier["id"])
        # bill_a: 1000 - 300 = 700 open; bill_b: 1000 untouched -> 1700
        assert after["outstanding_amount"] == "1700.00"
        assert (await _get_purchase_bill(client, headers, bill_b["id"]))["status"] == "posted"

    async def test_restored_after_allocation_is_deleted(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(db_session, name_hint="Outstanding Restore Tenant")
        supplier = await _create_supplier(client, headers)
        bill = await _create_posted_purchase_bill(client, headers, supplier_id=supplier["id"])
        payment = await _create_supplier_payment(client, headers, supplier_id=supplier["id"])
        allocation = await _create_allocation(client, headers, payment["id"], bill["id"], "1000.00")
        assert (await _get_supplier(client, headers, supplier["id"]))[
            "outstanding_amount"
        ] == "0.00"

        response = await client.delete(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            headers=headers,
        )
        assert response.status_code == 204, response.text

        after = await _get_supplier(client, headers, supplier["id"])
        assert after["outstanding_amount"] == "1000.00"

    async def test_two_suppliers_are_recalculated_independently(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(
            db_session, name_hint="Outstanding Two Supplier Tenant"
        )
        supplier_a = await _create_supplier(client, headers)
        supplier_b = await _create_supplier(client, headers)
        bill_a = await _create_posted_purchase_bill(client, headers, supplier_id=supplier_a["id"])
        await _create_posted_purchase_bill(client, headers, supplier_id=supplier_b["id"])
        payment_a = await _create_supplier_payment(client, headers, supplier_id=supplier_a["id"])

        await _create_allocation(client, headers, payment_a["id"], bill_a["id"], "1000.00")

        after_a = await _get_supplier(client, headers, supplier_a["id"])
        after_b = await _get_supplier(client, headers, supplier_b["id"])
        assert after_a["outstanding_amount"] == "0.00"
        assert after_b["outstanding_amount"] == "1000.00"  # untouched


class TestOutstandingEngineTenantIsolation:
    async def test_allocation_in_one_tenant_never_affects_anothers_bill_or_supplier(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers_a, _ = await _make_tenant_headers(db_session, name_hint="Isolation Tenant A")
        headers_b, _ = await _make_tenant_headers(db_session, name_hint="Isolation Tenant B")

        supplier_a = await _create_supplier(client, headers_a)
        bill_a = await _create_posted_purchase_bill(client, headers_a, supplier_id=supplier_a["id"])
        payment_a = await _create_supplier_payment(client, headers_a, supplier_id=supplier_a["id"])

        supplier_b = await _create_supplier(client, headers_b)
        bill_b = await _create_posted_purchase_bill(client, headers_b, supplier_id=supplier_b["id"])

        await _create_allocation(client, headers_a, payment_a["id"], bill_a["id"], "1000.00")

        # Tenant B's purchase bill/supplier are completely untouched by
        # tenant A's allocation.
        b_bill_after = await _get_purchase_bill(client, headers_b, bill_b["id"])
        b_supplier_after = await _get_supplier(client, headers_b, supplier_b["id"])
        assert b_bill_after["status"] == "posted"
        assert b_bill_after["balance_amount"] == "1000.00"
        assert b_supplier_after["outstanding_amount"] == "1000.00"
