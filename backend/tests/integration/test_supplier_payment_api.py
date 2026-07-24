import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.purchase.constants import PurchaseStatus
from app.modules.purchase.models import PurchaseBill
from app.modules.supplier_payments.constants import SupplierPaymentStatus
from app.modules.supplier_payments.models import SupplierPayment, SupplierPaymentAllocation
from app.modules.suppliers.constants import SupplierStatus
from app.modules.suppliers.models import Supplier

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

# _create_supplier_payment provisions a fresh supplier via the API by
# default, so test users need supplier:create access too for that setup to
# succeed. _create_posted_purchase_bill (allocation tests) provisions and
# posts a purchase bill via the API too, so allocation test users need the
# full purchase:*/supplier:* chain for that setup to succeed.
_ALL_SUPPLIER_PAYMENT_PERMISSIONS = [
    "supplier_payment:view",
    "supplier_payment:create",
    "supplier_payment:edit",
    "supplier_payment:delete",
    "supplier:view",
    "supplier:create",
]
_ALL_ALLOCATION_PERMISSIONS = [
    *_ALL_SUPPLIER_PAYMENT_PERMISSIONS,
    "purchase:view",
    "purchase:create",
    "purchase:edit",
    "purchase:post",
]
_PAYMENT_DATE = "2026-07-23"
_BILL_DATE = "2026-07-22"


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
        "code": f"SPSUP-{uuid.uuid4().hex[:8]}",
        "name": f"Supplier {uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/suppliers", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _set_supplier_inactive(db_session: AsyncSession, supplier_id: str) -> None:
    """SupplierUpdateRequest has no `status` field at all in this session
    (status is server-owned) - there is no API path to deactivate a
    supplier yet, so tests that need an inactive supplier flip it directly
    via the DB. Mirrors test_purchase_api.py's own helper."""
    row = (
        await db_session.execute(select(Supplier).where(Supplier.id == uuid.UUID(supplier_id)))
    ).scalar_one()
    row.status = SupplierStatus.INACTIVE
    await db_session.commit()


