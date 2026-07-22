import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.models import Invoice, InvoiceItem

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

# _create_invoice provisions a fresh company via the API by default, so test
# users need company:create access too for that setup to succeed.
_ALL_INVOICE_PERMISSIONS = [
    "invoice:view",
    "invoice:create",
    "invoice:edit",
    "invoice:delete",
    "company:view",
    "company:create",
    "company:edit",
]
# _create_invoice_item provisions a fresh trip catch (and that trip catch's
# fish, trip, boat and company) via the API by default, so item test users
# need the full chain's access for that setup to succeed too.
_ALL_INVOICE_ITEM_PERMISSIONS = [
    *_ALL_INVOICE_PERMISSIONS,
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
        "code": f"INVCO-{uuid.uuid4().hex[:8]}",
        "name": f"Invoice Owner {uuid.uuid4().hex[:8]}",
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
        "code": f"ITFISH-{uuid.uuid4().hex[:8]}",
        "name": f"Item Fish {uuid.uuid4().hex[:8]}",
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
        "code": f"ITB-{uuid.uuid4().hex[:8]}",
        "name": f"Item Boat {uuid.uuid4().hex[:8]}",
        "registration_number": f"ITREG-{uuid.uuid4().hex[:8]}",
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
        "trip_number": f"ITTRIP-{uuid.uuid4().hex[:8]}",
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
    """Provisions a fresh, matching trip catch by default (so the fish-match
    and quantity-availability rules pass out of the box); pass `trip_catch`
    to reuse one, or override `trip_catch_id`/`fish_id` directly to exercise
    validation failures."""
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


class TestCreateInvoice:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/invoices",
            json={"company_id": str(uuid.uuid4()), "invoice_date": _INVOICE_DATE},
        )
        assert response.status_code == 401

    async def test_requires_create_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["invoice:view"])
        response = await client.post(
            "/api/v1/invoices",
            json={"company_id": str(uuid.uuid4()), "invoice_date": _INVOICE_DATE},
            headers=headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_success_is_draft_with_zeroed_financials(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        body = await _create_invoice(client, headers, remarks="Weekly settlement")

        assert body["status"] == "draft"
        assert body["invoice_number"] is None
        assert body["subtotal"] == "0.00"
        assert body["discount_amount"] == "0.00"
        assert body["taxable_amount"] == "0.00"
        assert body["tax_amount"] == "0.00"
        assert body["transport_charge"] == "0.00"
        assert body["other_charge"] == "0.00"
        assert body["round_off"] == "0.00"
        assert body["total_amount"] == "0.00"
        assert body["paid_amount"] == "0.00"
        assert body["balance_amount"] == "0.00"
        assert body["remarks"] == "Weekly settlement"
        assert body["issued_at"] is None
        assert body["created_at"] == body["updated_at"]

    async def test_success_sets_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        body = await _create_invoice(client, headers)

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(select(Invoice).where(Invoice.id == uuid.UUID(body["id"])))
        ).scalar_one()
        assert row.created_by == admin.id
        assert row.updated_by == admin.id
        assert row.tenant_id == admin.tenant_id

    async def test_financial_fields_in_the_request_are_ignored(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company_id = (await _create_company(client, headers))["id"]
        response = await client.post(
            "/api/v1/invoices",
            json={
                "company_id": company_id,
                "invoice_date": _INVOICE_DATE,
                "total_amount": "99999.00",
                "paid_amount": "50000.00",
                "status": "issued",
                "invoice_number": "INV-0001",
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["total_amount"] == "0.00"
        assert body["paid_amount"] == "0.00"
        assert body["status"] == "draft"
        assert body["invoice_number"] is None

    async def test_unknown_company_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/invoices",
            json={"company_id": str(uuid.uuid4()), "invoice_date": _INVOICE_DATE},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVOICE_COMPANY_NOT_FOUND"

    async def test_inactive_company_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        await _update_company(client, headers, company["id"], status="inactive")

        response = await client.post(
            "/api/v1/invoices",
            json={"company_id": company["id"], "invoice_date": _INVOICE_DATE},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVOICE_COMPANY_INACTIVE"

    async def test_missing_company_id_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/invoices", json={"invoice_date": _INVOICE_DATE}, headers=headers
        )
        assert response.status_code == 422
        assert "company_id" in response.json()["error"]["field_errors"]

    async def test_missing_invoice_date_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        response = await client.post(
            "/api/v1/invoices", json={"company_id": company["id"]}, headers=headers
        )
        assert response.status_code == 422
        assert "invoice_date" in response.json()["error"]["field_errors"]

    async def test_cannot_use_another_tenants_company(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)

        other_tenant = Tenant(
            name="Foreign Company Owner", slug=f"foreign-company-owner-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_INVOICE_PERMISSIONS
        )
        foreign_company = await _create_company(client, other_headers)

        response = await client.post(
            "/api/v1/invoices",
            json={"company_id": foreign_company["id"], "invoice_date": _INVOICE_DATE},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVOICE_COMPANY_NOT_FOUND"


class TestGetInvoice:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/invoices/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(f"/api/v1/invoices/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_returns_the_invoice(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_invoice(client, headers)
        response = await client.get(f"/api/v1/invoices/{created['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(f"/api/v1/invoices/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVOICE_NOT_FOUND"

    async def test_soft_deleted_invoice_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_invoice(client, headers)
        await client.delete(f"/api/v1/invoices/{created['id']}", headers=headers)
        response = await client.get(f"/api/v1/invoices/{created['id']}", headers=headers)
        assert response.status_code == 404

    async def test_other_tenants_invoice_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_invoice(client, headers)

        other_tenant = Tenant(name="Other Invoice Co", slug=f"other-invoice-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_INVOICE_PERMISSIONS
        )

        response = await client.get(f"/api/v1/invoices/{created['id']}", headers=other_headers)
        assert response.status_code == 404


class TestListInvoices:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/invoices")
        assert response.status_code == 401

    async def test_default_response_shape(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_invoice(client, headers)
        response = await client.get("/api/v1/invoices", headers=headers)
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
            name="Search Invoice Company Tenant", slug=f"search-inv-co-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_INVOICE_PERMISSIONS)

        marker = uuid.uuid4().hex[:8]
        matching_company = await _create_company(
            client, headers, name=f"Ocean Fresh Traders {marker}"
        )
        irrelevant_company = await _create_company(client, headers, name=f"Irrelevant Co {marker}")
        target = await _create_invoice(client, headers, company_id=matching_company["id"])
        await _create_invoice(client, headers, company_id=irrelevant_company["id"])

        response = await client.get(
            "/api/v1/invoices", params={"q": f"ocean fresh traders {marker}"}, headers=headers
        )
        ids = [i["id"] for i in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_filters_by_company_id(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Company Filter Invoice Tenant", slug=f"company-filter-inv-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_INVOICE_PERMISSIONS)

        company_a = await _create_company(client, headers)
        company_b = await _create_company(client, headers)
        target = await _create_invoice(client, headers, company_id=company_a["id"])
        await _create_invoice(client, headers, company_id=company_b["id"])

        response = await client.get(
            "/api/v1/invoices", params={"company_id": company_a["id"]}, headers=headers
        )
        ids = [i["id"] for i in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_filters_by_status(self, client: AsyncClient, db_session: AsyncSession) -> None:
        other_tenant = Tenant(
            name="Status Filter Invoice Tenant", slug=f"status-filter-inv-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_INVOICE_PERMISSIONS)

        target = await _create_invoice(client, headers)

        response = await client.get("/api/v1/invoices", params={"status": "draft"}, headers=headers)
        ids = [i["id"] for i in response.json()["data"]]
        assert ids == [target["id"]]

        response_issued = await client.get(
            "/api/v1/invoices", params={"status": "issued"}, headers=headers
        )
        assert response_issued.json()["data"] == []

    async def test_filters_by_invoice_date_range(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Date Filter Invoice Tenant", slug=f"date-filter-inv-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_INVOICE_PERMISSIONS)

        in_range = await _create_invoice(client, headers, invoice_date="2026-06-05")
        await _create_invoice(client, headers, invoice_date="2099-01-01")

        response = await client.get(
            "/api/v1/invoices",
            params={"invoice_date_from": "2026-06-01", "invoice_date_to": "2026-06-30"},
            headers=headers,
        )
        ids = [i["id"] for i in response.json()["data"]]
        assert ids == [in_range["id"]]

    async def test_sort_ascending_and_descending_by_invoice_date(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Sort Date Invoice Tenant", slug=f"sort-date-inv-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_INVOICE_PERMISSIONS)

        company_id = (await _create_company(client, headers))["id"]
        older = await _create_invoice(
            client, headers, company_id=company_id, invoice_date="2026-06-01"
        )
        newer = await _create_invoice(
            client, headers, company_id=company_id, invoice_date="2026-06-08"
        )

        asc = await client.get("/api/v1/invoices", params={"sort": "invoice_date"}, headers=headers)
        assert [i["id"] for i in asc.json()["data"]] == [older["id"], newer["id"]]

        desc = await client.get(
            "/api/v1/invoices", params={"sort": "-invoice_date"}, headers=headers
        )
        assert [i["id"] for i in desc.json()["data"]] == [newer["id"], older["id"]]

    async def test_invalid_sort_field_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/invoices", params={"sort": "company_id"}, headers=headers
        )
        assert response.status_code == 422

    async def test_default_sort_is_most_recent_first(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Default Sort Invoice Tenant", slug=f"default-sort-inv-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_INVOICE_PERMISSIONS)

        first = await _create_invoice(client, headers)
        second = await _create_invoice(client, headers)

        response = await client.get("/api/v1/invoices", headers=headers)
        ids = [i["id"] for i in response.json()["data"]]
        assert ids == [second["id"], first["id"]]

    async def test_pagination_meta_is_correct(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Pagination Invoice Tenant", slug=f"pagination-inv-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_INVOICE_PERMISSIONS)

        for _ in range(3):
            await _create_invoice(client, headers)

        response = await client.get(
            "/api/v1/invoices", params={"page": 1, "page_size": 2}, headers=headers
        )
        meta = response.json()["meta"]
        assert meta["total_records"] == 3
        assert meta["total_pages"] == 2
        assert meta["current_page"] == 1
        assert meta["page_size"] == 2
        assert meta["has_next"] is True
        assert meta["has_previous"] is False

        page2 = await client.get(
            "/api/v1/invoices", params={"page": 2, "page_size": 2}, headers=headers
        )
        meta2 = page2.json()["meta"]
        assert meta2["has_next"] is False
        assert meta2["has_previous"] is True
        assert len(page2.json()["data"]) == 1

    async def test_invalid_page_size_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/invoices", params={"page_size": 101}, headers=headers)
        assert response.status_code == 422

    async def test_deleted_invoices_are_excluded(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Fresh List Invoice Tenant", slug=f"fresh-inv-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        isolated_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_INVOICE_PERMISSIONS
        )

        created = await _create_invoice(client, isolated_headers)
        await client.delete(f"/api/v1/invoices/{created['id']}", headers=isolated_headers)

        response = await client.get("/api/v1/invoices", headers=isolated_headers)
        assert response.json()["data"] == []
        assert response.json()["meta"]["total_records"] == 0

    async def test_tenant_isolation_returns_only_own_invoices(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        await _create_invoice(client, headers)

        other_tenant = Tenant(
            name="Isolated Invoice Co", slug=f"isolated-invoice-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_INVOICE_PERMISSIONS
        )

        response = await client.get("/api/v1/invoices", headers=other_headers)
        assert response.json()["data"] == []


class TestUpdateInvoice:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.put(f"/api/v1/invoices/{uuid.uuid4()}", json={"remarks": "x"})
        assert response.status_code == 401

    async def test_requires_edit_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["invoice:view"])
        response = await client.put(
            f"/api/v1/invoices/{uuid.uuid4()}", json={"remarks": "x"}, headers=headers
        )
        assert response.status_code == 403

    async def test_partial_update_only_changes_supplied_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_invoice(client, headers, remarks="Original")

        response = await client.put(
            f"/api/v1/invoices/{created['id']}",
            json={"due_date": "2026-08-13"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["due_date"] == "2026-08-13"
        assert body["remarks"] == "Original"

    async def test_reassign_company_to_unknown_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_invoice(client, headers)

        response = await client.put(
            f"/api/v1/invoices/{created['id']}",
            json={"company_id": str(uuid.uuid4())},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVOICE_COMPANY_NOT_FOUND"

    async def test_reassign_company_to_inactive_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_invoice(client, headers)
        inactive_company = await _create_company(client, headers)
        await _update_company(client, headers, inactive_company["id"], status="inactive")

        response = await client.put(
            f"/api/v1/invoices/{created['id']}",
            json={"company_id": inactive_company["id"]},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVOICE_COMPANY_INACTIVE"

    async def test_financial_fields_in_the_request_are_ignored(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_invoice(client, headers)

        response = await client.put(
            f"/api/v1/invoices/{created['id']}",
            json={"total_amount": "99999.00", "status": "issued"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total_amount"] == "0.00"
        assert body["status"] == "draft"

    async def test_update_bumps_updated_at_and_sets_updated_by(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_invoice(client, headers)

        response = await client.put(
            f"/api/v1/invoices/{created['id']}",
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
            await db_session.execute(select(Invoice).where(Invoice.id == uuid.UUID(created["id"])))
        ).scalar_one()
        assert row.updated_by == admin.id

    async def test_cannot_update_another_tenants_invoice(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_invoice(client, headers)

        other_tenant = Tenant(
            name="Other Invoice Updater", slug=f"other-inv-upd-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_INVOICE_PERMISSIONS
        )

        response = await client.put(
            f"/api/v1/invoices/{created['id']}",
            json={"remarks": "Hijacked"},
            headers=other_headers,
        )
        assert response.status_code == 404

        unchanged = await client.get(f"/api/v1/invoices/{created['id']}", headers=headers)
        assert unchanged.json()["remarks"] is None

    async def test_cannot_update_a_deleted_invoice(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_invoice(client, headers)
        await client.delete(f"/api/v1/invoices/{created['id']}", headers=headers)

        response = await client.put(
            f"/api/v1/invoices/{created['id']}",
            json={"remarks": "Should Not Apply"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVOICE_NOT_FOUND"

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            f"/api/v1/invoices/{uuid.uuid4()}", json={"remarks": "x"}, headers=headers
        )
        assert response.status_code == 404

    async def test_non_draft_invoice_cannot_be_updated(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_invoice(client, headers)

        row = (
            await db_session.execute(select(Invoice).where(Invoice.id == uuid.UUID(created["id"])))
        ).scalar_one()
        row.status = InvoiceStatus.ISSUED
        await db_session.commit()

        response = await client.put(
            f"/api/v1/invoices/{created['id']}",
            json={"remarks": "Should not apply"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVOICE_NOT_DRAFT"


class TestDeleteInvoice:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.delete(f"/api/v1/invoices/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_delete_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["invoice:view", "invoice:edit"])
        response = await client.delete(f"/api/v1/invoices/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_success_soft_deletes_and_sets_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_invoice(client, headers)

        response = await client.delete(f"/api/v1/invoices/{created['id']}", headers=headers)
        assert response.status_code == 204
        assert response.content == b""

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(select(Invoice).where(Invoice.id == uuid.UUID(created["id"])))
        ).scalar_one()
        assert row.deleted_at is not None
        assert row.deleted_by == admin.id

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.delete(f"/api/v1/invoices/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404

    async def test_deleting_twice_is_404_the_second_time(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_invoice(client, headers)
        first = await client.delete(f"/api/v1/invoices/{created['id']}", headers=headers)
        second = await client.delete(f"/api/v1/invoices/{created['id']}", headers=headers)
        assert first.status_code == 204
        assert second.status_code == 404

    async def test_cannot_delete_another_tenants_invoice(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_invoice(client, headers)

        other_tenant = Tenant(
            name="Other Invoice Deleter", slug=f"other-inv-del-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_INVOICE_PERMISSIONS
        )

        response = await client.delete(f"/api/v1/invoices/{created['id']}", headers=other_headers)
        assert response.status_code == 404

        still_there = await client.get(f"/api/v1/invoices/{created['id']}", headers=headers)
        assert still_there.status_code == 200

    async def test_non_draft_invoice_cannot_be_deleted(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_invoice(client, headers)

        row = (
            await db_session.execute(select(Invoice).where(Invoice.id == uuid.UUID(created["id"])))
        ).scalar_one()
        row.status = InvoiceStatus.CANCELLED
        await db_session.commit()

        response = await client.delete(f"/api/v1/invoices/{created['id']}", headers=headers)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVOICE_NOT_DRAFT"


class TestAddInvoiceItem:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            f"/api/v1/invoices/{uuid.uuid4()}/items",
            json={
                "trip_catch_id": str(uuid.uuid4()),
                "fish_id": str(uuid.uuid4()),
                "quantity": "10.000",
                "unit": "kg",
                "rate": "100.0000",
            },
        )
        assert response.status_code == 401

    async def test_requires_create_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["invoice:view"])
        response = await client.post(
            f"/api/v1/invoices/{uuid.uuid4()}/items",
            json={
                "trip_catch_id": str(uuid.uuid4()),
                "fish_id": str(uuid.uuid4()),
                "quantity": "10.000",
                "unit": "kg",
                "rate": "100.0000",
            },
            headers=headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_success_is_line_one_with_server_calculated_financials(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        trip_catch = await _create_trip_catch(client, headers)

        body = await _create_invoice_item(
            client,
            headers,
            invoice["id"],
            trip_catch=trip_catch,
            description="Pomfret - Grade A",
            quantity="25.000",
            rate="100.0000",
            discount_percent="5.00",
            tax_rate="5.00",
        )

        assert body["invoice_id"] == invoice["id"]
        assert body["line_number"] == 1
        assert body["trip_catch_id"] == trip_catch["id"]
        assert body["fish_id"] == trip_catch["fish_id"]
        assert body["description"] == "Pomfret - Grade A"
        assert body["quantity"] == "25.000"
        assert body["discount_percent"] == "5.00"
        assert body["tax_rate"] == "5.00"
        # gross = 25*100=2500; discount = 125.00; taxable = 2375.00;
        # tax = 118.75; line_total = 2493.75.
        assert body["discount_amount"] == "125.00"
        assert body["taxable_amount"] == "2375.00"
        assert body["tax_amount"] == "118.75"
        assert body["line_total"] == "2493.75"
        assert body["created_at"] == body["updated_at"]

    async def test_second_item_gets_line_number_two(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        await _create_invoice_item(client, headers, invoice["id"])
        second = await _create_invoice_item(client, headers, invoice["id"])
        assert second["line_number"] == 2

    async def test_success_sets_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        body = await _create_invoice_item(client, headers, invoice["id"])

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(
                select(InvoiceItem).where(InvoiceItem.id == uuid.UUID(body["id"]))
            )
        ).scalar_one()
        assert row.created_by == admin.id
        assert row.updated_by == admin.id
        assert row.tenant_id == admin.tenant_id

    async def test_financial_fields_in_the_request_are_ignored(self, client: AsyncClient) -> None:
        """The client's line_total/tax_amount/discount_amount are dropped
        entirely - the server computes its own from quantity/rate/
        discount_percent/tax_rate (app.modules.invoices.domain.totals),
        not "0.00" as before Session 4's calculation engine."""
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        trip_catch = await _create_trip_catch(client, headers)

        response = await client.post(
            f"/api/v1/invoices/{invoice['id']}/items",
            json={
                "trip_catch_id": trip_catch["id"],
                "fish_id": trip_catch["fish_id"],
                "quantity": "10.000",
                "unit": "kg",
                "rate": "100.0000",
                "line_total": "99999.00",
                "tax_amount": "500.00",
                "discount_amount": "10.00",
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        # 10 * 100 = 1000, discount_percent/tax_rate default to 0.
        assert body["discount_amount"] == "0.00"
        assert body["taxable_amount"] == "1000.00"
        assert body["tax_amount"] == "0.00"
        assert body["line_total"] == "1000.00"

    async def test_unknown_invoice_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        trip_catch = await _create_trip_catch(client, headers)
        response = await client.post(
            f"/api/v1/invoices/{uuid.uuid4()}/items",
            json={
                "trip_catch_id": trip_catch["id"],
                "fish_id": trip_catch["fish_id"],
                "quantity": "10.000",
                "unit": "kg",
                "rate": "100.0000",
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVOICE_NOT_FOUND"

    async def test_unknown_trip_catch_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        fish = await _create_fish(client, headers)

        response = await client.post(
            f"/api/v1/invoices/{invoice['id']}/items",
            json={
                "trip_catch_id": str(uuid.uuid4()),
                "fish_id": fish["id"],
                "quantity": "10.000",
                "unit": "kg",
                "rate": "100.0000",
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVOICE_ITEM_TRIP_CATCH_NOT_FOUND"

    async def test_unknown_fish_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        trip_catch = await _create_trip_catch(client, headers)

        response = await client.post(
            f"/api/v1/invoices/{invoice['id']}/items",
            json={
                "trip_catch_id": trip_catch["id"],
                "fish_id": str(uuid.uuid4()),
                "quantity": "10.000",
                "unit": "kg",
                "rate": "100.0000",
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVOICE_ITEM_FISH_NOT_FOUND"

    async def test_fish_mismatch_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        trip_catch = await _create_trip_catch(client, headers)
        other_fish = await _create_fish(client, headers)

        response = await client.post(
            f"/api/v1/invoices/{invoice['id']}/items",
            json={
                "trip_catch_id": trip_catch["id"],
                "fish_id": other_fish["id"],
                "quantity": "10.000",
                "unit": "kg",
                "rate": "100.0000",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVOICE_ITEM_FISH_MISMATCH"

    async def test_quantity_exceeding_available_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        trip_catch = await _create_trip_catch(client, headers, quantity_caught="10.000")

        response = await client.post(
            f"/api/v1/invoices/{invoice['id']}/items",
            json={
                "trip_catch_id": trip_catch["id"],
                "fish_id": trip_catch["fish_id"],
                "quantity": "10.001",
                "unit": "kg",
                "rate": "100.0000",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVOICE_ITEM_QUANTITY_EXCEEDS_AVAILABLE"

    async def test_quantity_equal_to_available_is_allowed(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        trip_catch = await _create_trip_catch(client, headers, quantity_caught="10.000")

        body = await _create_invoice_item(
            client, headers, invoice["id"], trip_catch=trip_catch, quantity="10.000"
        )
        assert body["quantity"] == "10.000"

    async def test_quantity_does_not_deduct_available_quantity(self, client: AsyncClient) -> None:
        """Session 3 validates only - it must never reserve or deduct
        inventory. That happens only in the Session 5 issue workflow."""
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        trip_catch = await _create_trip_catch(client, headers, quantity_caught="10.000")

        await _create_invoice_item(
            client, headers, invoice["id"], trip_catch=trip_catch, quantity="10.000"
        )

        response = await client.get(f"/api/v1/trip-catches/{trip_catch['id']}", headers=headers)
        assert response.json()["available_quantity"] == "10.000"

    async def test_zero_quantity_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        trip_catch = await _create_trip_catch(client, headers)

        response = await client.post(
            f"/api/v1/invoices/{invoice['id']}/items",
            json={
                "trip_catch_id": trip_catch["id"],
                "fish_id": trip_catch["fish_id"],
                "quantity": "0",
                "unit": "kg",
                "rate": "100.0000",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "quantity" in response.json()["error"]["field_errors"]

    async def test_negative_rate_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        trip_catch = await _create_trip_catch(client, headers)

        response = await client.post(
            f"/api/v1/invoices/{invoice['id']}/items",
            json={
                "trip_catch_id": trip_catch["id"],
                "fish_id": trip_catch["fish_id"],
                "quantity": "10.000",
                "unit": "kg",
                "rate": "-1",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "rate" in response.json()["error"]["field_errors"]

    async def test_discount_percent_above_100_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        trip_catch = await _create_trip_catch(client, headers)

        response = await client.post(
            f"/api/v1/invoices/{invoice['id']}/items",
            json={
                "trip_catch_id": trip_catch["id"],
                "fish_id": trip_catch["fish_id"],
                "quantity": "10.000",
                "unit": "kg",
                "rate": "100.0000",
                "discount_percent": "100.01",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "discount_percent" in response.json()["error"]["field_errors"]

    async def test_non_draft_invoice_cannot_receive_items(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        trip_catch = await _create_trip_catch(client, headers)

        row = (
            await db_session.execute(select(Invoice).where(Invoice.id == uuid.UUID(invoice["id"])))
        ).scalar_one()
        row.status = InvoiceStatus.ISSUED
        await db_session.commit()

        response = await client.post(
            f"/api/v1/invoices/{invoice['id']}/items",
            json={
                "trip_catch_id": trip_catch["id"],
                "fish_id": trip_catch["fish_id"],
                "quantity": "10.000",
                "unit": "kg",
                "rate": "100.0000",
            },
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVOICE_NOT_DRAFT"

    async def test_cannot_use_another_tenants_invoice(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)

        other_tenant = Tenant(
            name="Foreign Invoice For Items", slug=f"foreign-inv-items-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_INVOICE_ITEM_PERMISSIONS
        )
        foreign_invoice = await _create_invoice(client, other_headers)
        trip_catch = await _create_trip_catch(client, headers)

        response = await client.post(
            f"/api/v1/invoices/{foreign_invoice['id']}/items",
            json={
                "trip_catch_id": trip_catch["id"],
                "fish_id": trip_catch["fish_id"],
                "quantity": "10.000",
                "unit": "kg",
                "rate": "100.0000",
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVOICE_NOT_FOUND"

    async def test_cannot_use_another_tenants_trip_catch(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)

        other_tenant = Tenant(
            name="Foreign Trip Catch Owner", slug=f"foreign-catch-owner-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_INVOICE_ITEM_PERMISSIONS
        )
        foreign_catch = await _create_trip_catch(client, other_headers)

        response = await client.post(
            f"/api/v1/invoices/{invoice['id']}/items",
            json={
                "trip_catch_id": foreign_catch["id"],
                "fish_id": foreign_catch["fish_id"],
                "quantity": "10.000",
                "unit": "kg",
                "rate": "100.0000",
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVOICE_ITEM_TRIP_CATCH_NOT_FOUND"


class TestListInvoiceItems:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/invoices/{uuid.uuid4()}/items")
        assert response.status_code == 401

    async def test_requires_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(f"/api/v1/invoices/{uuid.uuid4()}/items", headers=headers)
        assert response.status_code == 403

    async def test_unknown_invoice_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(f"/api/v1/invoices/{uuid.uuid4()}/items", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVOICE_NOT_FOUND"

    async def test_returns_items_ordered_by_line_number(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        first = await _create_invoice_item(client, headers, invoice["id"])
        second = await _create_invoice_item(client, headers, invoice["id"])

        response = await client.get(f"/api/v1/invoices/{invoice['id']}/items", headers=headers)
        assert response.status_code == 200
        items = response.json()
        assert [i["id"] for i in items] == [first["id"], second["id"]]

    async def test_search_matches_description(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        marker = uuid.uuid4().hex[:8]
        target = await _create_invoice_item(
            client, headers, invoice["id"], description=f"Special Pomfret {marker}"
        )
        await _create_invoice_item(
            client, headers, invoice["id"], description=f"Irrelevant {marker}"
        )

        response = await client.get(
            f"/api/v1/invoices/{invoice['id']}/items",
            params={"q": f"special pomfret {marker}"},
            headers=headers,
        )
        assert [i["id"] for i in response.json()] == [target["id"]]

    async def test_search_matches_fish_name(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        marker = uuid.uuid4().hex[:8]
        matching_fish = await _create_fish(client, headers, name=f"Sardine {marker}")
        matching_catch = await _create_trip_catch(client, headers, fish_id=matching_fish["id"])
        target = await _create_invoice_item(
            client, headers, invoice["id"], trip_catch=matching_catch
        )
        await _create_invoice_item(client, headers, invoice["id"])

        response = await client.get(
            f"/api/v1/invoices/{invoice['id']}/items",
            params={"q": f"sardine {marker}"},
            headers=headers,
        )
        assert [i["id"] for i in response.json()] == [target["id"]]

    async def test_scoped_to_one_invoice(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice_a = await _create_invoice(client, headers)
        invoice_b = await _create_invoice(client, headers)
        target = await _create_invoice_item(client, headers, invoice_a["id"])
        await _create_invoice_item(client, headers, invoice_b["id"])

        response = await client.get(f"/api/v1/invoices/{invoice_a['id']}/items", headers=headers)
        assert [i["id"] for i in response.json()] == [target["id"]]

    async def test_deleted_items_are_excluded(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item = await _create_invoice_item(client, headers, invoice["id"])
        await client.delete(f"/api/v1/invoices/{invoice['id']}/items/{item['id']}", headers=headers)

        response = await client.get(f"/api/v1/invoices/{invoice['id']}/items", headers=headers)
        assert response.json() == []

    async def test_listing_is_allowed_on_a_non_draft_invoice(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item = await _create_invoice_item(client, headers, invoice["id"])

        row = (
            await db_session.execute(select(Invoice).where(Invoice.id == uuid.UUID(invoice["id"])))
        ).scalar_one()
        row.status = InvoiceStatus.ISSUED
        await db_session.commit()

        response = await client.get(f"/api/v1/invoices/{invoice['id']}/items", headers=headers)
        assert response.status_code == 200
        assert [i["id"] for i in response.json()] == [item["id"]]

    async def test_other_tenants_invoice_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        await _create_invoice_item(client, headers, invoice["id"])

        other_tenant = Tenant(
            name="Other Item List Tenant", slug=f"other-item-list-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_INVOICE_ITEM_PERMISSIONS
        )

        response = await client.get(
            f"/api/v1/invoices/{invoice['id']}/items", headers=other_headers
        )
        assert response.status_code == 404


class TestUpdateInvoiceItem:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.put(
            f"/api/v1/invoices/{uuid.uuid4()}/items/{uuid.uuid4()}", json={"quantity": "5.000"}
        )
        assert response.status_code == 401

    async def test_requires_edit_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["invoice:view"])
        response = await client.put(
            f"/api/v1/invoices/{uuid.uuid4()}/items/{uuid.uuid4()}",
            json={"quantity": "5.000"},
            headers=headers,
        )
        assert response.status_code == 403

    async def test_partial_update_only_changes_supplied_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item = await _create_invoice_item(client, headers, invoice["id"], description="Original")

        response = await client.put(
            f"/api/v1/invoices/{invoice['id']}/items/{item['id']}",
            json={"quantity": "5.000"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["quantity"] == "5.000"
        assert body["description"] == "Original"

    async def test_reassign_trip_catch_revalidates_fish_match(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item = await _create_invoice_item(client, headers, invoice["id"])
        other_trip_catch = await _create_trip_catch(client, headers)

        response = await client.put(
            f"/api/v1/invoices/{invoice['id']}/items/{item['id']}",
            json={"trip_catch_id": other_trip_catch["id"]},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVOICE_ITEM_FISH_MISMATCH"

    async def test_reassign_trip_catch_and_fish_together_succeeds(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item = await _create_invoice_item(client, headers, invoice["id"])
        other_trip_catch = await _create_trip_catch(client, headers)

        response = await client.put(
            f"/api/v1/invoices/{invoice['id']}/items/{item['id']}",
            json={
                "trip_catch_id": other_trip_catch["id"],
                "fish_id": other_trip_catch["fish_id"],
            },
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["trip_catch_id"] == other_trip_catch["id"]
        assert body["fish_id"] == other_trip_catch["fish_id"]

    async def test_quantity_increase_beyond_available_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        trip_catch = await _create_trip_catch(client, headers, quantity_caught="10.000")
        item = await _create_invoice_item(
            client, headers, invoice["id"], trip_catch=trip_catch, quantity="5.000"
        )

        response = await client.put(
            f"/api/v1/invoices/{invoice['id']}/items/{item['id']}",
            json={"quantity": "10.001"},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVOICE_ITEM_QUANTITY_EXCEEDS_AVAILABLE"

    async def test_revalidates_even_when_only_rate_changes(self, client: AsyncClient) -> None:
        """ "Revalidate every update" per TASKS.md - changing an unrelated
        field still re-runs the trip catch/fish/quantity checks against the
        item's current state."""
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item = await _create_invoice_item(client, headers, invoice["id"])

        response = await client.put(
            f"/api/v1/invoices/{invoice['id']}/items/{item['id']}",
            json={"rate": "120.0000"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["rate"] == "120.0000"

    async def test_unknown_item_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        response = await client.put(
            f"/api/v1/invoices/{invoice['id']}/items/{uuid.uuid4()}",
            json={"quantity": "5.000"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVOICE_ITEM_NOT_FOUND"

    async def test_update_bumps_updated_at_and_sets_updated_by(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item = await _create_invoice_item(client, headers, invoice["id"])

        response = await client.put(
            f"/api/v1/invoices/{invoice['id']}/items/{item['id']}",
            json={"description": "revised"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["updated_at"] >= item["updated_at"]

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(
                select(InvoiceItem).where(InvoiceItem.id == uuid.UUID(item["id"]))
            )
        ).scalar_one()
        assert row.updated_by == admin.id

    async def test_cannot_update_an_item_on_a_deleted_invoice(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item = await _create_invoice_item(client, headers, invoice["id"])
        await client.delete(f"/api/v1/invoices/{invoice['id']}", headers=headers)

        response = await client.put(
            f"/api/v1/invoices/{invoice['id']}/items/{item['id']}",
            json={"quantity": "5.000"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVOICE_NOT_FOUND"

    async def test_non_draft_invoice_item_cannot_be_updated(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item = await _create_invoice_item(client, headers, invoice["id"])

        row = (
            await db_session.execute(select(Invoice).where(Invoice.id == uuid.UUID(invoice["id"])))
        ).scalar_one()
        row.status = InvoiceStatus.ISSUED
        await db_session.commit()

        response = await client.put(
            f"/api/v1/invoices/{invoice['id']}/items/{item['id']}",
            json={"quantity": "5.000"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVOICE_NOT_DRAFT"

    async def test_cannot_update_another_tenants_invoice_item(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item = await _create_invoice_item(client, headers, invoice["id"])

        other_tenant = Tenant(
            name="Other Item Updater", slug=f"other-item-upd-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_INVOICE_ITEM_PERMISSIONS
        )

        response = await client.put(
            f"/api/v1/invoices/{invoice['id']}/items/{item['id']}",
            json={"description": "Hijacked"},
            headers=other_headers,
        )
        assert response.status_code == 404


class TestDeleteInvoiceItem:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.delete(f"/api/v1/invoices/{uuid.uuid4()}/items/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_delete_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["invoice:view", "invoice:edit"])
        response = await client.delete(
            f"/api/v1/invoices/{uuid.uuid4()}/items/{uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 403

    async def test_success_soft_deletes_and_sets_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item = await _create_invoice_item(client, headers, invoice["id"])

        response = await client.delete(
            f"/api/v1/invoices/{invoice['id']}/items/{item['id']}", headers=headers
        )
        assert response.status_code == 204
        assert response.content == b""

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(
                select(InvoiceItem).where(InvoiceItem.id == uuid.UUID(item["id"]))
            )
        ).scalar_one()
        assert row.deleted_at is not None
        assert row.deleted_by == admin.id

    async def test_does_not_change_trip_catch_available_quantity(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        trip_catch = await _create_trip_catch(client, headers, quantity_caught="10.000")
        item = await _create_invoice_item(
            client, headers, invoice["id"], trip_catch=trip_catch, quantity="10.000"
        )

        await client.delete(f"/api/v1/invoices/{invoice['id']}/items/{item['id']}", headers=headers)

        response = await client.get(f"/api/v1/trip-catches/{trip_catch['id']}", headers=headers)
        assert response.json()["available_quantity"] == "10.000"

    async def test_unknown_item_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        response = await client.delete(
            f"/api/v1/invoices/{invoice['id']}/items/{uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVOICE_ITEM_NOT_FOUND"

    async def test_deleting_twice_is_404_the_second_time(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item = await _create_invoice_item(client, headers, invoice["id"])

        first = await client.delete(
            f"/api/v1/invoices/{invoice['id']}/items/{item['id']}", headers=headers
        )
        second = await client.delete(
            f"/api/v1/invoices/{invoice['id']}/items/{item['id']}", headers=headers
        )
        assert first.status_code == 204
        assert second.status_code == 404

    async def test_non_draft_invoice_item_cannot_be_deleted(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item = await _create_invoice_item(client, headers, invoice["id"])

        row = (
            await db_session.execute(select(Invoice).where(Invoice.id == uuid.UUID(invoice["id"])))
        ).scalar_one()
        row.status = InvoiceStatus.CANCELLED
        await db_session.commit()

        response = await client.delete(
            f"/api/v1/invoices/{invoice['id']}/items/{item['id']}", headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVOICE_NOT_DRAFT"

    async def test_cannot_delete_another_tenants_invoice_item(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item = await _create_invoice_item(client, headers, invoice["id"])

        other_tenant = Tenant(
            name="Other Item Deleter", slug=f"other-item-del-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_INVOICE_ITEM_PERMISSIONS
        )

        response = await client.delete(
            f"/api/v1/invoices/{invoice['id']}/items/{item['id']}", headers=other_headers
        )
        assert response.status_code == 404

        still_there = await client.get(f"/api/v1/invoices/{invoice['id']}/items", headers=headers)
        assert len(still_there.json()) == 1


class TestFinancialEngine:
    """Sprint 9 Session 4 - the full CRUD surface is already covered above;
    these tests focus specifically on the financial engine's HTTP contract:
    client totals are ignored, the server recalculates automatically on
    every mutation, and Decimal precision is exact end-to-end."""

    async def test_create_with_charges_totals_immediately_with_no_items(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        body = await _create_invoice(
            client, headers, transport_charge="250.00", other_charge="10.00"
        )
        assert body["subtotal"] == "0.00"
        assert body["transport_charge"] == "250.00"
        assert body["other_charge"] == "10.00"
        assert body["total_amount"] == "260.00"
        assert body["balance_amount"] == "260.00"

    async def test_negative_transport_charge_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company_id = (await _create_company(client, headers))["id"]
        response = await client.post(
            "/api/v1/invoices",
            json={
                "company_id": company_id,
                "invoice_date": _INVOICE_DATE,
                "transport_charge": "-1.00",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "transport_charge" in response.json()["error"]["field_errors"]

    async def test_adding_an_item_updates_the_invoice_totals(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        trip_catch = await _create_trip_catch(client, headers)

        await _create_invoice_item(
            client,
            headers,
            invoice["id"],
            trip_catch=trip_catch,
            quantity="50.000",
            rate="450.0000",
            tax_rate="5.00",
        )

        response = await client.get(f"/api/v1/invoices/{invoice['id']}", headers=headers)
        body = response.json()
        assert body["subtotal"] == "23625.00"
        assert body["taxable_amount"] == "22500.00"
        assert body["tax_amount"] == "1125.00"
        assert body["total_amount"] == "23625.00"
        assert body["balance_amount"] == "23625.00"

    async def test_adding_a_second_item_sums_both_lines(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)

        await _create_invoice_item(
            client, headers, invoice["id"], quantity="10", rate="100", unit="kg"
        )
        await _create_invoice_item(
            client, headers, invoice["id"], quantity="5", rate="50", discount_percent="10"
        )

        response = await client.get(f"/api/v1/invoices/{invoice['id']}", headers=headers)
        body = response.json()
        # item 1: 10*100=1000; item 2: 5*50=250, discount 25 -> taxable 225.
        assert body["subtotal"] == "1225.00"
        assert body["discount_amount"] == "25.00"
        assert body["total_amount"] == "1225.00"

    async def test_updating_item_quantity_updates_the_invoice_totals(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item = await _create_invoice_item(client, headers, invoice["id"], quantity="10", rate="100")
        assert item["line_total"] == "1000.00"

        await client.put(
            f"/api/v1/invoices/{invoice['id']}/items/{item['id']}",
            json={"quantity": "20"},
            headers=headers,
        )

        response = await client.get(f"/api/v1/invoices/{invoice['id']}", headers=headers)
        assert response.json()["subtotal"] == "2000.00"
        assert response.json()["total_amount"] == "2000.00"

    async def test_deleting_an_item_reduces_the_invoice_totals(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item_a = await _create_invoice_item(
            client, headers, invoice["id"], quantity="10", rate="100"
        )
        await _create_invoice_item(client, headers, invoice["id"], quantity="5", rate="50")

        before = await client.get(f"/api/v1/invoices/{invoice['id']}", headers=headers)
        assert before.json()["subtotal"] == "1250.00"

        await client.delete(
            f"/api/v1/invoices/{invoice['id']}/items/{item_a['id']}", headers=headers
        )

        after = await client.get(f"/api/v1/invoices/{invoice['id']}", headers=headers)
        assert after.json()["subtotal"] == "250.00"
        assert after.json()["total_amount"] == "250.00"

    async def test_updating_transport_charge_updates_total_without_touching_items(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        item = await _create_invoice_item(client, headers, invoice["id"], quantity="10", rate="100")

        response = await client.put(
            f"/api/v1/invoices/{invoice['id']}",
            json={"transport_charge": "75.00"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["subtotal"] == "1000.00"
        assert body["total_amount"] == "1075.00"

        items_response = await client.get(
            f"/api/v1/invoices/{invoice['id']}/items", headers=headers
        )
        assert items_response.json()[0]["id"] == item["id"]
        assert items_response.json()[0]["line_total"] == "1000.00"

    async def test_decimal_accuracy_avoids_float_rounding_error(self, client: AsyncClient) -> None:
        """0.1 * 0.2 == 0.020000000000000004 in float but exactly 0.02 in
        Decimal - proof the calculation survives the full JSON round-trip
        (request -> pydantic Decimal -> domain -> Postgres NUMERIC ->
        response) without ever touching float."""
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)

        item = await _create_invoice_item(
            client,
            headers,
            invoice["id"],
            quantity="0.100",
            rate="0.2000",
            unit="kg",
        )
        assert item["taxable_amount"] == "0.02"
        assert item["line_total"] == "0.02"

    async def test_half_up_rounding_is_applied_consistently(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)

        # gross = 2 * 0.625 = 1.25; discount = 1.25*50/100 = 0.625 exactly
        # -> HALF_UP rounds to 0.63, not 0.62.
        item = await _create_invoice_item(
            client,
            headers,
            invoice["id"],
            quantity="2",
            rate="0.6250",
            discount_percent="50",
            unit="kg",
        )
        assert item["discount_amount"] == "0.63"
        assert item["taxable_amount"] == "0.62"

    async def test_extreme_quantity_and_rate_is_a_clean_calculation_error(
        self, client: AsyncClient
    ) -> None:
        """quantity/rate are each within their own field's max_digits bound,
        but their product overflows what a NUMERIC(14,2) column can store -
        the server must reject this cleanly, never a raw 500."""
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        trip_catch = await _create_trip_catch(client, headers, quantity_caught="999999999.999")

        response = await client.post(
            f"/api/v1/invoices/{invoice['id']}/items",
            json={
                "trip_catch_id": trip_catch["id"],
                "fish_id": trip_catch["fish_id"],
                "quantity": "999999999.999",
                "unit": "kg",
                "rate": "99999999.9999",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVOICE_CALCULATION_ERROR"
