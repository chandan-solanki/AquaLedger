"""Integration tests for the Delivery Challan <-> Invoice relationship
(Sprint 12 Session 14): the required invoice_id/invoice_item_id links,
multi-challan partial delivery, over-delivery rejection, and the hard
financial-isolation invariant - a delivery challan must never touch
Invoice.total_amount/paid_amount/balance_amount or
Company.outstanding_amount at any lifecycle stage. Mirrors
test_purchase_order_purchase_bill_linkage_api.py's helper style and its
TestFinancialInvariants section.
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
from app.modules.companies.models import Company
from app.modules.invoices.models import Invoice

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

_ALL_PERMISSIONS = [
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
        "code": f"LNKCO-{uuid.uuid4().hex[:8]}",
        "name": f"Linkage Owner {uuid.uuid4().hex[:8]}",
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
        "code": f"LNKFISH-{uuid.uuid4().hex[:8]}",
        "name": f"Linkage Fish {uuid.uuid4().hex[:8]}",
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
        "code": f"LNKB-{uuid.uuid4().hex[:8]}",
        "name": f"Linkage Boat {uuid.uuid4().hex[:8]}",
        "registration_number": f"LNKREG-{uuid.uuid4().hex[:8]}",
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
        "trip_number": f"LNKTRIP-{uuid.uuid4().hex[:8]}",
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
    client: AsyncClient, headers: dict[str, str], *, company_id: str, **overrides: Any
) -> dict[str, Any]:
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
        "rate": "200.0000",
    }
    payload.update(overrides)
    response = await client.post(
        f"/api/v1/invoices/{invoice_id}/items", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _issued_invoice_with_item(
    client: AsyncClient, headers: dict[str, str], *, company_id: str, **item_overrides: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    invoice = await _create_invoice(client, headers, company_id=company_id)
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
    return await client.post(
        f"/api/v1/delivery-challans/{delivery_challan_id}/items", json=overrides, headers=headers
    )


async def _read_invoice(db_session: AsyncSession, invoice_id: str) -> Invoice:
    return (
        await db_session.execute(select(Invoice).where(Invoice.id == uuid.UUID(invoice_id)))
    ).scalar_one()


async def _read_company(db_session: AsyncSession, company_id: str) -> Company:
    return (
        await db_session.execute(select(Company).where(Company.id == uuid.UUID(company_id)))
    ).scalar_one()


class TestHeaderLinkValidation:
    async def test_rejects_linking_a_draft_invoice(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        draft_invoice = await _create_invoice(client, headers, company_id=company["id"])

        response = await client.post(
            "/api/v1/delivery-challans",
            json={"invoice_id": draft_invoice["id"], "challan_date": _CHALLAN_DATE},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_INVOICE_NOT_DELIVERABLE"

    async def test_accepts_linking_an_issued_invoice(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        invoice, _ = await _issued_invoice_with_item(client, headers, company_id=company["id"])

        response = await client.post(
            "/api/v1/delivery-challans",
            json={"invoice_id": invoice["id"], "challan_date": _CHALLAN_DATE},
            headers=headers,
        )
        assert response.status_code == 201, response.text

    async def test_rejects_linking_an_unknown_invoice(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/delivery-challans",
            json={"invoice_id": str(uuid.uuid4()), "challan_date": _CHALLAN_DATE},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_INVOICE_NOT_FOUND"

    async def test_rejects_linking_an_invoice_from_another_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Other Linkage Invoice Tenant",
            slug=f"other-linkage-inv-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_PERMISSIONS)
        other_company = await _create_company(client, other_headers)
        other_invoice, _ = await _issued_invoice_with_item(
            client, other_headers, company_id=other_company["id"]
        )

        admin_headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/delivery-challans",
            json={"invoice_id": other_invoice["id"], "challan_date": _CHALLAN_DATE},
            headers=admin_headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_INVOICE_NOT_FOUND"


class TestPartialDeliveryAndOverDelivery:
    """Multiple delivery challans against one invoice item, cumulative
    remaining tracking, and hard over-delivery rejection - the exact
    scenario from TASKS.md Phase 18's real-data verification script."""

    async def test_full_partial_delivery_sequence_across_three_separate_challans(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        invoice, item = await _issued_invoice_with_item(
            client, headers, company_id=company["id"], quantity="100.000", rate="200.0000"
        )

        # Challan #1: 40 KG -> remaining 60.
        challan_1 = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        response_1 = await _add_challan_item(
            client, headers, challan_1["id"], invoice_item_id=item["id"], quantity="40.000"
        )
        assert response_1.status_code == 201, response_1.text

        # Challan #2: 30 KG more -> remaining 30.
        challan_2 = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        response_2 = await _add_challan_item(
            client, headers, challan_2["id"], invoice_item_id=item["id"], quantity="30.000"
        )
        assert response_2.status_code == 201, response_2.text

        # Challan #3: 31 KG more -> exceeds the 30 KG remaining, rejected.
        challan_3 = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        response_3 = await _add_challan_item(
            client, headers, challan_3["id"], invoice_item_id=item["id"], quantity="31.000"
        )
        assert response_3.status_code == 422
        assert response_3.json()["error"]["code"] == "DELIVERY_CHALLAN_OVER_DELIVERY"

        # But exactly 30 KG (the true remaining) succeeds.
        response_3b = await _add_challan_item(
            client, headers, challan_3["id"], invoice_item_id=item["id"], quantity="30.000"
        )
        assert response_3b.status_code == 201, response_3b.text

        # Now fully delivered - one more KG anywhere is rejected.
        challan_4 = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        response_4 = await _add_challan_item(
            client, headers, challan_4["id"], invoice_item_id=item["id"], quantity="1.000"
        )
        assert response_4.status_code == 422
        assert response_4.json()["error"]["code"] == "DELIVERY_CHALLAN_OVER_DELIVERY"

    async def test_single_challan_over_delivery_in_one_shot_is_rejected(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        invoice, item = await _issued_invoice_with_item(
            client, headers, company_id=company["id"], quantity="100.000"
        )
        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])

        response = await _add_challan_item(
            client, headers, challan["id"], invoice_item_id=item["id"], quantity="150.000"
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_OVER_DELIVERY"

    async def test_cancelling_a_challan_frees_its_reserved_quantity(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        invoice, item = await _issued_invoice_with_item(
            client, headers, company_id=company["id"], quantity="100.000"
        )
        challan_1 = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        await _add_challan_item(
            client, headers, challan_1["id"], invoice_item_id=item["id"], quantity="90.000"
        )

        challan_2 = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        blocked = await _add_challan_item(
            client, headers, challan_2["id"], invoice_item_id=item["id"], quantity="50.000"
        )
        assert blocked.status_code == 422

        cancel_response = await client.post(
            f"/api/v1/delivery-challans/{challan_1['id']}/cancel", headers=headers
        )
        assert cancel_response.status_code == 200, cancel_response.text

        now_succeeds = await _add_challan_item(
            client, headers, challan_2["id"], invoice_item_id=item["id"], quantity="50.000"
        )
        assert now_succeeds.status_code == 201, now_succeeds.text


class TestFinancialInvariants:
    """The brief's own hard invariant: a delivery challan never owns any
    financial figure, at any lifecycle stage. Only Invoice.issue() (already
    happened before any challan exists) and Payment allocation ever change
    Invoice.paid_amount/balance_amount or Company.outstanding_amount."""

    async def test_full_lifecycle_never_touches_invoice_or_company_financials(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        invoice, item = await _issued_invoice_with_item(
            client, headers, company_id=company["id"], quantity="100.000", rate="200.0000"
        )

        invoice_before = await _read_invoice(db_session, invoice["id"])
        company_before = await _read_company(db_session, company["id"])
        total_amount = invoice_before.total_amount
        paid_amount = invoice_before.paid_amount
        balance_amount = invoice_before.balance_amount
        outstanding = company_before.outstanding_amount

        # Draft creation.
        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        await db_session.refresh(invoice_before)
        await db_session.refresh(company_before)
        assert invoice_before.total_amount == total_amount
        assert invoice_before.paid_amount == paid_amount
        assert invoice_before.balance_amount == balance_amount
        assert company_before.outstanding_amount == outstanding

        # Item add.
        add_response = await _add_challan_item(
            client, headers, challan["id"], invoice_item_id=item["id"], quantity="40.000"
        )
        assert add_response.status_code == 201, add_response.text
        await db_session.refresh(invoice_before)
        await db_session.refresh(company_before)
        assert invoice_before.total_amount == total_amount
        assert invoice_before.paid_amount == paid_amount
        assert invoice_before.balance_amount == balance_amount
        assert company_before.outstanding_amount == outstanding

        # Dispatch.
        dispatch_response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/dispatch", headers=headers
        )
        assert dispatch_response.status_code == 200, dispatch_response.text
        await db_session.refresh(invoice_before)
        await db_session.refresh(company_before)
        assert invoice_before.total_amount == total_amount
        assert invoice_before.paid_amount == paid_amount
        assert invoice_before.balance_amount == balance_amount
        assert company_before.outstanding_amount == outstanding

        # Deliver.
        deliver_response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/deliver", headers=headers
        )
        assert deliver_response.status_code == 200, deliver_response.text
        await db_session.refresh(invoice_before)
        await db_session.refresh(company_before)
        assert invoice_before.total_amount == total_amount
        assert invoice_before.paid_amount == paid_amount
        assert invoice_before.balance_amount == balance_amount
        assert company_before.outstanding_amount == outstanding

    async def test_cancel_never_touches_invoice_or_company_financials(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        invoice, _ = await _issued_invoice_with_item(
            client, headers, company_id=company["id"], quantity="100.000"
        )
        invoice_row = await _read_invoice(db_session, invoice["id"])
        company_row = await _read_company(db_session, company["id"])
        balance_before = invoice_row.balance_amount
        outstanding_before = company_row.outstanding_amount

        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        cancel_response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/cancel", headers=headers
        )
        assert cancel_response.status_code == 200, cancel_response.text

        await db_session.refresh(invoice_row)
        await db_session.refresh(company_row)
        assert invoice_row.balance_amount == balance_before
        assert company_row.outstanding_amount == outstanding_before

    async def test_outstanding_amount_is_driven_only_by_invoice_issue_never_by_delivery(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Sanity check that this test suite's own baseline assumption
        holds: issuing the invoice (before any challan exists) is what
        establishes outstanding_amount, and it stays exactly that value
        throughout every delivery challan operation - never zero-drifted,
        never re-derived from delivery activity."""
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        invoice, item = await _issued_invoice_with_item(
            client, headers, company_id=company["id"], quantity="100.000", rate="200.0000"
        )
        company_row = await _read_company(db_session, company["id"])
        assert company_row.outstanding_amount == Decimal("20000.00")

        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        await _add_challan_item(
            client, headers, challan["id"], invoice_item_id=item["id"], quantity="100.000"
        )
        await client.post(f"/api/v1/delivery-challans/{challan['id']}/dispatch", headers=headers)
        await client.post(f"/api/v1/delivery-challans/{challan['id']}/deliver", headers=headers)

        await db_session.refresh(company_row)
        assert company_row.outstanding_amount == Decimal("20000.00")