async def _create_supplier_payment(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    supplier_id: str | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    if supplier_id is None:
        supplier_id = (await _create_supplier(client, headers))["id"]
    payload: dict[str, Any] = {
        "supplier_id": supplier_id,
        "payment_date": _PAYMENT_DATE,
        "payment_method": "cheque",
        "amount": "150000.00",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/supplier-payments", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_purchase_bill(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    supplier_id: str | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    if supplier_id is None:
        supplier_id = (await _create_supplier(client, headers))["id"]
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
        "quantity": "1500.000",
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


async def _create_posted_purchase_bill(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    supplier_id: str | None = None,
    quantity: str = "1500.000",
    rate: str = "100.0000",
) -> dict[str, Any]:
    """A fully posted purchase bill with a known balance_amount (quantity x
    rate, no tax/discount) - the default 1500 x 100 = 150000.00 matches
    _create_supplier_payment's default amount, so tests can allocate the
    full amount without doing the arithmetic themselves."""
    bill = await _create_purchase_bill(client, headers, supplier_id=supplier_id)
    await _add_purchase_bill_item(client, headers, bill["id"], quantity=quantity, rate=rate)
    posted = await client.post(f"/api/v1/purchase/{bill['id']}/post", headers=headers)
    assert posted.status_code == 200, posted.text
    result: dict[str, Any] = posted.json()
    return result


async def _create_supplier_payment_allocation(
    client: AsyncClient,
    headers: dict[str, str],
    supplier_payment_id: str,
    *,
    purchase_bill_id: str | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    if purchase_bill_id is None:
        purchase_bill_id = (await _create_posted_purchase_bill(client, headers))["id"]
    payload: dict[str, Any] = {"purchase_bill_id": purchase_bill_id, "allocated_amount": "100.00"}
    payload.update(overrides)
    response = await client.post(
        f"/api/v1/supplier-payments/{supplier_payment_id}/allocations",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


class TestCreateSupplierPayment:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/supplier-payments",
            json={
                "supplier_id": str(uuid.uuid4()),
                "payment_date": _PAYMENT_DATE,
                "payment_method": "cheque",
                "amount": "150000.00",
            },
        )
        assert response.status_code == 401

    async def test_requires_create_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["supplier_payment:view"])
        response = await client.post(
            "/api/v1/supplier-payments",
            json={
                "supplier_id": str(uuid.uuid4()),
                "payment_date": _PAYMENT_DATE,
                "payment_method": "cheque",
                "amount": "150000.00",
            },
            headers=headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_success_is_draft_with_server_owned_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        body = await _create_supplier_payment(
            client, headers, amount="150000.00", remarks="Against pending purchase bills"
        )

        assert body["status"] == "draft"
        assert body["payment_number"] is None
        assert body["posted_at"] is None
        assert body["amount"] == "150000.00"
        assert body["allocated_amount"] == "0.00"
        assert body["unallocated_amount"] == "150000.00"
        assert body["remarks"] == "Against pending purchase bills"
        assert body["created_at"] == body["updated_at"]

    async def test_success_sets_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        body = await _create_supplier_payment(client, headers)

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(
                select(SupplierPayment).where(SupplierPayment.id == uuid.UUID(body["id"]))
            )
        ).scalar_one()
        assert row.created_by == admin.id
        assert row.updated_by == admin.id
        assert row.tenant_id == admin.tenant_id

    async def test_server_owned_fields_in_the_request_are_ignored(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        supplier_id = (await _create_supplier(client, headers))["id"]
        response = await client.post(
            "/api/v1/supplier-payments",
            json={
                "supplier_id": supplier_id,
                "payment_date": _PAYMENT_DATE,
                "payment_method": "cheque",
                "amount": "150000.00",
                "payment_number": "SPAY-0001",
                "allocated_amount": "50000.00",
                "unallocated_amount": "50000.00",
                "status": "posted",
                "posted_at": "2026-07-23T04:00:00Z",
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["payment_number"] is None
        assert body["allocated_amount"] == "0.00"
        assert body["unallocated_amount"] == "150000.00"
        assert body["status"] == "draft"
        assert body["posted_at"] is None

    async def test_unknown_supplier_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/supplier-payments",
            json={
                "supplier_id": str(uuid.uuid4()),
                "payment_date": _PAYMENT_DATE,
                "payment_method": "cheque",
                "amount": "150000.00",
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_SUPPLIER_NOT_FOUND"

    async def test_inactive_supplier_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        await _set_supplier_inactive(db_session, supplier["id"])

        response = await client.post(
            "/api/v1/supplier-payments",
            json={
                "supplier_id": supplier["id"],
                "payment_date": _PAYMENT_DATE,
                "payment_method": "cheque",
                "amount": "150000.00",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_SUPPLIER_INACTIVE"

    async def test_missing_supplier_id_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/supplier-payments",
            json={
                "payment_date": _PAYMENT_DATE,
                "payment_method": "cheque",
                "amount": "150000.00",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "supplier_id" in response.json()["error"]["field_errors"]

    async def test_missing_amount_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        response = await client.post(
            "/api/v1/supplier-payments",
            json={
                "supplier_id": supplier["id"],
                "payment_date": _PAYMENT_DATE,
                "payment_method": "cheque",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "amount" in response.json()["error"]["field_errors"]

    async def test_zero_amount_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        response = await client.post(
            "/api/v1/supplier-payments",
            json={
                "supplier_id": supplier["id"],
                "payment_date": _PAYMENT_DATE,
                "payment_method": "cheque",
                "amount": "0",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "amount" in response.json()["error"]["field_errors"]

    async def test_negative_amount_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        response = await client.post(
            "/api/v1/supplier-payments",
            json={
                "supplier_id": supplier["id"],
                "payment_date": _PAYMENT_DATE,
                "payment_method": "cheque",
                "amount": "-1",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "amount" in response.json()["error"]["field_errors"]

    async def test_invalid_payment_method_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        response = await client.post(
            "/api/v1/supplier-payments",
            json={
                "supplier_id": supplier["id"],
                "payment_date": _PAYMENT_DATE,
                "payment_method": "bitcoin",
                "amount": "150000.00",
            },
            headers=headers,
        )
        assert response.status_code == 422

    async def test_cannot_use_another_tenants_supplier(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)

        other_tenant = Tenant(
            name="Foreign Supplier Payment Owner",
            slug=f"foreign-sp-supplier-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_SUPPLIER_PAYMENT_PERMISSIONS
        )
        foreign_supplier = await _create_supplier(client, other_headers)

        response = await client.post(
            "/api/v1/supplier-payments",
            json={
                "supplier_id": foreign_supplier["id"],
                "payment_date": _PAYMENT_DATE,
                "payment_method": "cheque",
                "amount": "150000.00",
            },
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_SUPPLIER_NOT_FOUND"


class TestGetSupplierPayment:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/supplier-payments/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(f"/api/v1/supplier-payments/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_returns_the_supplier_payment(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_supplier_payment(client, headers)
        response = await client.get(f"/api/v1/supplier-payments/{created['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(f"/api/v1/supplier-payments/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_NOT_FOUND"

    async def test_soft_deleted_supplier_payment_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_supplier_payment(client, headers)
        await client.delete(f"/api/v1/supplier-payments/{created['id']}", headers=headers)
        response = await client.get(f"/api/v1/supplier-payments/{created['id']}", headers=headers)
        assert response.status_code == 404

    async def test_other_tenants_supplier_payment_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_supplier_payment(client, headers)

        other_tenant = Tenant(
            name="Other Supplier Payment Co", slug=f"other-sp-payment-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_SUPPLIER_PAYMENT_PERMISSIONS
        )

        response = await client.get(
            f"/api/v1/supplier-payments/{created['id']}", headers=other_headers
        )
        assert response.status_code == 404


class TestListSupplierPayments:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/supplier-payments")
        assert response.status_code == 401

    async def test_default_response_shape(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_supplier_payment(client, headers)
        response = await client.get("/api/v1/supplier-payments", headers=headers)
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

    async def test_search_matches_supplier_name(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Search Supplier Payment Tenant", slug=f"search-sp-payment-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_SUPPLIER_PAYMENT_PERMISSIONS
        )

        marker = uuid.uuid4().hex[:8]
        matching_supplier = await _create_supplier(
            client, headers, name=f"Ocean Fresh Traders {marker}"
        )
        irrelevant_supplier = await _create_supplier(
            client, headers, name=f"Irrelevant Co {marker}"
        )
        target = await _create_supplier_payment(
            client, headers, supplier_id=matching_supplier["id"]
        )
        await _create_supplier_payment(client, headers, supplier_id=irrelevant_supplier["id"])

        response = await client.get(
            "/api/v1/supplier-payments",
            params={"q": f"ocean fresh traders {marker}"},
            headers=headers,
        )
        ids = [p["id"] for p in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_search_matches_reference_number(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Ref Search Supplier Payment Tenant",
            slug=f"ref-search-sp-payment-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_SUPPLIER_PAYMENT_PERMISSIONS
        )

        marker = uuid.uuid4().hex[:8]
        target = await _create_supplier_payment(client, headers, reference_number=f"REF-{marker}")
        await _create_supplier_payment(client, headers, reference_number="REF-IRRELEVANT")

        response = await client.get(
            "/api/v1/supplier-payments", params={"q": f"ref-{marker}"}, headers=headers
        )
        ids = [p["id"] for p in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_filters_by_supplier_id(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Supplier Filter Payment Tenant",
            slug=f"supplier-filter-sp-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_SUPPLIER_PAYMENT_PERMISSIONS
        )

        supplier_a = await _create_supplier(client, headers)
        supplier_b = await _create_supplier(client, headers)
        target = await _create_supplier_payment(client, headers, supplier_id=supplier_a["id"])
        await _create_supplier_payment(client, headers, supplier_id=supplier_b["id"])

        response = await client.get(
            "/api/v1/supplier-payments", params={"supplier_id": supplier_a["id"]}, headers=headers
        )
        ids = [p["id"] for p in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_filters_by_payment_method(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Method Filter Payment Tenant", slug=f"method-filter-sp-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_SUPPLIER_PAYMENT_PERMISSIONS
        )

        target = await _create_supplier_payment(client, headers, payment_method="upi")
        await _create_supplier_payment(client, headers, payment_method="cash")

        response = await client.get(
            "/api/v1/supplier-payments", params={"payment_method": "upi"}, headers=headers
        )
        ids = [p["id"] for p in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_filters_by_status(self, client: AsyncClient, db_session: AsyncSession) -> None:
        other_tenant = Tenant(
            name="Status Filter Payment Tenant", slug=f"status-filter-sp-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_SUPPLIER_PAYMENT_PERMISSIONS
        )

        target = await _create_supplier_payment(client, headers)

        response = await client.get(
            "/api/v1/supplier-payments", params={"status": "draft"}, headers=headers
        )
        ids = [p["id"] for p in response.json()["data"]]
        assert ids == [target["id"]]

        response_posted = await client.get(
            "/api/v1/supplier-payments", params={"status": "posted"}, headers=headers
        )
        assert response_posted.json()["data"] == []

    async def test_filters_by_payment_date_range(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Date Filter Payment Tenant", slug=f"date-filter-sp-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_SUPPLIER_PAYMENT_PERMISSIONS
        )

        in_range = await _create_supplier_payment(client, headers, payment_date="2026-06-05")
        await _create_supplier_payment(client, headers, payment_date="2099-01-01")

        response = await client.get(
            "/api/v1/supplier-payments",
            params={"payment_date_from": "2026-06-01", "payment_date_to": "2026-06-30"},
            headers=headers,
        )
        ids = [p["id"] for p in response.json()["data"]]
        assert ids == [in_range["id"]]

    async def test_sort_ascending_and_descending_by_payment_date(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Sort Date Payment Tenant", slug=f"sort-date-sp-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_SUPPLIER_PAYMENT_PERMISSIONS
        )

        supplier_id = (await _create_supplier(client, headers))["id"]
        earlier = await _create_supplier_payment(
            client, headers, supplier_id=supplier_id, payment_date="2026-01-01"
        )
        later = await _create_supplier_payment(
            client, headers, supplier_id=supplier_id, payment_date="2026-12-31"
        )

        asc = await client.get(
            "/api/v1/supplier-payments", params={"sort": "payment_date"}, headers=headers
        )
        assert [p["id"] for p in asc.json()["data"]] == [earlier["id"], later["id"]]

        desc = await client.get(
            "/api/v1/supplier-payments", params={"sort": "-payment_date"}, headers=headers
        )
        assert [p["id"] for p in desc.json()["data"]] == [later["id"], earlier["id"]]

    async def test_invalid_sort_field_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/supplier-payments", params={"sort": "amount"}, headers=headers
        )
        assert response.status_code == 422

    async def test_default_sort_is_most_recent_first(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Default Sort Payment Tenant", slug=f"default-sort-sp-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_SUPPLIER_PAYMENT_PERMISSIONS
        )

        first = await _create_supplier_payment(client, headers)
        second = await _create_supplier_payment(client, headers)

        response = await client.get("/api/v1/supplier-payments", headers=headers)
        ids = [p["id"] for p in response.json()["data"]]
        assert ids == [second["id"], first["id"]]

    async def test_pagination_meta_is_correct(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Pagination Payment Tenant", slug=f"pagination-sp-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_SUPPLIER_PAYMENT_PERMISSIONS
        )

        for _ in range(3):
            await _create_supplier_payment(client, headers)

        response = await client.get(
            "/api/v1/supplier-payments", params={"page": 1, "page_size": 2}, headers=headers
        )
        meta = response.json()["meta"]
        assert meta["total_records"] == 3
        assert meta["total_pages"] == 2
        assert meta["current_page"] == 1
        assert meta["page_size"] == 2
        assert meta["has_next"] is True
        assert meta["has_previous"] is False

        page2 = await client.get(
            "/api/v1/supplier-payments", params={"page": 2, "page_size": 2}, headers=headers
        )
        meta2 = page2.json()["meta"]
        assert meta2["has_next"] is False
        assert meta2["has_previous"] is True
        assert len(page2.json()["data"]) == 1

    async def test_invalid_page_size_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/supplier-payments", params={"page_size": 101}, headers=headers
        )
        assert response.status_code == 422

    async def test_deleted_supplier_payments_are_excluded(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Fresh List Payment Tenant", slug=f"fresh-sp-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        isolated_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_SUPPLIER_PAYMENT_PERMISSIONS
        )

        created = await _create_supplier_payment(client, isolated_headers)
        await client.delete(f"/api/v1/supplier-payments/{created['id']}", headers=isolated_headers)

        response = await client.get("/api/v1/supplier-payments", headers=isolated_headers)
        assert response.json()["data"] == []
        assert response.json()["meta"]["total_records"] == 0

    async def test_tenant_isolation_returns_only_own_supplier_payments(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        await _create_supplier_payment(client, headers)

        other_tenant = Tenant(
            name="Isolated Supplier Payment Co", slug=f"isolated-sp-payment-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_SUPPLIER_PAYMENT_PERMISSIONS
        )

        response = await client.get("/api/v1/supplier-payments", headers=other_headers)
        assert response.json()["data"] == []


class TestUpdateSupplierPayment:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.put(
            f"/api/v1/supplier-payments/{uuid.uuid4()}", json={"remarks": "x"}
        )
        assert response.status_code == 401

    async def test_requires_edit_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["supplier_payment:view"])
        response = await client.put(
            f"/api/v1/supplier-payments/{uuid.uuid4()}", json={"remarks": "x"}, headers=headers
        )
        assert response.status_code == 403

    async def test_partial_update_only_changes_supplied_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_supplier_payment(
            client, headers, remarks="Original", bank_name="Bank A"
        )

        response = await client.put(
            f"/api/v1/supplier-payments/{created['id']}",
            json={"bank_name": "Bank B"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["bank_name"] == "Bank B"
        assert body["remarks"] == "Original"

    async def test_amount_change_recomputes_unallocated_amount(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_supplier_payment(client, headers, amount="150000.00")
        assert created["unallocated_amount"] == "150000.00"

        response = await client.put(
            f"/api/v1/supplier-payments/{created['id']}",
            json={"amount": "225000.00"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["amount"] == "225000.00"
        assert body["unallocated_amount"] == "225000.00"
        assert body["allocated_amount"] == "0.00"

    async def test_reassign_supplier_to_unknown_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_supplier_payment(client, headers)

        response = await client.put(
            f"/api/v1/supplier-payments/{created['id']}",
            json={"supplier_id": str(uuid.uuid4())},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_SUPPLIER_NOT_FOUND"

    async def test_reassign_supplier_to_inactive_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_supplier_payment(client, headers)
        inactive_supplier = await _create_supplier(client, headers)
        await _set_supplier_inactive(db_session, inactive_supplier["id"])

        response = await client.put(
            f"/api/v1/supplier-payments/{created['id']}",
            json={"supplier_id": inactive_supplier["id"]},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_SUPPLIER_INACTIVE"

    async def test_server_owned_fields_in_the_request_are_ignored(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_supplier_payment(client, headers)

        response = await client.put(
            f"/api/v1/supplier-payments/{created['id']}",
            json={
                "payment_number": "SPAY-0001",
                "allocated_amount": "50000.00",
                "unallocated_amount": "9999.00",
                "status": "posted",
                "posted_at": "2026-07-23T04:00:00Z",
            },
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["payment_number"] is None
        assert body["allocated_amount"] == "0.00"
        assert body["status"] == "draft"
        assert body["posted_at"] is None

    async def test_update_bumps_updated_at_and_sets_updated_by(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_supplier_payment(client, headers)

        response = await client.put(
            f"/api/v1/supplier-payments/{created['id']}",
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
            await db_session.execute(
                select(SupplierPayment).where(SupplierPayment.id == uuid.UUID(created["id"]))
            )
        ).scalar_one()
        assert row.updated_by == admin.id

    async def test_cannot_update_another_tenants_supplier_payment(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_supplier_payment(client, headers)

        other_tenant = Tenant(
            name="Other Supplier Payment Updater", slug=f"other-sp-upd-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_SUPPLIER_PAYMENT_PERMISSIONS
        )

        response = await client.put(
            f"/api/v1/supplier-payments/{created['id']}",
            json={"remarks": "Hijacked"},
            headers=other_headers,
        )
        assert response.status_code == 404

        unchanged = await client.get(f"/api/v1/supplier-payments/{created['id']}", headers=headers)
        assert unchanged.json()["remarks"] is None

    async def test_cannot_update_a_deleted_supplier_payment(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_supplier_payment(client, headers)
        await client.delete(f"/api/v1/supplier-payments/{created['id']}", headers=headers)

        response = await client.put(
            f"/api/v1/supplier-payments/{created['id']}",
            json={"remarks": "Should Not Apply"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_NOT_FOUND"

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            f"/api/v1/supplier-payments/{uuid.uuid4()}", json={"remarks": "x"}, headers=headers
        )
        assert response.status_code == 404

    async def test_non_draft_supplier_payment_cannot_be_updated(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_supplier_payment(client, headers)

        row = (
            await db_session.execute(
                select(SupplierPayment).where(SupplierPayment.id == uuid.UUID(created["id"]))
            )
        ).scalar_one()
        row.status = SupplierPaymentStatus.POSTED
        await db_session.commit()

        response = await client.put(
            f"/api/v1/supplier-payments/{created['id']}",
            json={"remarks": "Should not apply"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_NOT_DRAFT"


class TestDeleteSupplierPayment:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.delete(f"/api/v1/supplier-payments/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_delete_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(
            db_session, tenant_id, ["supplier_payment:view", "supplier_payment:edit"]
        )
        response = await client.delete(f"/api/v1/supplier-payments/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_success_soft_deletes_and_sets_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_supplier_payment(client, headers)

        response = await client.delete(
            f"/api/v1/supplier-payments/{created['id']}", headers=headers
        )
        assert response.status_code == 204
        assert response.content == b""

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(
                select(SupplierPayment).where(SupplierPayment.id == uuid.UUID(created["id"]))
            )
        ).scalar_one()
        assert row.deleted_at is not None
        assert row.deleted_by == admin.id

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.delete(f"/api/v1/supplier-payments/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404

    async def test_deleting_twice_is_404_the_second_time(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_supplier_payment(client, headers)
        first = await client.delete(f"/api/v1/supplier-payments/{created['id']}", headers=headers)
        second = await client.delete(f"/api/v1/supplier-payments/{created['id']}", headers=headers)
        assert first.status_code == 204
        assert second.status_code == 404

    async def test_cannot_delete_another_tenants_supplier_payment(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_supplier_payment(client, headers)

        other_tenant = Tenant(
            name="Other Supplier Payment Deleter", slug=f"other-sp-del-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_SUPPLIER_PAYMENT_PERMISSIONS
        )

        response = await client.delete(
            f"/api/v1/supplier-payments/{created['id']}", headers=other_headers
        )
        assert response.status_code == 404

        still_there = await client.get(
            f"/api/v1/supplier-payments/{created['id']}", headers=headers
        )
        assert still_there.status_code == 200

    async def test_non_draft_supplier_payment_cannot_be_deleted(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_supplier_payment(client, headers)

        row = (
            await db_session.execute(
                select(SupplierPayment).where(SupplierPayment.id == uuid.UUID(created["id"]))
            )
        ).scalar_one()
        row.status = SupplierPaymentStatus.CANCELLED
        await db_session.commit()

        response = await client.delete(
            f"/api/v1/supplier-payments/{created['id']}", headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_NOT_DRAFT"


class TestCreateSupplierPaymentAllocation:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            f"/api/v1/supplier-payments/{uuid.uuid4()}/allocations",
            json={"purchase_bill_id": str(uuid.uuid4()), "allocated_amount": "100.00"},
        )
        assert response.status_code == 401

    async def test_requires_create_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["supplier_payment:view"])
        response = await client.post(
            f"/api/v1/supplier-payments/{uuid.uuid4()}/allocations",
            json={"purchase_bill_id": str(uuid.uuid4()), "allocated_amount": "100.00"},
            headers=headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_success_recalculates_payment_totals(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Alloc Create Tenant", slug=f"sp-alloc-create-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_ALLOCATION_PERMISSIONS)

        payment = await _create_supplier_payment(client, headers, amount="1000.00")
        bill = await _create_posted_purchase_bill(
            client, headers, quantity="10.000", rate="100.0000"
        )
        assert bill["balance_amount"] == "1000.00"

        body = await _create_supplier_payment_allocation(
            client, headers, payment["id"], purchase_bill_id=bill["id"], allocated_amount="600.00"
        )
        assert body["supplier_payment_id"] == payment["id"]
        assert body["purchase_bill_id"] == bill["id"]
        assert body["allocated_amount"] == "600.00"

        pay_after = await client.get(f"/api/v1/supplier-payments/{payment['id']}", headers=headers)
        assert pay_after.json()["allocated_amount"] == "600.00"
        assert pay_after.json()["unallocated_amount"] == "400.00"

    async def test_success_sets_created_by(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Alloc Audit Tenant", slug=f"sp-alloc-audit-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_ALLOCATION_PERMISSIONS)
        user = (
            await db_session.execute(select(User).where(User.tenant_id == other_tenant.id))
        ).scalar_one()

        payment = await _create_supplier_payment(client, headers, amount="1000.00")
        body = await _create_supplier_payment_allocation(
            client, headers, payment["id"], allocated_amount="100.00"
        )

        row = (
            await db_session.execute(
                select(SupplierPaymentAllocation).where(
                    SupplierPaymentAllocation.id == uuid.UUID(body["id"])
                )
            )
        ).scalar_one()
        assert row.created_by == user.id
        assert row.tenant_id == user.tenant_id

    async def test_supports_multiple_allocations_on_one_payment(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Multi Alloc Tenant", slug=f"sp-multi-alloc-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_ALLOCATION_PERMISSIONS)

        payment = await _create_supplier_payment(client, headers, amount="1000.00")
        bill_a = await _create_posted_purchase_bill(
            client, headers, quantity="10.000", rate="100.0000"
        )
        bill_b = await _create_posted_purchase_bill(
            client, headers, quantity="10.000", rate="100.0000"
        )

        await _create_supplier_payment_allocation(
            client, headers, payment["id"], purchase_bill_id=bill_a["id"], allocated_amount="300.00"
        )
        await _create_supplier_payment_allocation(
            client, headers, payment["id"], purchase_bill_id=bill_b["id"], allocated_amount="400.00"
        )

        pay_after = await client.get(f"/api/v1/supplier-payments/{payment['id']}", headers=headers)
        assert pay_after.json()["allocated_amount"] == "700.00"
        assert pay_after.json()["unallocated_amount"] == "300.00"

        listed = await client.get(
            f"/api/v1/supplier-payments/{payment['id']}/allocations", headers=headers
        )
        assert len(listed.json()) == 2

    async def test_supports_one_purchase_bill_allocated_from_many_payments(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Shared Bill Alloc Tenant", slug=f"sp-shared-bill-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_ALLOCATION_PERMISSIONS)

        bill = await _create_posted_purchase_bill(client, headers)
        payment_a = await _create_supplier_payment(client, headers, amount="60000.00")
        payment_b = await _create_supplier_payment(client, headers, amount="90000.00")

        await _create_supplier_payment_allocation(
            client,
            headers,
            payment_a["id"],
            purchase_bill_id=bill["id"],
            allocated_amount="60000.00",
        )
        await _create_supplier_payment_allocation(
            client,
            headers,
            payment_b["id"],
            purchase_bill_id=bill["id"],
            allocated_amount="90000.00",
        )

        listed_a = await client.get(
            f"/api/v1/supplier-payments/{payment_a['id']}/allocations", headers=headers
        )
        listed_b = await client.get(
            f"/api/v1/supplier-payments/{payment_b['id']}/allocations", headers=headers
        )
        assert len(listed_a.json()) == 1
        assert len(listed_b.json()) == 1

    async def test_partial_allocation_leaves_the_rest_unallocated(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Partial Alloc Tenant", slug=f"sp-partial-alloc-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_ALLOCATION_PERMISSIONS)

        payment = await _create_supplier_payment(client, headers, amount="150000.00")
        await _create_supplier_payment_allocation(
            client, headers, payment["id"], allocated_amount="50000.00"
        )

        pay_after = await client.get(f"/api/v1/supplier-payments/{payment['id']}", headers=headers)
        assert pay_after.json()["allocated_amount"] == "50000.00"
        assert pay_after.json()["unallocated_amount"] == "100000.00"
        assert pay_after.json()["status"] == "draft"

    async def test_unknown_supplier_payment_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            f"/api/v1/supplier-payments/{uuid.uuid4()}/allocations",
            json={"purchase_bill_id": str(uuid.uuid4()), "allocated_amount": "100.00"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_NOT_FOUND"

    async def test_unknown_purchase_bill_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers)
        response = await client.post(
            f"/api/v1/supplier-payments/{payment['id']}/allocations",
            json={"purchase_bill_id": str(uuid.uuid4()), "allocated_amount": "100.00"},
            headers=headers,
        )
        assert response.status_code == 404
        assert (
            response.json()["error"]["code"]
            == "SUPPLIER_PAYMENT_ALLOCATION_PURCHASE_BILL_NOT_FOUND"
        )

    async def test_draft_purchase_bill_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers)
        draft_bill = await _create_purchase_bill(client, headers)

        response = await client.post(
            f"/api/v1/supplier-payments/{payment['id']}/allocations",
            json={"purchase_bill_id": draft_bill["id"], "allocated_amount": "100.00"},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_PURCHASE_BILL_NOT_ALLOCATABLE"

    async def test_cancelled_purchase_bill_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers)
        bill = await _create_posted_purchase_bill(client, headers)

        row = (
            await db_session.execute(
                select(PurchaseBill).where(PurchaseBill.id == uuid.UUID(bill["id"]))
            )
        ).scalar_one()
        row.status = PurchaseStatus.CANCELLED
        await db_session.commit()

        response = await client.post(
            f"/api/v1/supplier-payments/{payment['id']}/allocations",
            json={"purchase_bill_id": bill["id"], "allocated_amount": "100.00"},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_PURCHASE_BILL_NOT_ALLOCATABLE"

    async def test_amount_exceeding_purchase_bill_balance_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers, amount="5000.00")
        bill = await _create_posted_purchase_bill(
            client, headers, quantity="10.000", rate="100.0000"
        )  # balance 1000.00

        response = await client.post(
            f"/api/v1/supplier-payments/{payment['id']}/allocations",
            json={"purchase_bill_id": bill["id"], "allocated_amount": "1000.01"},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_ALLOCATION_AMOUNT_EXCEEDED"

    async def test_amount_exceeding_payment_unallocated_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers, amount="500.00")
        bill = await _create_posted_purchase_bill(
            client, headers, quantity="1000.000", rate="100.0000"
        )  # balance 100000.00

        response = await client.post(
            f"/api/v1/supplier-payments/{payment['id']}/allocations",
            json={"purchase_bill_id": bill["id"], "allocated_amount": "500.01"},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_ALLOCATION_AMOUNT_EXCEEDED"

    async def test_amount_exactly_equal_to_balance_and_unallocated_is_allowed(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers, amount="150000.00")
        bill = await _create_posted_purchase_bill(client, headers)  # balance 150000.00

        body = await _create_supplier_payment_allocation(
            client,
            headers,
            payment["id"],
            purchase_bill_id=bill["id"],
            allocated_amount="150000.00",
        )
        assert body["allocated_amount"] == "150000.00"

        pay_after = await client.get(f"/api/v1/supplier-payments/{payment['id']}", headers=headers)
        assert pay_after.json()["unallocated_amount"] == "0.00"

    async def test_zero_allocated_amount_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers)
        bill = await _create_posted_purchase_bill(client, headers)

        response = await client.post(
            f"/api/v1/supplier-payments/{payment['id']}/allocations",
            json={"purchase_bill_id": bill["id"], "allocated_amount": "0"},
            headers=headers,
        )
        assert response.status_code == 422
        assert "allocated_amount" in response.json()["error"]["field_errors"]

    async def test_non_draft_supplier_payment_is_409(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers)
        bill = await _create_posted_purchase_bill(client, headers)

        row = (
            await db_session.execute(
                select(SupplierPayment).where(SupplierPayment.id == uuid.UUID(payment["id"]))
            )
        ).scalar_one()
        row.status = SupplierPaymentStatus.POSTED
        await db_session.commit()

        response = await client.post(
            f"/api/v1/supplier-payments/{payment['id']}/allocations",
            json={"purchase_bill_id": bill["id"], "allocated_amount": "100.00"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT"

    async def test_cannot_use_another_tenants_purchase_bill(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers)

        other_tenant = Tenant(
            name="Foreign Bill For Alloc", slug=f"sp-foreign-bill-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_ALLOCATION_PERMISSIONS
        )
        foreign_bill = await _create_posted_purchase_bill(client, other_headers)

        response = await client.post(
            f"/api/v1/supplier-payments/{payment['id']}/allocations",
            json={"purchase_bill_id": foreign_bill["id"], "allocated_amount": "100.00"},
            headers=headers,
        )
        assert response.status_code == 404
        assert (
            response.json()["error"]["code"]
            == "SUPPLIER_PAYMENT_ALLOCATION_PURCHASE_BILL_NOT_FOUND"
        )

    async def test_duplicate_allocation_against_same_purchase_bill_is_conflict(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers, amount="150000.00")
        bill = await _create_posted_purchase_bill(client, headers)

        await _create_supplier_payment_allocation(
            client, headers, payment["id"], purchase_bill_id=bill["id"], allocated_amount="100.00"
        )
        # A second, small allocation against the same purchase bill from the
        # same payment stays within both amount ceilings, so it reaches the
        # DB and trips the unique(supplier_payment_id, purchase_bill_id)
        # constraint.
        response = await client.post(
            f"/api/v1/supplier-payments/{payment['id']}/allocations",
            json={"purchase_bill_id": bill["id"], "allocated_amount": "50.00"},
            headers=headers,
        )
        assert response.status_code == 409


class TestListSupplierPaymentAllocations:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/supplier-payments/{uuid.uuid4()}/allocations")
        assert response.status_code == 401

    async def test_requires_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(
            f"/api/v1/supplier-payments/{uuid.uuid4()}/allocations", headers=headers
        )
        assert response.status_code == 403

    async def test_unknown_supplier_payment_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/supplier-payments/{uuid.uuid4()}/allocations", headers=headers
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_NOT_FOUND"

    async def test_returns_allocations_oldest_first(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers, amount="1000.00")
        first = await _create_supplier_payment_allocation(
            client, headers, payment["id"], allocated_amount="300.00"
        )
        second = await _create_supplier_payment_allocation(
            client, headers, payment["id"], allocated_amount="300.00"
        )

        response = await client.get(
            f"/api/v1/supplier-payments/{payment['id']}/allocations", headers=headers
        )
        assert response.status_code == 200
        assert [a["id"] for a in response.json()] == [first["id"], second["id"]]

    async def test_empty_when_no_allocations(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers)
        response = await client.get(
            f"/api/v1/supplier-payments/{payment['id']}/allocations", headers=headers
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_allowed_regardless_of_payment_status(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers)

        row = (
            await db_session.execute(
                select(SupplierPayment).where(SupplierPayment.id == uuid.UUID(payment["id"]))
            )
        ).scalar_one()
        row.status = SupplierPaymentStatus.POSTED
        await db_session.commit()

        response = await client.get(
            f"/api/v1/supplier-payments/{payment['id']}/allocations", headers=headers
        )
        assert response.status_code == 200

    async def test_cannot_use_another_tenants_supplier_payment(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers)

        other_tenant = Tenant(
            name="Foreign Payment For Alloc List", slug=f"sp-foreign-list-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_ALLOCATION_PERMISSIONS
        )

        response = await client.get(
            f"/api/v1/supplier-payments/{payment['id']}/allocations", headers=other_headers
        )
        assert response.status_code == 404


class TestUpdateSupplierPaymentAllocation:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.put(
            f"/api/v1/supplier-payments/{uuid.uuid4()}/allocations/{uuid.uuid4()}",
            json={"allocated_amount": "50.00"},
        )
        assert response.status_code == 401

    async def test_requires_edit_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["supplier_payment:view"])
        response = await client.put(
            f"/api/v1/supplier-payments/{uuid.uuid4()}/allocations/{uuid.uuid4()}",
            json={"allocated_amount": "50.00"},
            headers=headers,
        )
        assert response.status_code == 403

    async def test_amount_change_recalculates_payment_totals(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers, amount="1000.00")
        allocation = await _create_supplier_payment_allocation(
            client, headers, payment["id"], allocated_amount="300.00"
        )

        response = await client.put(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            json={"allocated_amount": "500.00"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["allocated_amount"] == "500.00"

        pay_after = await client.get(f"/api/v1/supplier-payments/{payment['id']}", headers=headers)
        assert pay_after.json()["allocated_amount"] == "500.00"
        assert pay_after.json()["unallocated_amount"] == "500.00"

    async def test_can_increase_up_to_its_own_previous_amount_plus_unallocated(
        self, client: AsyncClient
    ) -> None:
        """Regression guard for the update-time ceiling: the allocation's
        own prior amount must be added back to unallocated_amount before
        validating the new amount (see
        SupplierPaymentService.update_allocation) - otherwise a
        same-or-larger reallocation of an existing allocation would
        incorrectly appear to exceed the payment's unallocated_amount."""
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers, amount="1000.00")
        bill = await _create_posted_purchase_bill(
            client, headers, quantity="1000.000", rate="100.0000"
        )  # balance 100000.00
        allocation = await _create_supplier_payment_allocation(
            client, headers, payment["id"], purchase_bill_id=bill["id"], allocated_amount="1000.00"
        )

        response = await client.put(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            json={"allocated_amount": "1000.00"},
            headers=headers,
        )
        assert response.status_code == 200

    async def test_reassign_purchase_bill_to_unknown_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers)
        allocation = await _create_supplier_payment_allocation(client, headers, payment["id"])

        response = await client.put(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            json={"purchase_bill_id": str(uuid.uuid4())},
            headers=headers,
        )
        assert response.status_code == 404
        assert (
            response.json()["error"]["code"]
            == "SUPPLIER_PAYMENT_ALLOCATION_PURCHASE_BILL_NOT_FOUND"
        )

    async def test_reassign_purchase_bill_to_draft_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers)
        allocation = await _create_supplier_payment_allocation(client, headers, payment["id"])
        draft_bill = await _create_purchase_bill(client, headers)

        response = await client.put(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            json={"purchase_bill_id": draft_bill["id"]},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_PURCHASE_BILL_NOT_ALLOCATABLE"

    async def test_amount_exceeding_purchase_bill_balance_is_422(self, client: AsyncClient) -> None:
        """Unlike the customer-payment equivalent, PurchaseBill.balance_amount
        is never reduced by an allocation in this session (Session 4's job -
        TASKS.md: "Do not update Purchase Bill financials yet"), so the
        effective ceiling on update is the bill's *original, static*
        balance_amount plus this allocation's own prior amount (added back -
        see SupplierPaymentService.update_allocation's docstring), not a
        balance that has already been decremented by a prior allocation."""
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers, amount="100000.00")
        bill = await _create_posted_purchase_bill(
            client, headers, quantity="10.000", rate="100.0000"
        )  # balance 1000.00, stays 1000.00 forever this session
        allocation = await _create_supplier_payment_allocation(
            client, headers, payment["id"], purchase_bill_id=bill["id"], allocated_amount="100.00"
        )

        response = await client.put(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            json={"allocated_amount": "1100.01"},  # > 1000.00 balance + 100.00 added back
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_ALLOCATION_AMOUNT_EXCEEDED"

    async def test_amount_exceeding_payment_unallocated_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers, amount="1000.00")
        bill = await _create_posted_purchase_bill(
            client, headers, quantity="1000.000", rate="100.0000"
        )  # balance 100000.00
        other_bill = await _create_posted_purchase_bill(
            client, headers, quantity="1000.000", rate="100.0000"
        )
        allocation = await _create_supplier_payment_allocation(
            client, headers, payment["id"], purchase_bill_id=bill["id"], allocated_amount="300.00"
        )
        # Consume the rest of the payment's unallocated_amount with a second
        # allocation against a different purchase bill.
        await _create_supplier_payment_allocation(
            client,
            headers,
            payment["id"],
            purchase_bill_id=other_bill["id"],
            allocated_amount="700.00",
        )

        response = await client.put(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            json={"allocated_amount": "300.01"},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_ALLOCATION_AMOUNT_EXCEEDED"

    async def test_unknown_allocation_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers)
        response = await client.put(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{uuid.uuid4()}",
            json={"allocated_amount": "50.00"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_ALLOCATION_NOT_FOUND"

    async def test_unknown_supplier_payment_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            f"/api/v1/supplier-payments/{uuid.uuid4()}/allocations/{uuid.uuid4()}",
            json={"allocated_amount": "50.00"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_NOT_FOUND"

    async def test_non_draft_supplier_payment_is_409(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers, amount="1000.00")
        allocation = await _create_supplier_payment_allocation(
            client, headers, payment["id"], allocated_amount="300.00"
        )

        row = (
            await db_session.execute(
                select(SupplierPayment).where(SupplierPayment.id == uuid.UUID(payment["id"]))
            )
        ).scalar_one()
        row.status = SupplierPaymentStatus.POSTED
        await db_session.commit()

        response = await client.put(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            json={"allocated_amount": "100.00"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT"

    async def test_cannot_update_another_tenants_allocation(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers, amount="1000.00")
        allocation = await _create_supplier_payment_allocation(
            client, headers, payment["id"], allocated_amount="300.00"
        )

        other_tenant = Tenant(
            name="Other Alloc Updater", slug=f"sp-other-alloc-upd-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_ALLOCATION_PERMISSIONS
        )

        response = await client.put(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            json={"allocated_amount": "50.00"},
            headers=other_headers,
        )
        assert response.status_code == 404


class TestDeleteSupplierPaymentAllocation:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.delete(
            f"/api/v1/supplier-payments/{uuid.uuid4()}/allocations/{uuid.uuid4()}"
        )
        assert response.status_code == 401

    async def test_requires_delete_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(
            db_session, tenant_id, ["supplier_payment:view", "supplier_payment:edit"]
        )
        response = await client.delete(
            f"/api/v1/supplier-payments/{uuid.uuid4()}/allocations/{uuid.uuid4()}",
            headers=headers,
        )
        assert response.status_code == 403

    async def test_success_hard_deletes_and_restores_unallocated_amount(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers, amount="1000.00")
        allocation = await _create_supplier_payment_allocation(
            client, headers, payment["id"], allocated_amount="400.00"
        )

        pay_mid = await client.get(f"/api/v1/supplier-payments/{payment['id']}", headers=headers)
        assert pay_mid.json()["unallocated_amount"] == "600.00"

        response = await client.delete(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            headers=headers,
        )
        assert response.status_code == 204
        assert response.content == b""

        row = (
            await db_session.execute(
                select(SupplierPaymentAllocation).where(
                    SupplierPaymentAllocation.id == uuid.UUID(allocation["id"])
                )
            )
        ).scalar_one_or_none()
        assert row is None  # hard-deleted, not soft-deleted

        pay_after = await client.get(f"/api/v1/supplier-payments/{payment['id']}", headers=headers)
        assert pay_after.json()["allocated_amount"] == "0.00"
        assert pay_after.json()["unallocated_amount"] == "1000.00"

    async def test_unknown_allocation_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers)
        response = await client.delete(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{uuid.uuid4()}",
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_ALLOCATION_NOT_FOUND"

    async def test_unknown_supplier_payment_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.delete(
            f"/api/v1/supplier-payments/{uuid.uuid4()}/allocations/{uuid.uuid4()}",
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_NOT_FOUND"

    async def test_deleting_twice_is_404_the_second_time(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers)
        allocation = await _create_supplier_payment_allocation(client, headers, payment["id"])

        first = await client.delete(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            headers=headers,
        )
        second = await client.delete(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            headers=headers,
        )
        assert first.status_code == 204
        assert second.status_code == 404

    async def test_non_draft_supplier_payment_is_409(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers)
        allocation = await _create_supplier_payment_allocation(client, headers, payment["id"])

        row = (
            await db_session.execute(
                select(SupplierPayment).where(SupplierPayment.id == uuid.UUID(payment["id"]))
            )
        ).scalar_one()
        row.status = SupplierPaymentStatus.POSTED
        await db_session.commit()

        response = await client.delete(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT"

    async def test_cannot_delete_another_tenants_allocation(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _create_supplier_payment(client, headers)
        allocation = await _create_supplier_payment_allocation(client, headers, payment["id"])

        other_tenant = Tenant(
            name="Other Alloc Deleter", slug=f"sp-other-alloc-del-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_ALLOCATION_PERMISSIONS
        )

        response = await client.delete(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            headers=other_headers,
        )
        assert response.status_code == 404

        still_there = await client.get(
            f"/api/v1/supplier-payments/{payment['id']}/allocations", headers=headers
        )
        assert len(still_there.json()) == 1


_ALL_POST_PERMISSIONS = [*_ALL_ALLOCATION_PERMISSIONS, "supplier_payment:post"]


class TestPostSupplierPayment:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(f"/api/v1/supplier-payments/{uuid.uuid4()}/post")
        assert response.status_code == 401

    async def test_requires_post_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, _ALL_ALLOCATION_PERMISSIONS)
        response = await client.post(
            f"/api/v1/supplier-payments/{uuid.uuid4()}/post", headers=headers
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_view_only_permission_is_not_enough(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["supplier_payment:view"])
        response = await client.post(
            f"/api/v1/supplier-payments/{uuid.uuid4()}/post", headers=headers
        )
        assert response.status_code == 403

    async def test_success_posts_and_assigns_a_payment_number(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Post Success Tenant", slug=f"sp-post-success-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_POST_PERMISSIONS)

        bill = await _create_posted_purchase_bill(client, headers)
        payment = await _create_supplier_payment(client, headers, amount="150000.00")
        await _create_supplier_payment_allocation(
            client,
            headers,
            payment["id"],
            purchase_bill_id=bill["id"],
            allocated_amount="150000.00",
        )

        response = await client.post(
            f"/api/v1/supplier-payments/{payment['id']}/post", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "posted"
        assert body["payment_number"] == "SPAY/2026-27/00001"
        assert body["allocated_amount"] == "150000.00"
        assert body["unallocated_amount"] == "0.00"
        assert body["posted_at"] is not None

    async def test_double_post_is_409(self, client: AsyncClient, db_session: AsyncSession) -> None:
        other_tenant = Tenant(
            name="Post Double Tenant", slug=f"sp-post-double-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_POST_PERMISSIONS)

        bill = await _create_posted_purchase_bill(client, headers)
        payment = await _create_supplier_payment(client, headers, amount="150000.00")
        await _create_supplier_payment_allocation(
            client,
            headers,
            payment["id"],
            purchase_bill_id=bill["id"],
            allocated_amount="150000.00",
        )
        first = await client.post(
            f"/api/v1/supplier-payments/{payment['id']}/post", headers=headers
        )
        assert first.status_code == 200, first.text

        second = await client.post(
            f"/api/v1/supplier-payments/{payment['id']}/post", headers=headers
        )
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "SUPPLIER_PAYMENT_NOT_DRAFT"

    async def test_posting_a_cancelled_payment_is_409(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Post Cancelled Tenant", slug=f"sp-post-cancelled-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_POST_PERMISSIONS)

        payment = await _create_supplier_payment(client, headers, amount="150000.00")
        row = (
            await db_session.execute(
                select(SupplierPayment).where(SupplierPayment.id == uuid.UUID(payment["id"]))
            )
        ).scalar_one()
        row.status = SupplierPaymentStatus.CANCELLED
        await db_session.commit()

        response = await client.post(
            f"/api/v1/supplier-payments/{payment['id']}/post", headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_NOT_DRAFT"

    async def test_posting_with_no_allocations_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Post No Alloc Tenant", slug=f"sp-post-no-alloc-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_POST_PERMISSIONS)

        payment = await _create_supplier_payment(client, headers, amount="150000.00")

        response = await client.post(
            f"/api/v1/supplier-payments/{payment['id']}/post", headers=headers
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_NO_ALLOCATIONS"

    async def test_posting_unknown_payment_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, _ALL_POST_PERMISSIONS)
        response = await client.post(
            f"/api/v1/supplier-payments/{uuid.uuid4()}/post", headers=headers
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_NOT_FOUND"

    async def test_cannot_post_another_tenants_payment(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        bill = await _create_posted_purchase_bill(client, headers)
        payment = await _create_supplier_payment(client, headers, amount="150000.00")
        await _create_supplier_payment_allocation(
            client,
            headers,
            payment["id"],
            purchase_bill_id=bill["id"],
            allocated_amount="150000.00",
        )

        other_tenant = Tenant(
            name="Post Isolation Tenant", slug=f"sp-post-isolation-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_POST_PERMISSIONS)

        response = await client.post(
            f"/api/v1/supplier-payments/{payment['id']}/post", headers=other_headers
        )
        assert response.status_code == 404

        still_draft = await client.get(
            f"/api/v1/supplier-payments/{payment['id']}", headers=headers
        )
        assert still_draft.json()["status"] == "draft"

    async def test_posted_payment_cannot_be_updated(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Post Immutable Update Tenant", slug=f"sp-post-imm-upd-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_POST_PERMISSIONS)

        bill = await _create_posted_purchase_bill(client, headers)
        payment = await _create_supplier_payment(client, headers, amount="150000.00")
        await _create_supplier_payment_allocation(
            client,
            headers,
            payment["id"],
            purchase_bill_id=bill["id"],
            allocated_amount="150000.00",
        )
        await client.post(f"/api/v1/supplier-payments/{payment['id']}/post", headers=headers)

        response = await client.put(
            f"/api/v1/supplier-payments/{payment['id']}",
            json={"remarks": "Trying to edit"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_NOT_DRAFT"

    async def test_posted_payment_cannot_be_deleted(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Post Immutable Delete Tenant", slug=f"sp-post-imm-del-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_POST_PERMISSIONS)

        bill = await _create_posted_purchase_bill(client, headers)
        payment = await _create_supplier_payment(client, headers, amount="150000.00")
        await _create_supplier_payment_allocation(
            client,
            headers,
            payment["id"],
            purchase_bill_id=bill["id"],
            allocated_amount="150000.00",
        )
        await client.post(f"/api/v1/supplier-payments/{payment['id']}/post", headers=headers)

        response = await client.delete(
            f"/api/v1/supplier-payments/{payment['id']}", headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_NOT_DRAFT"

    async def test_posted_payments_allocations_are_immutable(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Post Immutable Alloc Tenant", slug=f"sp-post-imm-alloc-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, other_tenant.id, _ALL_POST_PERMISSIONS)

        bill = await _create_posted_purchase_bill(client, headers)
        other_bill = await _create_posted_purchase_bill(client, headers)
        payment = await _create_supplier_payment(client, headers, amount="150000.00")
        allocation = await _create_supplier_payment_allocation(
            client,
            headers,
            payment["id"],
            purchase_bill_id=bill["id"],
            allocated_amount="150000.00",
        )
        await client.post(f"/api/v1/supplier-payments/{payment['id']}/post", headers=headers)

        create_response = await client.post(
            f"/api/v1/supplier-payments/{payment['id']}/allocations",
            json={"purchase_bill_id": other_bill["id"], "allocated_amount": "1.00"},
            headers=headers,
        )
        assert create_response.status_code == 409
        assert (
            create_response.json()["error"]["code"]
            == "SUPPLIER_PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT"
        )

        update_response = await client.put(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            json={"allocated_amount": "1.00"},
            headers=headers,
        )
        assert update_response.status_code == 409
        assert (
            update_response.json()["error"]["code"]
            == "SUPPLIER_PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT"
        )

        delete_response = await client.delete(
            f"/api/v1/supplier-payments/{payment['id']}/allocations/{allocation['id']}",
            headers=headers,
        )
        assert delete_response.status_code == 409
        assert (
            delete_response.json()["error"]["code"]
            == "SUPPLIER_PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT"
        )
