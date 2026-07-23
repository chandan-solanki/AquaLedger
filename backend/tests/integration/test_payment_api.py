import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.models import Invoice
from app.modules.payments.constants import PaymentStatus
from app.modules.payments.models import Payment, PaymentAllocation

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

# _create_payment provisions a fresh company via the API by default, so test
# users need company:create access too for that setup to succeed.
_ALL_PAYMENT_PERMISSIONS = [
    "payment:view",
    "payment:create",
    "payment:edit",
    "payment:delete",
    "company:view",
    "company:create",
    "company:edit",
]
# _create_issued_invoice provisions a fresh trip catch (and that trip
# catch's fish, trip, boat) and issues the resulting invoice via the API, so
# allocation test users need the full chain's access for that setup to
# succeed too.
_ALL_ALLOCATION_PERMISSIONS = [
    *_ALL_PAYMENT_PERMISSIONS,
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
# Sprint 10 Session 5 - the posting workflow's own route-level permission,
# on top of everything allocation setup needs.
_ALL_POST_PERMISSIONS = [*_ALL_ALLOCATION_PERMISSIONS, "payment:post"]
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
        "code": f"PAYCO-{uuid.uuid4().hex[:8]}",
        "name": f"Payment Owner {uuid.uuid4().hex[:8]}",
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


async def _create_payment(
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


async def _create_fish(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": f"PALFISH-{uuid.uuid4().hex[:8]}",
        "name": f"Alloc Fish {uuid.uuid4().hex[:8]}",
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
        "code": f"PALB-{uuid.uuid4().hex[:8]}",
        "name": f"Alloc Boat {uuid.uuid4().hex[:8]}",
        "registration_number": f"PALREG-{uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/boats", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_returned_trip(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    boat_id = (await _create_boat(client, headers))["id"]
    payload: dict[str, Any] = {
        "boat_id": boat_id,
        "trip_number": f"PALTRIP-{uuid.uuid4().hex[:8]}",
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
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    trip_id = (await _create_returned_trip(client, headers))["id"]
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
    company_id: str | None = None,
    quantity: str = "10.000",
    rate: str = "100.0000",
) -> dict[str, Any]:
    """A fully issued invoice with a known balance_amount (quantity x rate,
    no tax/discount) - the default 10 x 100 = 1000.00 matches
    _create_payment's default amount, so tests can allocate the full amount
    without doing the arithmetic themselves."""
    invoice = await _create_draft_invoice(client, headers, company_id=company_id)
    trip_catch = await _create_trip_catch(client, headers)
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
    *,
    invoice_id: str | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    if invoice_id is None:
        invoice_id = (await _create_issued_invoice(client, headers))["id"]
    payload: dict[str, Any] = {"invoice_id": invoice_id, "allocated_amount": "100.00"}
    payload.update(overrides)
    response = await client.post(
        f"/api/v1/payments/{payment_id}/allocations", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


class TestCreatePayment:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/payments",
            json={
                "company_id": str(uuid.uuid4()),
                "payment_date": _PAYMENT_DATE,
                "payment_method": "cheque",
                "amount": "1000.00",
            },
        )
        assert response.status_code == 401

    async def test_requires_create_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["payment:view"])
        response = await client.post(
            "/api/v1/payments",
            json={
                "company_id": str(uuid.uuid4()),
                "payment_date": _PAYMENT_DATE,
                "payment_method": "cheque",
                "amount": "1000.00",
            },
            headers=headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_success_is_draft_with_server_owned_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        body = await _create_payment(
            client, headers, amount="200000.00", remarks="Against pending invoices"
        )

        assert body["status"] == "draft"
        assert body["payment_number"] is None
        assert body["amount"] == "200000.00"
        assert body["allocated_amount"] == "0.00"
        assert body["unallocated_amount"] == "200000.00"
        assert body["remarks"] == "Against pending invoices"
        assert body["created_at"] == body["updated_at"]

    async def test_success_sets_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        body = await _create_payment(client, headers)

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(select(Payment).where(Payment.id == uuid.UUID(body["id"])))
        ).scalar_one()
        assert row.created_by == admin.id
        assert row.updated_by == admin.id
        assert row.tenant_id == admin.tenant_id

    async def test_server_owned_fields_in_the_request_are_ignored(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        company_id = (await _create_company(client, headers))["id"]
        response = await client.post(
            "/api/v1/payments",
            json={
                "company_id": company_id,
                "payment_date": _PAYMENT_DATE,
                "payment_method": "cheque",
                "amount": "1000.00",
                "payment_number": "PAY-0001",
                "allocated_amount": "500.00",
                "unallocated_amount": "500.00",
                "status": "posted",
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["payment_number"] is None
        assert body["allocated_amount"] == "0.00"
        assert body["unallocated_amount"] == "1000.00"
        assert body["status"] == "draft"

    async def test_unknown_company_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/payments",
            json={
                "company_id": str(uuid.uuid4()),
                "payment_date": _PAYMENT_DATE,
                "payment_method": "cheque",
                "amount": "1000.00",
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_COMPANY_NOT_FOUND"

    async def test_inactive_company_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        await _update_company(client, headers, company["id"], status="inactive")

        response = await client.post(
            "/api/v1/payments",
            json={
                "company_id": company["id"],
                "payment_date": _PAYMENT_DATE,
                "payment_method": "cheque",
                "amount": "1000.00",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PAYMENT_COMPANY_INACTIVE"

    async def test_missing_company_id_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/payments",
            json={"payment_date": _PAYMENT_DATE, "payment_method": "cheque", "amount": "1000.00"},
            headers=headers,
        )
        assert response.status_code == 422
        assert "company_id" in response.json()["error"]["field_errors"]

    async def test_missing_amount_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        response = await client.post(
            "/api/v1/payments",
            json={
                "company_id": company["id"],
                "payment_date": _PAYMENT_DATE,
                "payment_method": "cheque",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "amount" in response.json()["error"]["field_errors"]

    async def test_zero_amount_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        response = await client.post(
            "/api/v1/payments",
            json={
                "company_id": company["id"],
                "payment_date": _PAYMENT_DATE,
                "payment_method": "cheque",
                "amount": "0",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "amount" in response.json()["error"]["field_errors"]

    async def test_invalid_payment_method_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        response = await client.post(
            "/api/v1/payments",
            json={
                "company_id": company["id"],
                "payment_date": _PAYMENT_DATE,
                "payment_method": "bitcoin",
                "amount": "1000.00",
            },
            headers=headers,
        )
        assert response.status_code == 422

    async def test_cannot_use_another_tenants_company(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)

        other_tenant = Tenant(
            name="Foreign Payment Company Owner", slug=f"foreign-pay-co-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_PAYMENT_PERMISSIONS
        )
        foreign_company = await _create_company(client, other_headers)

        response = await client.post(
            "/api/v1/payments",
            json={
                "company_id": foreign_company["id"],
                "payment_date": _PAYMENT_DATE,
                "payment_method": "cheque",
                "amount": "1000.00",
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_COMPANY_NOT_FOUND"


class TestGetPayment:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/payments/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(f"/api/v1/payments/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_returns_the_payment(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_payment(client, headers)
        response = await client.get(f"/api/v1/payments/{created['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(f"/api/v1/payments/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_NOT_FOUND"

    async def test_soft_deleted_payment_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_payment(client, headers)
        await client.delete(f"/api/v1/payments/{created['id']}", headers=headers)
        response = await client.get(f"/api/v1/payments/{created['id']}", headers=headers)
        assert response.status_code == 404

    async def test_other_tenants_payment_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_payment(client, headers)

        other_tenant = Tenant(name="Other Payment Co", slug=f"other-payment-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_PAYMENT_PERMISSIONS
        )

        response = await client.get(f"/api/v1/payments/{created['id']}", headers=other_headers)
        assert response.status_code == 404


class TestListPayments:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/payments")
        assert response.status_code == 401

    async def test_default_response_shape(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_payment(client, headers)
        response = await client.get("/api/v1/payments", headers=headers)
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

    async def test_search_matches_company_name(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Search Payment Company Tenant", slug=f"search-pay-co-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_PAYMENT_PERMISSIONS)

        marker = uuid.uuid4().hex[:8]
        matching_company = await _create_company(
            client, headers, name=f"Ocean Fresh Traders {marker}"
        )
        irrelevant_company = await _create_company(client, headers, name=f"Irrelevant Co {marker}")
        target = await _create_payment(client, headers, company_id=matching_company["id"])
        await _create_payment(client, headers, company_id=irrelevant_company["id"])

        response = await client.get(
            "/api/v1/payments", params={"q": f"ocean fresh traders {marker}"}, headers=headers
        )
        ids = [p["id"] for p in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_search_matches_reference_number(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Ref Search Payment Tenant", slug=f"ref-search-pay-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_PAYMENT_PERMISSIONS)

        marker = uuid.uuid4().hex[:8]
        target = await _create_payment(client, headers, reference_number=f"REF-{marker}")
        await _create_payment(client, headers, reference_number="REF-IRRELEVANT")

        response = await client.get(
            "/api/v1/payments", params={"q": f"ref-{marker}"}, headers=headers
        )
        ids = [p["id"] for p in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_filters_by_company_id(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Company Filter Payment Tenant", slug=f"company-filter-pay-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_PAYMENT_PERMISSIONS)

        company_a = await _create_company(client, headers)
        company_b = await _create_company(client, headers)
        target = await _create_payment(client, headers, company_id=company_a["id"])
        await _create_payment(client, headers, company_id=company_b["id"])

        response = await client.get(
            "/api/v1/payments", params={"company_id": company_a["id"]}, headers=headers
        )
        ids = [p["id"] for p in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_filters_by_payment_method(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Method Filter Payment Tenant", slug=f"method-filter-pay-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_PAYMENT_PERMISSIONS)

        target = await _create_payment(client, headers, payment_method="upi")
        await _create_payment(client, headers, payment_method="cash")

        response = await client.get(
            "/api/v1/payments", params={"payment_method": "upi"}, headers=headers
        )
        ids = [p["id"] for p in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_filters_by_status(self, client: AsyncClient, db_session: AsyncSession) -> None:
        other_tenant = Tenant(
            name="Status Filter Payment Tenant", slug=f"status-filter-pay-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_PAYMENT_PERMISSIONS)

        target = await _create_payment(client, headers)

        response = await client.get("/api/v1/payments", params={"status": "draft"}, headers=headers)
        ids = [p["id"] for p in response.json()["data"]]
        assert ids == [target["id"]]

        response_posted = await client.get(
            "/api/v1/payments", params={"status": "posted"}, headers=headers
        )
        assert response_posted.json()["data"] == []

    async def test_filters_by_payment_date_range(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Date Filter Payment Tenant", slug=f"date-filter-pay-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_PAYMENT_PERMISSIONS)

        in_range = await _create_payment(client, headers, payment_date="2026-06-05")
        await _create_payment(client, headers, payment_date="2099-01-01")

        response = await client.get(
            "/api/v1/payments",
            params={"payment_date_from": "2026-06-01", "payment_date_to": "2026-06-30"},
            headers=headers,
        )
        ids = [p["id"] for p in response.json()["data"]]
        assert ids == [in_range["id"]]

    async def test_sort_ascending_and_descending_by_amount(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Sort Amount Payment Tenant", slug=f"sort-amount-pay-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_PAYMENT_PERMISSIONS)

        company_id = (await _create_company(client, headers))["id"]
        smaller = await _create_payment(client, headers, company_id=company_id, amount="100.00")
        larger = await _create_payment(client, headers, company_id=company_id, amount="500.00")

        asc = await client.get("/api/v1/payments", params={"sort": "amount"}, headers=headers)
        assert [p["id"] for p in asc.json()["data"]] == [smaller["id"], larger["id"]]

        desc = await client.get("/api/v1/payments", params={"sort": "-amount"}, headers=headers)
        assert [p["id"] for p in desc.json()["data"]] == [larger["id"], smaller["id"]]

    async def test_invalid_sort_field_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/payments", params={"sort": "company_id"}, headers=headers
        )
        assert response.status_code == 422

    async def test_default_sort_is_most_recent_first(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Default Sort Payment Tenant", slug=f"default-sort-pay-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_PAYMENT_PERMISSIONS)

        first = await _create_payment(client, headers)
        second = await _create_payment(client, headers)

        response = await client.get("/api/v1/payments", headers=headers)
        ids = [p["id"] for p in response.json()["data"]]
        assert ids == [second["id"], first["id"]]

    async def test_pagination_meta_is_correct(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Pagination Payment Tenant", slug=f"pagination-pay-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_PAYMENT_PERMISSIONS)

        for _ in range(3):
            await _create_payment(client, headers)

        response = await client.get(
            "/api/v1/payments", params={"page": 1, "page_size": 2}, headers=headers
        )
        meta = response.json()["meta"]
        assert meta["total_records"] == 3
        assert meta["total_pages"] == 2
        assert meta["current_page"] == 1
        assert meta["page_size"] == 2
        assert meta["has_next"] is True
        assert meta["has_previous"] is False

        page2 = await client.get(
            "/api/v1/payments", params={"page": 2, "page_size": 2}, headers=headers
        )
        meta2 = page2.json()["meta"]
        assert meta2["has_next"] is False
        assert meta2["has_previous"] is True
        assert len(page2.json()["data"]) == 1

    async def test_invalid_page_size_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/payments", params={"page_size": 101}, headers=headers)
        assert response.status_code == 422

    async def test_deleted_payments_are_excluded(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Fresh List Payment Tenant", slug=f"fresh-pay-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        isolated_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_PAYMENT_PERMISSIONS
        )

        created = await _create_payment(client, isolated_headers)
        await client.delete(f"/api/v1/payments/{created['id']}", headers=isolated_headers)

        response = await client.get("/api/v1/payments", headers=isolated_headers)
        assert response.json()["data"] == []
        assert response.json()["meta"]["total_records"] == 0

    async def test_tenant_isolation_returns_only_own_payments(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        await _create_payment(client, headers)

        other_tenant = Tenant(
            name="Isolated Payment Co", slug=f"isolated-payment-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_PAYMENT_PERMISSIONS
        )

        response = await client.get("/api/v1/payments", headers=other_headers)
        assert response.json()["data"] == []


class TestUpdatePayment:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.put(f"/api/v1/payments/{uuid.uuid4()}", json={"remarks": "x"})
        assert response.status_code == 401

    async def test_requires_edit_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["payment:view"])
        response = await client.put(
            f"/api/v1/payments/{uuid.uuid4()}", json={"remarks": "x"}, headers=headers
        )
        assert response.status_code == 403

    async def test_partial_update_only_changes_supplied_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_payment(client, headers, remarks="Original", bank_name="Bank A")

        response = await client.put(
            f"/api/v1/payments/{created['id']}",
            json={"bank_name": "Bank B"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["bank_name"] == "Bank B"
        assert body["remarks"] == "Original"

    async def test_amount_change_recomputes_unallocated_amount(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_payment(client, headers, amount="1000.00")
        assert created["unallocated_amount"] == "1000.00"

        response = await client.put(
            f"/api/v1/payments/{created['id']}",
            json={"amount": "2500.00"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["amount"] == "2500.00"
        assert body["unallocated_amount"] == "2500.00"
        assert body["allocated_amount"] == "0.00"

    async def test_reassign_company_to_unknown_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_payment(client, headers)

        response = await client.put(
            f"/api/v1/payments/{created['id']}",
            json={"company_id": str(uuid.uuid4())},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_COMPANY_NOT_FOUND"

    async def test_reassign_company_to_inactive_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_payment(client, headers)
        inactive_company = await _create_company(client, headers)
        await _update_company(client, headers, inactive_company["id"], status="inactive")

        response = await client.put(
            f"/api/v1/payments/{created['id']}",
            json={"company_id": inactive_company["id"]},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PAYMENT_COMPANY_INACTIVE"

    async def test_server_owned_fields_in_the_request_are_ignored(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_payment(client, headers)

        response = await client.put(
            f"/api/v1/payments/{created['id']}",
            json={
                "payment_number": "PAY-0001",
                "allocated_amount": "500.00",
                "unallocated_amount": "9999.00",
                "status": "posted",
            },
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["payment_number"] is None
        assert body["allocated_amount"] == "0.00"
        assert body["status"] == "draft"

    async def test_update_bumps_updated_at_and_sets_updated_by(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_payment(client, headers)

        response = await client.put(
            f"/api/v1/payments/{created['id']}",
            json={"remarks": "revised"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["updated_at"] >= created["updated_at"]

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(select(Payment).where(Payment.id == uuid.UUID(created["id"])))
        ).scalar_one()
        assert row.updated_by == admin.id

    async def test_cannot_update_another_tenants_payment(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_payment(client, headers)

        other_tenant = Tenant(
            name="Other Payment Updater", slug=f"other-pay-upd-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_PAYMENT_PERMISSIONS
        )

        response = await client.put(
            f"/api/v1/payments/{created['id']}",
            json={"remarks": "Hijacked"},
            headers=other_headers,
        )
        assert response.status_code == 404

        unchanged = await client.get(f"/api/v1/payments/{created['id']}", headers=headers)
        assert unchanged.json()["remarks"] is None

    async def test_cannot_update_a_deleted_payment(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_payment(client, headers)
        await client.delete(f"/api/v1/payments/{created['id']}", headers=headers)

        response = await client.put(
            f"/api/v1/payments/{created['id']}",
            json={"remarks": "Should Not Apply"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_NOT_FOUND"

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            f"/api/v1/payments/{uuid.uuid4()}", json={"remarks": "x"}, headers=headers
        )
        assert response.status_code == 404

    async def test_non_draft_payment_cannot_be_updated(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_payment(client, headers)

        row = (
            await db_session.execute(select(Payment).where(Payment.id == uuid.UUID(created["id"])))
        ).scalar_one()
        row.status = PaymentStatus.POSTED
        await db_session.commit()

        response = await client.put(
            f"/api/v1/payments/{created['id']}",
            json={"remarks": "Should not apply"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PAYMENT_NOT_DRAFT"


class TestDeletePayment:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.delete(f"/api/v1/payments/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_delete_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["payment:view", "payment:edit"])
        response = await client.delete(f"/api/v1/payments/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_success_soft_deletes_and_sets_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_payment(client, headers)

        response = await client.delete(f"/api/v1/payments/{created['id']}", headers=headers)
        assert response.status_code == 204
        assert response.content == b""

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(select(Payment).where(Payment.id == uuid.UUID(created["id"])))
        ).scalar_one()
        assert row.deleted_at is not None
        assert row.deleted_by == admin.id

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.delete(f"/api/v1/payments/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404

    async def test_deleting_twice_is_404_the_second_time(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_payment(client, headers)
        first = await client.delete(f"/api/v1/payments/{created['id']}", headers=headers)
        second = await client.delete(f"/api/v1/payments/{created['id']}", headers=headers)
        assert first.status_code == 204
        assert second.status_code == 404

    async def test_cannot_delete_another_tenants_payment(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_payment(client, headers)

        other_tenant = Tenant(
            name="Other Payment Deleter", slug=f"other-pay-del-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_PAYMENT_PERMISSIONS
        )

        response = await client.delete(f"/api/v1/payments/{created['id']}", headers=other_headers)
        assert response.status_code == 404

        still_there = await client.get(f"/api/v1/payments/{created['id']}", headers=headers)
        assert still_there.status_code == 200

    async def test_non_draft_payment_cannot_be_deleted(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_payment(client, headers)

        row = (
            await db_session.execute(select(Payment).where(Payment.id == uuid.UUID(created["id"])))
        ).scalar_one()
        row.status = PaymentStatus.CANCELLED
        await db_session.commit()

        response = await client.delete(f"/api/v1/payments/{created['id']}", headers=headers)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PAYMENT_NOT_DRAFT"


class TestCreatePaymentAllocation:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            f"/api/v1/payments/{uuid.uuid4()}/allocations",
            json={"invoice_id": str(uuid.uuid4()), "allocated_amount": "100.00"},
        )
        assert response.status_code == 401

    async def test_requires_create_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["payment:view"])
        response = await client.post(
            f"/api/v1/payments/{uuid.uuid4()}/allocations",
            json={"invoice_id": str(uuid.uuid4()), "allocated_amount": "100.00"},
            headers=headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_success_recalculates_payment_totals(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Alloc Create Tenant", slug=f"alloc-create-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_ALLOCATION_PERMISSIONS)

        payment = await _create_payment(client, headers, amount="1000.00")
        invoice = await _create_issued_invoice(client, headers)
        assert invoice["balance_amount"] == "1000.00"

        body = await _create_allocation(
            client, headers, payment["id"], invoice_id=invoice["id"], allocated_amount="600.00"
        )
        assert body["payment_id"] == payment["id"]
        assert body["invoice_id"] == invoice["id"]
        assert body["allocated_amount"] == "600.00"

        pay_after = await client.get(f"/api/v1/payments/{payment['id']}", headers=headers)
        assert pay_after.json()["allocated_amount"] == "600.00"
        assert pay_after.json()["unallocated_amount"] == "400.00"

    async def test_success_sets_created_by(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(name="Alloc Audit Tenant", slug=f"alloc-audit-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_ALLOCATION_PERMISSIONS)
        user = (
            await db_session.execute(select(User).where(User.tenant_id == other_tenant.id))
        ).scalar_one()

        payment = await _create_payment(client, headers, amount="1000.00")
        body = await _create_allocation(client, headers, payment["id"], allocated_amount="100.00")

        row = (
            await db_session.execute(
                select(PaymentAllocation).where(PaymentAllocation.id == uuid.UUID(body["id"]))
            )
        ).scalar_one()
        assert row.created_by == user.id
        assert row.tenant_id == user.tenant_id

    async def test_supports_multiple_allocations_on_one_payment(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(name="Multi Alloc Tenant", slug=f"multi-alloc-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_ALLOCATION_PERMISSIONS)

        payment = await _create_payment(client, headers, amount="1000.00")
        invoice_a = await _create_issued_invoice(client, headers)
        invoice_b = await _create_issued_invoice(client, headers)

        await _create_allocation(
            client, headers, payment["id"], invoice_id=invoice_a["id"], allocated_amount="300.00"
        )
        await _create_allocation(
            client, headers, payment["id"], invoice_id=invoice_b["id"], allocated_amount="400.00"
        )

        pay_after = await client.get(f"/api/v1/payments/{payment['id']}", headers=headers)
        assert pay_after.json()["allocated_amount"] == "700.00"
        assert pay_after.json()["unallocated_amount"] == "300.00"

        listed = await client.get(f"/api/v1/payments/{payment['id']}/allocations", headers=headers)
        assert len(listed.json()) == 2

    async def test_supports_one_invoice_allocated_from_many_payments(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Shared Invoice Alloc Tenant", slug=f"shared-inv-alloc-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_ALLOCATION_PERMISSIONS)

        invoice = await _create_issued_invoice(client, headers)
        payment_a = await _create_payment(client, headers, amount="600.00")
        payment_b = await _create_payment(client, headers, amount="400.00")

        await _create_allocation(
            client, headers, payment_a["id"], invoice_id=invoice["id"], allocated_amount="600.00"
        )
        await _create_allocation(
            client, headers, payment_b["id"], invoice_id=invoice["id"], allocated_amount="400.00"
        )

        listed_a = await client.get(
            f"/api/v1/payments/{payment_a['id']}/allocations", headers=headers
        )
        listed_b = await client.get(
            f"/api/v1/payments/{payment_b['id']}/allocations", headers=headers
        )
        assert len(listed_a.json()) == 1
        assert len(listed_b.json()) == 1

    async def test_partial_allocation_leaves_the_rest_unallocated(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Partial Alloc Tenant", slug=f"partial-alloc-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_ALLOCATION_PERMISSIONS)

        payment = await _create_payment(client, headers, amount="1000.00")
        await _create_allocation(client, headers, payment["id"], allocated_amount="250.00")

        pay_after = await client.get(f"/api/v1/payments/{payment['id']}", headers=headers)
        assert pay_after.json()["allocated_amount"] == "250.00"
        assert pay_after.json()["unallocated_amount"] == "750.00"
        assert pay_after.json()["status"] == "draft"

    async def test_unknown_payment_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            f"/api/v1/payments/{uuid.uuid4()}/allocations",
            json={"invoice_id": str(uuid.uuid4()), "allocated_amount": "100.00"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_NOT_FOUND"

    async def test_unknown_invoice_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers)
        response = await client.post(
            f"/api/v1/payments/{payment['id']}/allocations",
            json={"invoice_id": str(uuid.uuid4()), "allocated_amount": "100.00"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_ALLOCATION_INVOICE_NOT_FOUND"

    async def test_draft_invoice_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers)
        invoice = await _create_draft_invoice(client, headers)

        response = await client.post(
            f"/api/v1/payments/{payment['id']}/allocations",
            json={"invoice_id": invoice["id"], "allocated_amount": "100.00"},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PAYMENT_ALLOCATION_INVOICE_INVALID_STATUS"

    async def test_cancelled_invoice_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers)
        invoice = await _create_issued_invoice(client, headers)

        row = (
            await db_session.execute(select(Invoice).where(Invoice.id == uuid.UUID(invoice["id"])))
        ).scalar_one()
        row.status = InvoiceStatus.CANCELLED
        await db_session.commit()

        response = await client.post(
            f"/api/v1/payments/{payment['id']}/allocations",
            json={"invoice_id": invoice["id"], "allocated_amount": "100.00"},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PAYMENT_ALLOCATION_INVOICE_INVALID_STATUS"

    async def test_paid_invoice_is_422(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers)
        invoice = await _create_issued_invoice(client, headers)

        row = (
            await db_session.execute(select(Invoice).where(Invoice.id == uuid.UUID(invoice["id"])))
        ).scalar_one()
        row.status = InvoiceStatus.PAID
        await db_session.commit()

        response = await client.post(
            f"/api/v1/payments/{payment['id']}/allocations",
            json={"invoice_id": invoice["id"], "allocated_amount": "100.00"},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PAYMENT_ALLOCATION_INVOICE_INVALID_STATUS"

    async def test_partially_paid_invoice_is_allowed(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """There is no paid_amount-updating endpoint yet (Session 4/5), so
        partially_paid is induced with a direct status flip - the
        allocation business rule only inspects `status`, independent of
        whether `balance_amount` is itself consistent with it."""
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers, amount="1000.00")
        invoice = await _create_issued_invoice(client, headers)

        row = (
            await db_session.execute(select(Invoice).where(Invoice.id == uuid.UUID(invoice["id"])))
        ).scalar_one()
        row.status = InvoiceStatus.PARTIALLY_PAID
        await db_session.commit()

        body = await _create_allocation(
            client, headers, payment["id"], invoice_id=invoice["id"], allocated_amount="500.00"
        )
        assert body["allocated_amount"] == "500.00"

    async def test_amount_exceeding_invoice_balance_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers, amount="5000.00")
        invoice = await _create_issued_invoice(client, headers)  # balance 1000.00

        response = await client.post(
            f"/api/v1/payments/{payment['id']}/allocations",
            json={"invoice_id": invoice["id"], "allocated_amount": "1000.01"},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PAYMENT_ALLOCATION_AMOUNT_EXCEEDED"

    async def test_amount_exceeding_payment_unallocated_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers, amount="500.00")
        invoice = await _create_issued_invoice(client, headers, quantity="100.000")  # balance 10000

        response = await client.post(
            f"/api/v1/payments/{payment['id']}/allocations",
            json={"invoice_id": invoice["id"], "allocated_amount": "500.01"},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PAYMENT_ALLOCATION_AMOUNT_EXCEEDED"

    async def test_amount_exactly_equal_to_balance_and_unallocated_is_allowed(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers, amount="1000.00")
        invoice = await _create_issued_invoice(client, headers)  # balance 1000.00

        body = await _create_allocation(
            client, headers, payment["id"], invoice_id=invoice["id"], allocated_amount="1000.00"
        )
        assert body["allocated_amount"] == "1000.00"

        pay_after = await client.get(f"/api/v1/payments/{payment['id']}", headers=headers)
        assert pay_after.json()["unallocated_amount"] == "0.00"

    async def test_zero_allocated_amount_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers)
        invoice = await _create_issued_invoice(client, headers)

        response = await client.post(
            f"/api/v1/payments/{payment['id']}/allocations",
            json={"invoice_id": invoice["id"], "allocated_amount": "0"},
            headers=headers,
        )
        assert response.status_code == 422
        assert "allocated_amount" in response.json()["error"]["field_errors"]

    async def test_non_draft_payment_is_409(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers)
        invoice = await _create_issued_invoice(client, headers)

        row = (
            await db_session.execute(select(Payment).where(Payment.id == uuid.UUID(payment["id"])))
        ).scalar_one()
        row.status = PaymentStatus.POSTED
        await db_session.commit()

        response = await client.post(
            f"/api/v1/payments/{payment['id']}/allocations",
            json={"invoice_id": invoice["id"], "allocated_amount": "100.00"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT"

    async def test_cannot_use_another_tenants_invoice(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers)

        other_tenant = Tenant(
            name="Foreign Invoice For Alloc", slug=f"foreign-inv-alloc-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_ALLOCATION_PERMISSIONS
        )
        foreign_invoice = await _create_issued_invoice(client, other_headers)

        response = await client.post(
            f"/api/v1/payments/{payment['id']}/allocations",
            json={"invoice_id": foreign_invoice["id"], "allocated_amount": "100.00"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_ALLOCATION_INVOICE_NOT_FOUND"

    async def test_duplicate_allocation_against_same_invoice_is_conflict(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers, amount="1000.00")
        invoice = await _create_issued_invoice(client, headers)

        await _create_allocation(
            client, headers, payment["id"], invoice_id=invoice["id"], allocated_amount="100.00"
        )
        # A second, small allocation against the same invoice from the same
        # payment stays within both amount ceilings, so it reaches the DB
        # and trips the unique(payment_id, invoice_id) constraint.
        response = await client.post(
            f"/api/v1/payments/{payment['id']}/allocations",
            json={"invoice_id": invoice["id"], "allocated_amount": "50.00"},
            headers=headers,
        )
        assert response.status_code == 409


class TestListPaymentAllocations:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/payments/{uuid.uuid4()}/allocations")
        assert response.status_code == 401

    async def test_requires_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(f"/api/v1/payments/{uuid.uuid4()}/allocations", headers=headers)
        assert response.status_code == 403

    async def test_unknown_payment_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(f"/api/v1/payments/{uuid.uuid4()}/allocations", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_NOT_FOUND"

    async def test_returns_allocations_oldest_first(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers, amount="1000.00")
        first = await _create_allocation(client, headers, payment["id"], allocated_amount="300.00")
        second = await _create_allocation(client, headers, payment["id"], allocated_amount="300.00")

        response = await client.get(
            f"/api/v1/payments/{payment['id']}/allocations", headers=headers
        )
        assert response.status_code == 200
        assert [a["id"] for a in response.json()] == [first["id"], second["id"]]

    async def test_empty_when_no_allocations(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers)
        response = await client.get(
            f"/api/v1/payments/{payment['id']}/allocations", headers=headers
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_allowed_regardless_of_payment_status(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers)

        row = (
            await db_session.execute(select(Payment).where(Payment.id == uuid.UUID(payment["id"])))
        ).scalar_one()
        row.status = PaymentStatus.POSTED
        await db_session.commit()

        response = await client.get(
            f"/api/v1/payments/{payment['id']}/allocations", headers=headers
        )
        assert response.status_code == 200

    async def test_cannot_use_another_tenants_payment(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers)

        other_tenant = Tenant(
            name="Foreign Payment For Alloc List", slug=f"foreign-pay-alloc-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_ALLOCATION_PERMISSIONS
        )

        response = await client.get(
            f"/api/v1/payments/{payment['id']}/allocations", headers=other_headers
        )
        assert response.status_code == 404


class TestUpdatePaymentAllocation:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.put(
            f"/api/v1/payments/{uuid.uuid4()}/allocations/{uuid.uuid4()}",
            json={"allocated_amount": "50.00"},
        )
        assert response.status_code == 401

    async def test_requires_edit_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["payment:view"])
        response = await client.put(
            f"/api/v1/payments/{uuid.uuid4()}/allocations/{uuid.uuid4()}",
            json={"allocated_amount": "50.00"},
            headers=headers,
        )
        assert response.status_code == 403

    async def test_amount_change_recalculates_payment_totals(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers, amount="1000.00")
        allocation = await _create_allocation(
            client, headers, payment["id"], allocated_amount="300.00"
        )

        response = await client.put(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}",
            json={"allocated_amount": "500.00"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["allocated_amount"] == "500.00"

        pay_after = await client.get(f"/api/v1/payments/{payment['id']}", headers=headers)
        assert pay_after.json()["allocated_amount"] == "500.00"
        assert pay_after.json()["unallocated_amount"] == "500.00"

    async def test_can_increase_up_to_its_own_previous_amount_plus_unallocated(
        self, client: AsyncClient
    ) -> None:
        """Regression guard for the update-time ceiling: the allocation's
        own prior amount must be added back to unallocated_amount before
        validating the new amount (see
        PaymentService.update_allocation) - otherwise a same-or-larger
        reallocation of an existing allocation would incorrectly appear to
        exceed the payment's unallocated_amount."""
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers, amount="1000.00")
        invoice = await _create_issued_invoice(client, headers, quantity="100.000")  # balance 10000
        allocation = await _create_allocation(
            client, headers, payment["id"], invoice_id=invoice["id"], allocated_amount="1000.00"
        )

        response = await client.put(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}",
            json={"allocated_amount": "1000.00"},
            headers=headers,
        )
        assert response.status_code == 200

    async def test_reassign_invoice_to_unknown_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers)
        allocation = await _create_allocation(client, headers, payment["id"])

        response = await client.put(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}",
            json={"invoice_id": str(uuid.uuid4())},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_ALLOCATION_INVOICE_NOT_FOUND"

    async def test_reassign_invoice_to_draft_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers)
        allocation = await _create_allocation(client, headers, payment["id"])
        draft_invoice = await _create_draft_invoice(client, headers)

        response = await client.put(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}",
            json={"invoice_id": draft_invoice["id"]},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PAYMENT_ALLOCATION_INVOICE_INVALID_STATUS"

    async def test_amount_exceeding_invoice_balance_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers, amount="5000.00")
        invoice = await _create_issued_invoice(client, headers)  # balance 1000.00
        allocation = await _create_allocation(
            client, headers, payment["id"], invoice_id=invoice["id"], allocated_amount="500.00"
        )

        response = await client.put(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}",
            json={"allocated_amount": "1000.01"},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PAYMENT_ALLOCATION_AMOUNT_EXCEEDED"

    async def test_amount_exceeding_payment_unallocated_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers, amount="1000.00")
        invoice = await _create_issued_invoice(client, headers, quantity="100.000")  # balance 10000
        other_invoice = await _create_issued_invoice(client, headers, quantity="100.000")
        allocation = await _create_allocation(
            client, headers, payment["id"], invoice_id=invoice["id"], allocated_amount="300.00"
        )
        # Consume the rest of the payment's unallocated_amount with a second
        # allocation against a different invoice.
        await _create_allocation(
            client,
            headers,
            payment["id"],
            invoice_id=other_invoice["id"],
            allocated_amount="700.00",
        )

        response = await client.put(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}",
            json={"allocated_amount": "300.01"},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PAYMENT_ALLOCATION_AMOUNT_EXCEEDED"

    async def test_unknown_allocation_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers)
        response = await client.put(
            f"/api/v1/payments/{payment['id']}/allocations/{uuid.uuid4()}",
            json={"allocated_amount": "50.00"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_ALLOCATION_NOT_FOUND"

    async def test_unknown_payment_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            f"/api/v1/payments/{uuid.uuid4()}/allocations/{uuid.uuid4()}",
            json={"allocated_amount": "50.00"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_NOT_FOUND"

    async def test_non_draft_payment_is_409(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers, amount="1000.00")
        allocation = await _create_allocation(
            client, headers, payment["id"], allocated_amount="300.00"
        )

        row = (
            await db_session.execute(select(Payment).where(Payment.id == uuid.UUID(payment["id"])))
        ).scalar_one()
        row.status = PaymentStatus.POSTED
        await db_session.commit()

        response = await client.put(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}",
            json={"allocated_amount": "100.00"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT"

    async def test_cannot_update_another_tenants_allocation(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers, amount="1000.00")
        allocation = await _create_allocation(
            client, headers, payment["id"], allocated_amount="300.00"
        )

        other_tenant = Tenant(
            name="Other Alloc Updater", slug=f"other-alloc-upd-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_ALLOCATION_PERMISSIONS
        )

        response = await client.put(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}",
            json={"allocated_amount": "50.00"},
            headers=other_headers,
        )
        assert response.status_code == 404


class TestDeletePaymentAllocation:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.delete(
            f"/api/v1/payments/{uuid.uuid4()}/allocations/{uuid.uuid4()}"
        )
        assert response.status_code == 401

    async def test_requires_delete_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["payment:view", "payment:edit"])
        response = await client.delete(
            f"/api/v1/payments/{uuid.uuid4()}/allocations/{uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 403

    async def test_success_hard_deletes_and_restores_unallocated_amount(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers, amount="1000.00")
        allocation = await _create_allocation(
            client, headers, payment["id"], allocated_amount="400.00"
        )

        pay_mid = await client.get(f"/api/v1/payments/{payment['id']}", headers=headers)
        assert pay_mid.json()["unallocated_amount"] == "600.00"

        response = await client.delete(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}", headers=headers
        )
        assert response.status_code == 204
        assert response.content == b""

        row = (
            await db_session.execute(
                select(PaymentAllocation).where(PaymentAllocation.id == uuid.UUID(allocation["id"]))
            )
        ).scalar_one_or_none()
        assert row is None  # hard-deleted, not soft-deleted

        pay_after = await client.get(f"/api/v1/payments/{payment['id']}", headers=headers)
        assert pay_after.json()["allocated_amount"] == "0.00"
        assert pay_after.json()["unallocated_amount"] == "1000.00"

    async def test_unknown_allocation_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers)
        response = await client.delete(
            f"/api/v1/payments/{payment['id']}/allocations/{uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_ALLOCATION_NOT_FOUND"

    async def test_unknown_payment_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.delete(
            f"/api/v1/payments/{uuid.uuid4()}/allocations/{uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_NOT_FOUND"

    async def test_deleting_twice_is_404_the_second_time(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers)
        allocation = await _create_allocation(client, headers, payment["id"])

        first = await client.delete(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}", headers=headers
        )
        second = await client.delete(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}", headers=headers
        )
        assert first.status_code == 204
        assert second.status_code == 404

    async def test_non_draft_payment_is_409(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers)
        allocation = await _create_allocation(client, headers, payment["id"])

        row = (
            await db_session.execute(select(Payment).where(Payment.id == uuid.UUID(payment["id"])))
        ).scalar_one()
        row.status = PaymentStatus.POSTED
        await db_session.commit()

        response = await client.delete(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}", headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT"

    async def test_cannot_delete_another_tenants_allocation(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_payment(client, headers)
        allocation = await _create_allocation(client, headers, payment["id"])

        other_tenant = Tenant(
            name="Other Alloc Deleter", slug=f"other-alloc-del-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_ALLOCATION_PERMISSIONS
        )

        response = await client.delete(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}",
            headers=other_headers,
        )
        assert response.status_code == 404

        still_there = await client.get(
            f"/api/v1/payments/{payment['id']}/allocations", headers=headers
        )
        assert len(still_there.json()) == 1


class TestPostPayment:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(f"/api/v1/payments/{uuid.uuid4()}/post")
        assert response.status_code == 401

    async def test_requires_post_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, _ALL_ALLOCATION_PERMISSIONS)
        response = await client.post(f"/api/v1/payments/{uuid.uuid4()}/post", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_view_only_permission_is_not_enough(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["payment:view"])
        response = await client.post(f"/api/v1/payments/{uuid.uuid4()}/post", headers=headers)
        assert response.status_code == 403

    async def test_success_posts_and_assigns_a_payment_number(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Post Success Tenant", slug=f"post-success-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_POST_PERMISSIONS)

        invoice = await _create_issued_invoice(client, headers)
        payment = await _create_payment(client, headers, amount="1000.00")
        await _create_allocation(
            client, headers, payment["id"], invoice_id=invoice["id"], allocated_amount="1000.00"
        )

        response = await client.post(f"/api/v1/payments/{payment['id']}/post", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "posted"
        assert body["payment_number"] == "PAY/2026-27/00001"
        assert body["allocated_amount"] == "1000.00"
        assert body["unallocated_amount"] == "0.00"

    async def test_double_post_is_409(self, client: AsyncClient, db_session: AsyncSession) -> None:
        other_tenant = Tenant(name="Post Double Tenant", slug=f"post-double-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_POST_PERMISSIONS)

        invoice = await _create_issued_invoice(client, headers)
        payment = await _create_payment(client, headers, amount="1000.00")
        await _create_allocation(
            client, headers, payment["id"], invoice_id=invoice["id"], allocated_amount="1000.00"
        )
        first = await client.post(f"/api/v1/payments/{payment['id']}/post", headers=headers)
        assert first.status_code == 200, first.text

        second = await client.post(f"/api/v1/payments/{payment['id']}/post", headers=headers)
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "PAYMENT_NOT_DRAFT"

    async def test_posting_a_cancelled_payment_is_409(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Post Cancelled Tenant", slug=f"post-cancelled-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_POST_PERMISSIONS)

        payment = await _create_payment(client, headers, amount="1000.00")
        row = (
            await db_session.execute(select(Payment).where(Payment.id == uuid.UUID(payment["id"])))
        ).scalar_one()
        row.status = PaymentStatus.CANCELLED
        await db_session.commit()

        response = await client.post(f"/api/v1/payments/{payment['id']}/post", headers=headers)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PAYMENT_NOT_DRAFT"

    async def test_posting_with_no_allocations_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Post No Alloc Tenant", slug=f"post-no-alloc-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_POST_PERMISSIONS)

        payment = await _create_payment(client, headers, amount="1000.00")

        response = await client.post(f"/api/v1/payments/{payment['id']}/post", headers=headers)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PAYMENT_NO_ALLOCATIONS"

    async def test_posting_unknown_payment_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, _ALL_POST_PERMISSIONS)
        response = await client.post(f"/api/v1/payments/{uuid.uuid4()}/post", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_NOT_FOUND"

    async def test_cannot_post_another_tenants_payment(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_issued_invoice(client, headers)
        payment = await _create_payment(client, headers, amount="1000.00")
        await _create_allocation(
            client, headers, payment["id"], invoice_id=invoice["id"], allocated_amount="1000.00"
        )

        other_tenant = Tenant(
            name="Post Isolation Tenant", slug=f"post-isolation-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_POST_PERMISSIONS)

        response = await client.post(
            f"/api/v1/payments/{payment['id']}/post", headers=other_headers
        )
        assert response.status_code == 404

        still_draft = await client.get(f"/api/v1/payments/{payment['id']}", headers=headers)
        assert still_draft.json()["status"] == "draft"

    async def test_posted_payment_cannot_be_updated(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Post Immutable Update Tenant", slug=f"post-imm-upd-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_POST_PERMISSIONS)

        invoice = await _create_issued_invoice(client, headers)
        payment = await _create_payment(client, headers, amount="1000.00")
        await _create_allocation(
            client, headers, payment["id"], invoice_id=invoice["id"], allocated_amount="1000.00"
        )
        await client.post(f"/api/v1/payments/{payment['id']}/post", headers=headers)

        response = await client.put(
            f"/api/v1/payments/{payment['id']}", json={"remarks": "Trying to edit"}, headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PAYMENT_NOT_DRAFT"

    async def test_posted_payment_cannot_be_deleted(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Post Immutable Delete Tenant", slug=f"post-imm-del-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_POST_PERMISSIONS)

        invoice = await _create_issued_invoice(client, headers)
        payment = await _create_payment(client, headers, amount="1000.00")
        await _create_allocation(
            client, headers, payment["id"], invoice_id=invoice["id"], allocated_amount="1000.00"
        )
        await client.post(f"/api/v1/payments/{payment['id']}/post", headers=headers)

        response = await client.delete(f"/api/v1/payments/{payment['id']}", headers=headers)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PAYMENT_NOT_DRAFT"

    async def test_posted_payments_allocations_are_immutable(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Post Immutable Alloc Tenant", slug=f"post-imm-alloc-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_POST_PERMISSIONS)

        invoice = await _create_issued_invoice(client, headers)
        other_invoice = await _create_issued_invoice(client, headers)
        payment = await _create_payment(client, headers, amount="1000.00")
        allocation = await _create_allocation(
            client, headers, payment["id"], invoice_id=invoice["id"], allocated_amount="1000.00"
        )
        await client.post(f"/api/v1/payments/{payment['id']}/post", headers=headers)

        create_response = await client.post(
            f"/api/v1/payments/{payment['id']}/allocations",
            json={"invoice_id": other_invoice["id"], "allocated_amount": "1.00"},
            headers=headers,
        )
        assert create_response.status_code == 409
        assert create_response.json()["error"]["code"] == "PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT"

        update_response = await client.put(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}",
            json={"allocated_amount": "1.00"},
            headers=headers,
        )
        assert update_response.status_code == 409
        assert update_response.json()["error"]["code"] == "PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT"

        delete_response = await client.delete(
            f"/api/v1/payments/{payment['id']}/allocations/{allocation['id']}", headers=headers
        )
        assert delete_response.status_code == 409
        assert delete_response.json()["error"]["code"] == "PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT"
