import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

# _create_issued_invoice provisions a fresh company/trip catch (and that
# trip catch's fish, trip, boat) chain and issues the resulting invoice via
# the API, so these outstanding-engine tests need the full chain's access.
_ALL_OUTSTANDING_PERMISSIONS = [
    "payment:view",
    "payment:create",
    "payment:edit",
    "payment:delete",
    "company:view",
    "company:create",
    "company:edit",
    "invoice:view",
    "invoice:create",
    "invoice:edit",
    "invoice:issue",
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
_PAYMENT_DATE = "2026-07-23"
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
    touches companies, invoices and payments together, so a dedicated
    tenant per test keeps company.outstanding_amount assertions from being
    polluted by other tests' data."""
    tenant = Tenant(
        name=name_hint, slug=f"{name_hint.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
    )
    db_session.add(tenant)
    await db_session.commit()
    headers = await _make_user_headers(db_session, tenant.id, _ALL_OUTSTANDING_PERMISSIONS)
    return headers, tenant.id


async def _create_company(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": f"OUTCO-{uuid.uuid4().hex[:8]}",
        "name": f"Outstanding Owner {uuid.uuid4().hex[:8]}",
        "company_type": "customer",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/companies", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _get_company(
    client: AsyncClient, headers: dict[str, str], company_id: str
) -> dict[str, Any]:
    response = await client.get(f"/api/v1/companies/{company_id}", headers=headers)
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_payment(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    company_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "company_id": company_id,
        "payment_date": _PAYMENT_DATE,
        "payment_method": "cheque",
        "amount": "1000.00",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/payments", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_draft_invoice(
    client: AsyncClient, headers: dict[str, str], *, company_id: str, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"company_id": company_id, "invoice_date": _INVOICE_DATE}
    payload.update(overrides)
    response = await client.post("/api/v1/invoices", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _get_invoice(
    client: AsyncClient, headers: dict[str, str], invoice_id: str
) -> dict[str, Any]:
    response = await client.get(f"/api/v1/invoices/{invoice_id}", headers=headers)
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_fish(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": f"OUTFISH-{uuid.uuid4().hex[:8]}",
        "name": f"Outstanding Fish {uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/fish", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_boat(
    client: AsyncClient, headers: dict[str, str], *, company_id: str, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "company_id": company_id,
        "code": f"OUTB-{uuid.uuid4().hex[:8]}",
        "name": f"Outstanding Boat {uuid.uuid4().hex[:8]}",
        "registration_number": f"OUTREG-{uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/boats", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_returned_trip(
    client: AsyncClient, headers: dict[str, str], *, company_id: str, **overrides: Any
) -> dict[str, Any]:
    boat_id = (await _create_boat(client, headers, company_id=company_id))["id"]
    payload: dict[str, Any] = {
        "boat_id": boat_id,
        "trip_number": f"OUTTRIP-{uuid.uuid4().hex[:8]}",
        "trip_type": "fishing",
        "departure_datetime": _DEPARTURE,
    }
    payload.update(overrides)
    response = await client.post("/api/v1/trips", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    trip = response.json()
    returned = await client.put(
        f"/api/v1/trips/{trip['id']}",
        json={"status": "returned", "actual_return_datetime": _RETURN},
        headers=headers,
    )
    assert returned.status_code == 200, returned.text
    result: dict[str, Any] = returned.json()
    return result


async def _create_trip_catch(
    client: AsyncClient, headers: dict[str, str], *, company_id: str, **overrides: Any
) -> dict[str, Any]:
    trip_id = (await _create_returned_trip(client, headers, company_id=company_id))["id"]
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


async def _create_issued_invoice(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    company_id: str,
    quantity: str = "10.000",
    rate: str = "100.0000",
) -> dict[str, Any]:
    """A fully issued invoice with a known balance_amount (quantity x rate,
    no tax/discount) - the default 10 x 100 = 1000.00 matches
    _create_payment's default amount."""
    invoice = await _create_draft_invoice(client, headers, company_id=company_id)
    trip_catch = await _create_trip_catch(client, headers, company_id=company_id)
    item_response = await client.post(
        f"/api/v1/invoices/{invoice['id']}/items",
        json={
            "trip_catch_id": trip_catch["id"],
            "fish_id": trip_catch["fish_id"],
            "quantity": quantity,
            "unit": "kg",
            "rate": rate,
        },
        headers=headers,
    )
    assert item_response.status_code == 201, item_response.text
    issued = await client.post(f"/api/v1/invoices/{invoice['id']}/issue", headers=headers)
    assert issued.status_code == 200, issued.text
    result: dict[str, Any] = issued.json()
    return result


async def _create_allocation(
    client: AsyncClient,
    headers: dict[str, str],
    payment_id: str,
    invoice_id: str,
    allocated_amount: str,
) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/payments/{payment_id}/allocations",
        json={"invoice_id": invoice_id, "allocated_amount": allocated_amount},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


class TestInvoiceStatusTransitions:
    """ISSUED -> PARTIALLY_PAID -> PAID -> back down, driven purely by
    allocation create/update/delete (TASKS.md Sprint 10 Session 4)."""

    async def test_partial_allocation_moves_issued_to_partially_paid(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(db_session, name_hint="Status Partial Tenant")
        company = await _create_company(client, headers)
        invoice = await _create_issued_invoice(client, headers, company_id=company["id"])
        payment = await _create_payment(client, headers, company_id=company["id"])

        await _create_allocation(client, headers, payment["id"], invoice["id"], "400.00")

        after = await _get_invoice(client, headers, invoice["id"])
        assert after["status"] == "partially_paid"
        assert after["paid_amount"] == "400.00"
        assert after["balance_amount"] == "600.00"

    async def test_full_allocation_moves_to_paid(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(db_session, name_hint="Status Full Tenant")
        company = await _create_company(client, headers)
        invoice = await _create_issued_invoice(client, headers, company_id=company["id"])
        payment = await _create_payment(client, headers, company_id=company["id"])

        await _create_allocation(client, headers, payment["id"], invoice["id"], "1000.00")

        after = await _get_invoice(client, headers, invoice["id"])
        assert after["status"] == "paid"
        assert after["paid_amount"] == "1000.00"
        assert after["balance_amount"] == "0.00"

    async def test_two_partial_allocations_from_different_payments_reach_paid(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(db_session, name_hint="Status Multi Payment Tenant")
        company = await _create_company(client, headers)
        invoice = await _create_issued_invoice(client, headers, company_id=company["id"])
        payment_a = await _create_payment(
            client, headers, company_id=company["id"], amount="600.00"
        )
        payment_b = await _create_payment(
            client, headers, company_id=company["id"], amount="400.00"
        )

        await _create_allocation(client, headers, payment_a["id"], invoice["id"], "600.00")
        mid = await _get_invoice(client, headers, invoice["id"])
        assert mid["status"] == "partially_paid"

        await _create_allocation(client, headers, payment_b["id"], invoice["id"], "400.00")
        after = await _get_invoice(client, headers, invoice["id"])
        assert after["status"] == "paid"
        assert after["balance_amount"] == "0.00"

    async def test_updating_allocation_amount_up_moves_partially_paid_to_paid(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(db_session, name_hint="Status Update Up Tenant")
        company = await _create_company(client, headers)
        invoice = await _create_issued_invoice(client, headers, company_id=company["id"])
        payment = await _create_payment(client, headers, company_id=company["id"])
        allocation = await _create_allocation(
            client, headers, payment["id"], invoice["id"], "400.00"
        )

        response = await client.put(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}",
            json={"allocated_amount": "1000.00"},
            headers=headers,
        )
        assert response.status_code == 200, response.text

        after = await _get_invoice(client, headers, invoice["id"])
        assert after["status"] == "paid"
        assert after["balance_amount"] == "0.00"

    async def test_updating_allocation_amount_down_on_a_paid_invoice_moves_back_to_partially_paid(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The edge case that motivated allow_paid on _ensure_invoice_allocatable:
        the invoice is PAID *because of* this allocation, and reducing it
        must still be permitted."""
        headers, _ = await _make_tenant_headers(db_session, name_hint="Status Update Down Tenant")
        company = await _create_company(client, headers)
        invoice = await _create_issued_invoice(client, headers, company_id=company["id"])
        payment = await _create_payment(client, headers, company_id=company["id"])
        allocation = await _create_allocation(
            client, headers, payment["id"], invoice["id"], "1000.00"
        )
        mid = await _get_invoice(client, headers, invoice["id"])
        assert mid["status"] == "paid"

        response = await client.put(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}",
            json={"allocated_amount": "300.00"},
            headers=headers,
        )
        assert response.status_code == 200, response.text

        after = await _get_invoice(client, headers, invoice["id"])
        assert after["status"] == "partially_paid"
        assert after["paid_amount"] == "300.00"
        assert after["balance_amount"] == "700.00"

    async def test_deleting_the_only_allocation_moves_paid_back_to_issued(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(db_session, name_hint="Status Delete Tenant")
        company = await _create_company(client, headers)
        invoice = await _create_issued_invoice(client, headers, company_id=company["id"])
        payment = await _create_payment(client, headers, company_id=company["id"])
        allocation = await _create_allocation(
            client, headers, payment["id"], invoice["id"], "1000.00"
        )
        mid = await _get_invoice(client, headers, invoice["id"])
        assert mid["status"] == "paid"

        response = await client.delete(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}", headers=headers
        )
        assert response.status_code == 204, response.text

        after = await _get_invoice(client, headers, invoice["id"])
        assert after["status"] == "issued"
        assert after["paid_amount"] == "0.00"
        assert after["balance_amount"] == "1000.00"

    async def test_deleting_one_of_two_allocations_moves_paid_to_partially_paid(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(
            db_session, name_hint="Status Delete Partial Tenant"
        )
        company = await _create_company(client, headers)
        invoice = await _create_issued_invoice(client, headers, company_id=company["id"])
        payment_a = await _create_payment(
            client, headers, company_id=company["id"], amount="600.00"
        )
        payment_b = await _create_payment(
            client, headers, company_id=company["id"], amount="400.00"
        )
        await _create_allocation(client, headers, payment_a["id"], invoice["id"], "600.00")
        allocation_b = await _create_allocation(
            client, headers, payment_b["id"], invoice["id"], "400.00"
        )
        mid = await _get_invoice(client, headers, invoice["id"])
        assert mid["status"] == "paid"

        response = await client.delete(
            f"/api/v1/payments/{payment_b['id']}/allocations/{allocation_b['id']}", headers=headers
        )
        assert response.status_code == 204, response.text

        after = await _get_invoice(client, headers, invoice["id"])
        assert after["status"] == "partially_paid"
        assert after["paid_amount"] == "600.00"
        assert after["balance_amount"] == "400.00"

    async def test_reassigning_a_paid_allocation_to_a_different_invoice_recalculates_both(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(db_session, name_hint="Status Reassign Tenant")
        company = await _create_company(client, headers)
        invoice_a = await _create_issued_invoice(client, headers, company_id=company["id"])
        invoice_b = await _create_issued_invoice(client, headers, company_id=company["id"])
        payment = await _create_payment(client, headers, company_id=company["id"])
        allocation = await _create_allocation(
            client, headers, payment["id"], invoice_a["id"], "1000.00"
        )
        mid = await _get_invoice(client, headers, invoice_a["id"])
        assert mid["status"] == "paid"

        response = await client.put(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}",
            json={"invoice_id": invoice_b["id"]},
            headers=headers,
        )
        assert response.status_code == 200, response.text

        a_after = await _get_invoice(client, headers, invoice_a["id"])
        b_after = await _get_invoice(client, headers, invoice_b["id"])
        assert a_after["status"] == "issued"
        assert a_after["balance_amount"] == "1000.00"
        assert b_after["status"] == "paid"
        assert b_after["balance_amount"] == "0.00"


class TestCompanyOutstandingAmount:
    """Company.outstanding_amount recomputed from the sum of every open
    invoice's balance_amount - never incremented (TASKS.md)."""

    async def test_zero_after_full_allocation(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(db_session, name_hint="Outstanding Zero Tenant")
        company = await _create_company(client, headers)
        invoice = await _create_issued_invoice(client, headers, company_id=company["id"])
        after_issue = await _get_company(client, headers, company["id"])
        assert after_issue["outstanding_amount"] == "1000.00"

        payment = await _create_payment(client, headers, company_id=company["id"])
        await _create_allocation(client, headers, payment["id"], invoice["id"], "1000.00")

        after_allocation = await _get_company(client, headers, company["id"])
        assert after_allocation["outstanding_amount"] == "0.00"

    async def test_reflects_partial_payment(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(db_session, name_hint="Outstanding Partial Tenant")
        company = await _create_company(client, headers)
        invoice = await _create_issued_invoice(client, headers, company_id=company["id"])
        payment = await _create_payment(client, headers, company_id=company["id"])

        await _create_allocation(client, headers, payment["id"], invoice["id"], "400.00")

        after = await _get_company(client, headers, company["id"])
        assert after["outstanding_amount"] == "600.00"

    async def test_sums_multiple_open_invoices_for_the_same_company(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(
            db_session, name_hint="Outstanding Multi Invoice Tenant"
        )
        company = await _create_company(client, headers)
        invoice_a = await _create_issued_invoice(client, headers, company_id=company["id"])
        invoice_b = await _create_issued_invoice(client, headers, company_id=company["id"])
        # 2000.00 total outstanding after both are issued.
        payment = await _create_payment(client, headers, company_id=company["id"], amount="300.00")

        await _create_allocation(client, headers, payment["id"], invoice_a["id"], "300.00")

        after = await _get_company(client, headers, company["id"])
        # invoice_a: 1000 - 300 = 700 open; invoice_b: 1000 untouched -> 1700
        assert after["outstanding_amount"] == "1700.00"
        assert (await _get_invoice(client, headers, invoice_b["id"]))["status"] == "issued"

    async def test_restored_after_allocation_is_deleted(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(db_session, name_hint="Outstanding Restore Tenant")
        company = await _create_company(client, headers)
        invoice = await _create_issued_invoice(client, headers, company_id=company["id"])
        payment = await _create_payment(client, headers, company_id=company["id"])
        allocation = await _create_allocation(
            client, headers, payment["id"], invoice["id"], "1000.00"
        )
        assert (await _get_company(client, headers, company["id"]))["outstanding_amount"] == "0.00"

        response = await client.delete(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}", headers=headers
        )
        assert response.status_code == 204, response.text

        after = await _get_company(client, headers, company["id"])
        assert after["outstanding_amount"] == "1000.00"

    async def test_two_companies_are_recalculated_independently(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _ = await _make_tenant_headers(
            db_session, name_hint="Outstanding Two Company Tenant"
        )
        company_a = await _create_company(client, headers)
        company_b = await _create_company(client, headers)
        invoice_a = await _create_issued_invoice(client, headers, company_id=company_a["id"])
        await _create_issued_invoice(client, headers, company_id=company_b["id"])
        payment_a = await _create_payment(client, headers, company_id=company_a["id"])

        await _create_allocation(client, headers, payment_a["id"], invoice_a["id"], "1000.00")

        after_a = await _get_company(client, headers, company_a["id"])
        after_b = await _get_company(client, headers, company_b["id"])
        assert after_a["outstanding_amount"] == "0.00"
        assert after_b["outstanding_amount"] == "1000.00"  # untouched


class TestOutstandingEngineTenantIsolation:
    async def test_allocation_in_one_tenant_never_affects_anothers_invoice_or_company(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers_a, _ = await _make_tenant_headers(db_session, name_hint="Isolation Tenant A")
        headers_b, _ = await _make_tenant_headers(db_session, name_hint="Isolation Tenant B")

        company_a = await _create_company(client, headers_a)
        invoice_a = await _create_issued_invoice(client, headers_a, company_id=company_a["id"])
        payment_a = await _create_payment(client, headers_a, company_id=company_a["id"])

        company_b = await _create_company(client, headers_b)
        invoice_b = await _create_issued_invoice(client, headers_b, company_id=company_b["id"])

        await _create_allocation(client, headers_a, payment_a["id"], invoice_a["id"], "1000.00")

        # Tenant B's invoice/company are completely untouched by tenant A's allocation.
        b_invoice_after = await _get_invoice(client, headers_b, invoice_b["id"])
        b_company_after = await _get_company(client, headers_b, company_b["id"])
        assert b_invoice_after["status"] == "issued"
        assert b_invoice_after["balance_amount"] == "1000.00"
        assert b_company_after["outstanding_amount"] == "1000.00"
