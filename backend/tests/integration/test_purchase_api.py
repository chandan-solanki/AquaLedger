import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.purchase.constants import PurchaseStatus
from app.modules.purchase.models import PurchaseBill
from app.modules.suppliers.constants import SupplierStatus
from app.modules.suppliers.models import Supplier

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

# _create_purchase_bill provisions a fresh supplier via the API by default,
# so test users need supplier:create access too for that setup to succeed.
_ALL_PURCHASE_PERMISSIONS = [
    "purchase:view",
    "purchase:create",
    "purchase:edit",
    "purchase:delete",
    "supplier:view",
    "supplier:create",
]
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
        "code": f"SUP-{uuid.uuid4().hex[:8]}",
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
    via the DB."""
    row = (
        await db_session.execute(select(Supplier).where(Supplier.id == uuid.UUID(supplier_id)))
    ).scalar_one()
    row.status = SupplierStatus.INACTIVE
    await db_session.commit()


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


class TestCreatePurchaseBill:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/purchase",
            json={"supplier_id": str(uuid.uuid4()), "bill_date": _BILL_DATE},
        )
        assert response.status_code == 401

    async def test_requires_create_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["purchase:view"])
        response = await client.post(
            "/api/v1/purchase",
            json={"supplier_id": str(uuid.uuid4()), "bill_date": _BILL_DATE},
            headers=headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_success_is_draft_with_server_owned_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        body = await _create_purchase_bill(
            client, headers, due_date="2026-08-22", remarks="Weekly settlement"
        )

        assert body["status"] == "draft"
        assert body["bill_number"] is None
        assert body["posted_at"] is None
        assert body["subtotal"] == "0.00"
        assert body["discount_amount"] == "0.00"
        assert body["tax_amount"] == "0.00"
        assert body["transport_charge"] == "0.00"
        assert body["other_charge"] == "0.00"
        assert body["round_off"] == "0.00"
        assert body["total_amount"] == "0.00"
        assert body["paid_amount"] == "0.00"
        assert body["balance_amount"] == "0.00"
        assert body["remarks"] == "Weekly settlement"
        assert body["due_date"] == "2026-08-22"
        assert body["created_at"] == body["updated_at"]

    async def test_success_sets_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        body = await _create_purchase_bill(client, headers)

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(
                select(PurchaseBill).where(PurchaseBill.id == uuid.UUID(body["id"]))
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
            "/api/v1/purchase",
            json={
                "supplier_id": supplier_id,
                "bill_date": _BILL_DATE,
                "bill_number": "PUR-0001",
                "subtotal": "5000.00",
                "total_amount": "5000.00",
                "status": "posted",
                "posted_at": "2026-07-23T04:00:00Z",
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["bill_number"] is None
        assert body["subtotal"] == "0.00"
        assert body["total_amount"] == "0.00"
        assert body["status"] == "draft"
        assert body["posted_at"] is None

    async def test_unknown_supplier_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/purchase",
            json={"supplier_id": str(uuid.uuid4()), "bill_date": _BILL_DATE},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_BILL_SUPPLIER_NOT_FOUND"

    async def test_inactive_supplier_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # SupplierUpdateRequest has no `status` field at all in this
        # session (status is server-owned, see SupplierCreateRequest's
        # docstring) - there is no API path to deactivate a supplier yet,
        # so this flips it directly via the DB to exercise the check.
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        await _set_supplier_inactive(db_session, supplier["id"])

        response = await client.post(
            "/api/v1/purchase",
            json={"supplier_id": supplier["id"], "bill_date": _BILL_DATE},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PURCHASE_BILL_SUPPLIER_INACTIVE"

    async def test_missing_supplier_id_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/purchase", json={"bill_date": _BILL_DATE}, headers=headers
        )
        assert response.status_code == 422
        assert "supplier_id" in response.json()["error"]["field_errors"]

    async def test_missing_bill_date_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        response = await client.post(
            "/api/v1/purchase", json={"supplier_id": supplier["id"]}, headers=headers
        )
        assert response.status_code == 422
        assert "bill_date" in response.json()["error"]["field_errors"]

    async def test_cannot_use_another_tenants_supplier(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)

        other_tenant = Tenant(
            name="Foreign Purchase Supplier Owner", slug=f"foreign-pur-sup-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_PURCHASE_PERMISSIONS
        )
        foreign_supplier = await _create_supplier(client, other_headers)

        response = await client.post(
            "/api/v1/purchase",
            json={"supplier_id": foreign_supplier["id"], "bill_date": _BILL_DATE},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_BILL_SUPPLIER_NOT_FOUND"


class TestGetPurchaseBill:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/purchase/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(f"/api/v1/purchase/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_returns_the_bill(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_purchase_bill(client, headers)
        response = await client.get(f"/api/v1/purchase/{created['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(f"/api/v1/purchase/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_FOUND"

    async def test_soft_deleted_bill_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_purchase_bill(client, headers)
        await client.delete(f"/api/v1/purchase/{created['id']}", headers=headers)
        response = await client.get(f"/api/v1/purchase/{created['id']}", headers=headers)
        assert response.status_code == 404

    async def test_other_tenants_bill_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_purchase_bill(client, headers)

        other_tenant = Tenant(name="Other Purch Co", slug=f"other-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_PURCHASE_PERMISSIONS
        )

        response = await client.get(f"/api/v1/purchase/{created['id']}", headers=other_headers)
        assert response.status_code == 404


class TestListPurchaseBills:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/purchase")
        assert response.status_code == 401

    async def test_default_response_shape(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await _create_purchase_bill(client, headers)
        response = await client.get("/api/v1/purchase", headers=headers)
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

    async def test_search_matches_supplier_name(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        marker = uuid.uuid4().hex[:8]
        supplier = await _create_supplier(client, headers, name=f"Ocean Supplies {marker}")
        matching = await _create_purchase_bill(client, headers, supplier_id=supplier["id"])
        await _create_purchase_bill(client, headers)  # noise, unrelated supplier

        response = await client.get(
            "/api/v1/purchase", params={"q": f"ocean supplies {marker}"}, headers=headers
        )
        ids = [b["id"] for b in response.json()["data"]]
        assert ids == [matching["id"]]

    async def test_filters_by_status(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        draft = await _create_purchase_bill(client, headers)

        response = await client.get("/api/v1/purchase", params={"status": "draft"}, headers=headers)
        ids = [b["id"] for b in response.json()["data"]]
        assert draft["id"] in ids

        response_posted = await client.get(
            "/api/v1/purchase", params={"status": "posted"}, headers=headers
        )
        assert draft["id"] not in [b["id"] for b in response_posted.json()["data"]]

    async def test_filters_by_supplier_id(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier_a = await _create_supplier(client, headers)
        supplier_b = await _create_supplier(client, headers)
        target = await _create_purchase_bill(client, headers, supplier_id=supplier_a["id"])
        await _create_purchase_bill(client, headers, supplier_id=supplier_b["id"])

        response = await client.get(
            "/api/v1/purchase", params={"supplier_id": supplier_a["id"]}, headers=headers
        )
        ids = [b["id"] for b in response.json()["data"]]
        assert ids == [target["id"]]

    async def test_filters_by_bill_date_range(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        in_range = await _create_purchase_bill(client, headers, bill_date="2026-06-15")
        await _create_purchase_bill(client, headers, bill_date="2026-01-01")

        response = await client.get(
            "/api/v1/purchase",
            params={"bill_date_from": "2026-06-01", "bill_date_to": "2026-06-30"},
            headers=headers,
        )
        ids = [b["id"] for b in response.json()["data"]]
        assert in_range["id"] in ids

    async def test_sort_ascending_and_descending(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        first = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], bill_date="2026-01-01"
        )
        second = await _create_purchase_bill(
            client, headers, supplier_id=supplier["id"], bill_date="2026-06-01"
        )

        asc = await client.get(
            "/api/v1/purchase",
            params={"supplier_id": supplier["id"], "sort": "bill_date"},
            headers=headers,
        )
        assert [b["id"] for b in asc.json()["data"]] == [first["id"], second["id"]]

        desc = await client.get(
            "/api/v1/purchase",
            params={"supplier_id": supplier["id"], "sort": "-bill_date"},
            headers=headers,
        )
        assert [b["id"] for b in desc.json()["data"]] == [second["id"], first["id"]]

    async def test_invalid_sort_field_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/purchase", params={"sort": "not_a_field"}, headers=headers
        )
        assert response.status_code == 422

    async def test_pagination_meta_is_correct(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        for _ in range(3):
            await _create_purchase_bill(client, headers, supplier_id=supplier["id"])

        response = await client.get(
            "/api/v1/purchase",
            params={"supplier_id": supplier["id"], "page": 1, "page_size": 2},
            headers=headers,
        )
        meta = response.json()["meta"]
        assert meta["total_records"] == 3
        assert meta["total_pages"] == 2
        assert meta["current_page"] == 1
        assert meta["page_size"] == 2
        assert meta["has_next"] is True
        assert meta["has_previous"] is False

        page2 = await client.get(
            "/api/v1/purchase",
            params={"supplier_id": supplier["id"], "page": 2, "page_size": 2},
            headers=headers,
        )
        meta2 = page2.json()["meta"]
        assert meta2["has_next"] is False
        assert meta2["has_previous"] is True
        assert len(page2.json()["data"]) == 1

    async def test_deleted_bills_are_excluded(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_purchase_bill(client, headers)
        await client.delete(f"/api/v1/purchase/{created['id']}", headers=headers)

        response = await client.get(
            "/api/v1/purchase", params={"supplier_id": created["supplier_id"]}, headers=headers
        )
        assert response.json()["data"] == []

    async def test_tenant_isolation_returns_only_own_bills(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        await _create_purchase_bill(client, headers)

        other_tenant = Tenant(name="Isolated Purch", slug=f"isolated-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_PURCHASE_PERMISSIONS
        )

        response = await client.get("/api/v1/purchase", headers=other_headers)
        assert response.json()["data"] == []


class TestUpdatePurchaseBill:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.put(
            f"/api/v1/purchase/{uuid.uuid4()}", json={"remarks": "New remark"}
        )
        assert response.status_code == 401

    async def test_requires_edit_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["purchase:view"])
        response = await client.put(
            f"/api/v1/purchase/{uuid.uuid4()}", json={"remarks": "New remark"}, headers=headers
        )
        assert response.status_code == 403

    async def test_partial_update_only_changes_supplied_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_purchase_bill(
            client, headers, due_date="2026-08-01", remarks="Original"
        )

        response = await client.put(
            f"/api/v1/purchase/{created['id']}",
            json={"remarks": "Updated"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["remarks"] == "Updated"
        assert body["due_date"] == "2026-08-01"

    async def test_cannot_set_server_owned_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_purchase_bill(client, headers)

        response = await client.put(
            f"/api/v1/purchase/{created['id']}",
            json={"bill_number": "PUR-9999", "status": "posted", "total_amount": "999.00"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["bill_number"] is None
        assert body["status"] == "draft"
        assert body["total_amount"] == "0.00"

    async def test_reassigning_to_an_unknown_supplier_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_purchase_bill(client, headers)

        response = await client.put(
            f"/api/v1/purchase/{created['id']}",
            json={"supplier_id": str(uuid.uuid4())},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_BILL_SUPPLIER_NOT_FOUND"

    async def test_reassigning_to_an_inactive_supplier_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_purchase_bill(client, headers)
        new_supplier = await _create_supplier(client, headers)
        await _set_supplier_inactive(db_session, new_supplier["id"])

        response = await client.put(
            f"/api/v1/purchase/{created['id']}",
            json={"supplier_id": new_supplier["id"]},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PURCHASE_BILL_SUPPLIER_INACTIVE"

    async def test_reassigning_to_the_same_supplier_does_not_revalidate(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_purchase_bill(client, headers)

        response = await client.put(
            f"/api/v1/purchase/{created['id']}",
            json={"supplier_id": created["supplier_id"], "remarks": "Touched"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["remarks"] == "Touched"

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            f"/api/v1/purchase/{uuid.uuid4()}", json={"remarks": "X"}, headers=headers
        )
        assert response.status_code == 404

    async def test_cannot_update_a_deleted_bill(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_purchase_bill(client, headers)
        await client.delete(f"/api/v1/purchase/{created['id']}", headers=headers)

        response = await client.put(
            f"/api/v1/purchase/{created['id']}",
            json={"remarks": "Should Not Apply"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_FOUND"


class TestUpdateNonDraftPurchaseBillIsRejected:
    """Only DRAFT bills may be updated/deleted (TASKS.md). No posting
    endpoint exists yet in this session, so the only way to produce a
    non-DRAFT row is to flip its status directly via the DB session."""

    async def test_posted_bill_cannot_be_updated(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_purchase_bill(client, headers)

        row = (
            await db_session.execute(
                select(PurchaseBill).where(PurchaseBill.id == uuid.UUID(created["id"]))
            )
        ).scalar_one()
        row.status = PurchaseStatus.POSTED
        await db_session.commit()

        response = await client.put(
            f"/api/v1/purchase/{created['id']}",
            json={"remarks": "Should be rejected"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_DRAFT"

    async def test_posted_bill_cannot_be_deleted(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_purchase_bill(client, headers)

        row = (
            await db_session.execute(
                select(PurchaseBill).where(PurchaseBill.id == uuid.UUID(created["id"]))
            )
        ).scalar_one()
        row.status = PurchaseStatus.POSTED
        await db_session.commit()

        response = await client.delete(f"/api/v1/purchase/{created['id']}", headers=headers)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_DRAFT"

    async def test_cancelled_bill_cannot_be_updated(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_purchase_bill(client, headers)

        row = (
            await db_session.execute(
                select(PurchaseBill).where(PurchaseBill.id == uuid.UUID(created["id"]))
            )
        ).scalar_one()
        row.status = PurchaseStatus.CANCELLED
        await db_session.commit()

        response = await client.put(
            f"/api/v1/purchase/{created['id']}",
            json={"remarks": "Should be rejected"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_DRAFT"


class TestDeletePurchaseBill:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.delete(f"/api/v1/purchase/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_delete_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(
            db_session, tenant_id, ["purchase:view", "purchase:edit"]
        )
        response = await client.delete(f"/api/v1/purchase/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_success_soft_deletes_and_sets_audit_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_purchase_bill(client, headers)

        response = await client.delete(f"/api/v1/purchase/{created['id']}", headers=headers)
        assert response.status_code == 204
        assert response.content == b""

        admin = (
            await db_session.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        ).scalar_one()
        row = (
            await db_session.execute(
                select(PurchaseBill).where(PurchaseBill.id == uuid.UUID(created["id"]))
            )
        ).scalar_one()
        assert row.deleted_at is not None
        assert row.deleted_by == admin.id

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.delete(f"/api/v1/purchase/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404

    async def test_deleting_twice_is_404_the_second_time(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = await _create_purchase_bill(client, headers)
        first = await client.delete(f"/api/v1/purchase/{created['id']}", headers=headers)
        second = await client.delete(f"/api/v1/purchase/{created['id']}", headers=headers)
        assert first.status_code == 204
        assert second.status_code == 404

    async def test_cannot_delete_another_tenants_bill(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        created = await _create_purchase_bill(client, headers)

        other_tenant = Tenant(name="Other Deleter Purch", slug=f"other-del-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_PURCHASE_PERMISSIONS
        )

        response = await client.delete(f"/api/v1/purchase/{created['id']}", headers=other_headers)
        assert response.status_code == 404

        still_there = await client.get(f"/api/v1/purchase/{created['id']}", headers=headers)
        assert still_there.status_code == 200


_ITEM_PAYLOAD: dict[str, Any] = {
    "description": "Pomfret - Grade A",
    "quantity": "50.000",
    "unit": "KG",
    "rate": "450.0000",
}


async def _add_item(
    client: AsyncClient, headers: dict[str, str], purchase_bill_id: str, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {**_ITEM_PAYLOAD}
    payload.update(overrides)
    response = await client.post(
        f"/api/v1/purchase/{purchase_bill_id}/items", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _set_bill_status(
    db_session: AsyncSession, purchase_bill_id: str, status: PurchaseStatus
) -> None:
    row = (
        await db_session.execute(
            select(PurchaseBill).where(PurchaseBill.id == uuid.UUID(purchase_bill_id))
        )
    ).scalar_one()
    row.status = status
    await db_session.commit()


class TestAddPurchaseBillItem:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(f"/api/v1/purchase/{uuid.uuid4()}/items", json=_ITEM_PAYLOAD)
        assert response.status_code == 401

    async def test_requires_create_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["purchase:view"])
        response = await client.post(
            f"/api/v1/purchase/{uuid.uuid4()}/items", json=_ITEM_PAYLOAD, headers=headers
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_success_assigns_line_number_and_calculates_financial_fields(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)

        item = await _add_item(client, headers, bill["id"])

        assert item["line_number"] == 1
        assert item["purchase_bill_id"] == bill["id"]
        assert item["description"] == "Pomfret - Grade A"
        assert item["quantity"] == "50.000"
        assert item["unit"] == "KG"
        assert item["rate"] == "450.0000"
        assert item["discount_percent"] == "0.00"
        assert item["tax_rate"] == "0.00"
        # gross = 50.000 * 450.0000 = 22500.00, 0% discount, 0% tax.
        assert item["discount_amount"] == "0.00"
        assert item["taxable_amount"] == "22500.00"
        assert item["tax_amount"] == "0.00"
        assert item["line_total"] == "22500.00"

    async def test_calculates_discount_and_tax(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)

        item = await _add_item(
            client, headers, bill["id"], discount_percent="10.00", tax_rate="5.00"
        )

        # gross = 22500.00, discount = 2250.00, taxable = 20250.00,
        # tax = 20250.00 * 5% = 1012.50, line_total = 21262.50.
        assert item["discount_amount"] == "2250.00"
        assert item["taxable_amount"] == "20250.00"
        assert item["tax_amount"] == "1012.50"
        assert item["line_total"] == "21262.50"

    async def test_server_owned_fields_in_the_request_are_ignored(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)

        response = await client.post(
            f"/api/v1/purchase/{bill['id']}/items",
            json={
                **_ITEM_PAYLOAD,
                "line_number": 99,
                "discount_amount": "500.00",
                "taxable_amount": "500.00",
                "tax_amount": "500.00",
                "line_total": "500.00",
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["line_number"] == 1
        # The client's spoofed 500.00 values are ignored - the server
        # computes its own from quantity/rate/discount_percent/tax_rate.
        assert body["discount_amount"] == "0.00"
        assert body["taxable_amount"] == "22500.00"
        assert body["tax_amount"] == "0.00"
        assert body["line_total"] == "22500.00"

    async def test_sequential_line_numbers_across_multiple_items(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)

        first = await _add_item(client, headers, bill["id"], description="Item 1")
        second = await _add_item(client, headers, bill["id"], description="Item 2")
        third = await _add_item(client, headers, bill["id"], description="Item 3")

        assert [first["line_number"], second["line_number"], third["line_number"]] == [1, 2, 3]

    async def test_line_number_is_never_reused_after_delete(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)

        await _add_item(client, headers, bill["id"], description="Item 1")
        second = await _add_item(client, headers, bill["id"], description="Item 2")
        await _add_item(client, headers, bill["id"], description="Item 3")

        delete_response = await client.delete(
            f"/api/v1/purchase/{bill['id']}/items/{second['id']}", headers=headers
        )
        assert delete_response.status_code == 204

        fourth = await _add_item(client, headers, bill["id"], description="Item 4")
        assert fourth["line_number"] == 4

    @pytest.mark.parametrize(
        "overrides",
        [
            {"description": ""},
            {"quantity": "0"},
            {"quantity": "-1"},
            {"unit": ""},
            {"rate": "-1"},
            {"discount_percent": "-1"},
            {"discount_percent": "100.01"},
            {"tax_rate": "-1"},
            {"tax_rate": "100.01"},
        ],
    )
    async def test_validation_errors_are_422(
        self, client: AsyncClient, overrides: dict[str, Any]
    ) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)

        response = await client.post(
            f"/api/v1/purchase/{bill['id']}/items",
            json={**_ITEM_PAYLOAD, **overrides},
            headers=headers,
        )
        assert response.status_code == 422

    async def test_missing_required_fields_are_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)

        response = await client.post(
            f"/api/v1/purchase/{bill['id']}/items", json={}, headers=headers
        )
        assert response.status_code == 422
        field_errors = response.json()["error"]["field_errors"]
        assert "description" in field_errors
        assert "quantity" in field_errors
        assert "unit" in field_errors
        assert "rate" in field_errors

    async def test_unknown_bill_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            f"/api/v1/purchase/{uuid.uuid4()}/items", json=_ITEM_PAYLOAD, headers=headers
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_FOUND"

    async def test_cannot_add_item_to_a_non_draft_bill(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        await _set_bill_status(db_session, bill["id"], PurchaseStatus.POSTED)

        response = await client.post(
            f"/api/v1/purchase/{bill['id']}/items", json=_ITEM_PAYLOAD, headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_DRAFT"

    async def test_cannot_add_item_to_another_tenants_bill(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)

        other_tenant = Tenant(name="Other Item Adder", slug=f"other-item-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_PURCHASE_PERMISSIONS
        )

        response = await client.post(
            f"/api/v1/purchase/{bill['id']}/items", json=_ITEM_PAYLOAD, headers=other_headers
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_FOUND"


class TestListPurchaseBillItems:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/purchase/{uuid.uuid4()}/items")
        assert response.status_code == 401

    async def test_requires_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get(f"/api/v1/purchase/{uuid.uuid4()}/items", headers=headers)
        assert response.status_code == 403

    async def test_returns_items_ordered_by_line_number(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        first = await _add_item(client, headers, bill["id"], description="Item 1")
        second = await _add_item(client, headers, bill["id"], description="Item 2")

        response = await client.get(f"/api/v1/purchase/{bill['id']}/items", headers=headers)
        assert response.status_code == 200
        ids = [i["id"] for i in response.json()]
        assert ids == [first["id"], second["id"]]

    async def test_search_matches_description(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        target = await _add_item(client, headers, bill["id"], description="Pomfret - Grade A")
        await _add_item(client, headers, bill["id"], description="Sardine")

        response = await client.get(
            f"/api/v1/purchase/{bill['id']}/items", params={"q": "pomfret"}, headers=headers
        )
        ids = [i["id"] for i in response.json()]
        assert ids == [target["id"]]

    async def test_sort_descending_by_description(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        await _add_item(client, headers, bill["id"], description="Alpha")
        await _add_item(client, headers, bill["id"], description="Charlie")
        await _add_item(client, headers, bill["id"], description="Bravo")

        response = await client.get(
            f"/api/v1/purchase/{bill['id']}/items",
            params={"sort": "-description"},
            headers=headers,
        )
        descriptions = [i["description"] for i in response.json()]
        assert descriptions == ["Charlie", "Bravo", "Alpha"]

    async def test_invalid_sort_field_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)

        response = await client.get(
            f"/api/v1/purchase/{bill['id']}/items",
            params={"sort": "not_a_field"},
            headers=headers,
        )
        assert response.status_code == 422

    async def test_allowed_regardless_of_bill_status(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        await _add_item(client, headers, bill["id"])
        await _set_bill_status(db_session, bill["id"], PurchaseStatus.POSTED)

        response = await client.get(f"/api/v1/purchase/{bill['id']}/items", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_unknown_bill_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(f"/api/v1/purchase/{uuid.uuid4()}/items", headers=headers)
        assert response.status_code == 404

    async def test_cannot_list_items_of_another_tenants_bill(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        await _add_item(client, headers, bill["id"])

        other_tenant = Tenant(name="Other Item Lister", slug=f"other-list-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_PURCHASE_PERMISSIONS
        )

        response = await client.get(f"/api/v1/purchase/{bill['id']}/items", headers=other_headers)
        assert response.status_code == 404


class TestUpdatePurchaseBillItem:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.put(
            f"/api/v1/purchase/{uuid.uuid4()}/items/{uuid.uuid4()}", json={"quantity": "1.000"}
        )
        assert response.status_code == 401

    async def test_requires_edit_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["purchase:view"])
        response = await client.put(
            f"/api/v1/purchase/{uuid.uuid4()}/items/{uuid.uuid4()}",
            json={"quantity": "1.000"},
            headers=headers,
        )
        assert response.status_code == 403

    async def test_partial_update_only_changes_supplied_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        item = await _add_item(client, headers, bill["id"])

        response = await client.put(
            f"/api/v1/purchase/{bill['id']}/items/{item['id']}",
            json={"quantity": "75.500"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["quantity"] == "75.500"
        assert body["rate"] == item["rate"]
        assert body["description"] == item["description"]

    async def test_cannot_set_server_owned_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        item = await _add_item(client, headers, bill["id"])

        response = await client.put(
            f"/api/v1/purchase/{bill['id']}/items/{item['id']}",
            json={"line_number": 99, "line_total": "999.00"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["line_number"] == 1
        # The client's spoofed line_total is ignored - recomputed from
        # quantity/rate/discount_percent/tax_rate instead.
        assert body["line_total"] == "22500.00"

    @pytest.mark.parametrize(
        "payload",
        [
            {"quantity": "0"},
            {"rate": "-1"},
            {"discount_percent": "100.01"},
            {"tax_rate": "-1"},
            {"unit": ""},
            {"description": ""},
        ],
    )
    async def test_validation_errors_are_422(
        self, client: AsyncClient, payload: dict[str, Any]
    ) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        item = await _add_item(client, headers, bill["id"])

        response = await client.put(
            f"/api/v1/purchase/{bill['id']}/items/{item['id']}", json=payload, headers=headers
        )
        assert response.status_code == 422

    async def test_unknown_item_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)

        response = await client.put(
            f"/api/v1/purchase/{bill['id']}/items/{uuid.uuid4()}",
            json={"quantity": "1.000"},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_BILL_ITEM_NOT_FOUND"

    async def test_item_belonging_to_a_different_bill_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill_a = await _create_purchase_bill(client, headers)
        bill_b = await _create_purchase_bill(client, headers)
        item = await _add_item(client, headers, bill_a["id"])

        response = await client.put(
            f"/api/v1/purchase/{bill_b['id']}/items/{item['id']}",
            json={"quantity": "1.000"},
            headers=headers,
        )
        assert response.status_code == 404

    async def test_cannot_update_item_on_a_non_draft_bill(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        item = await _add_item(client, headers, bill["id"])
        await _set_bill_status(db_session, bill["id"], PurchaseStatus.POSTED)

        response = await client.put(
            f"/api/v1/purchase/{bill['id']}/items/{item['id']}",
            json={"quantity": "1.000"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_DRAFT"


class TestDeletePurchaseBillItem:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.delete(f"/api/v1/purchase/{uuid.uuid4()}/items/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_delete_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(
            db_session, tenant_id, ["purchase:view", "purchase:edit"]
        )
        response = await client.delete(
            f"/api/v1/purchase/{uuid.uuid4()}/items/{uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 403

    async def test_success_removes_the_item(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        item = await _add_item(client, headers, bill["id"])

        response = await client.delete(
            f"/api/v1/purchase/{bill['id']}/items/{item['id']}", headers=headers
        )
        assert response.status_code == 204
        assert response.content == b""

        listed = await client.get(f"/api/v1/purchase/{bill['id']}/items", headers=headers)
        assert listed.json() == []

    async def test_deleting_twice_is_404_the_second_time(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        item = await _add_item(client, headers, bill["id"])

        first = await client.delete(
            f"/api/v1/purchase/{bill['id']}/items/{item['id']}", headers=headers
        )
        second = await client.delete(
            f"/api/v1/purchase/{bill['id']}/items/{item['id']}", headers=headers
        )
        assert first.status_code == 204
        assert second.status_code == 404
        assert second.json()["error"]["code"] == "PURCHASE_BILL_ITEM_NOT_FOUND"

    async def test_unknown_item_id_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)

        response = await client.delete(
            f"/api/v1/purchase/{bill['id']}/items/{uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 404

    async def test_cannot_delete_item_on_a_non_draft_bill(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        item = await _add_item(client, headers, bill["id"])
        await _set_bill_status(db_session, bill["id"], PurchaseStatus.POSTED)

        response = await client.delete(
            f"/api/v1/purchase/{bill['id']}/items/{item['id']}", headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_DRAFT"

    async def test_cannot_delete_another_tenants_item(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        item = await _add_item(client, headers, bill["id"])

        other_tenant = Tenant(name="Other Item Deleter", slug=f"other-idel-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_PURCHASE_PERMISSIONS
        )

        response = await client.delete(
            f"/api/v1/purchase/{bill['id']}/items/{item['id']}", headers=other_headers
        )
        assert response.status_code == 404

        still_there = await client.get(f"/api/v1/purchase/{bill['id']}/items", headers=headers)
        assert len(still_there.json()) == 1


class TestPurchaseFinancialEngine:
    """Sprint 11 Session 4 (TASKS.md) - end-to-end financial engine
    coverage through the HTTP API, complementing the service-level tests in
    test_purchase_recalculation.py."""

    async def test_bill_totals_automatically_recalculate_across_item_mutations(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)

        item_a = await _add_item(
            client, headers, bill["id"], description="Item A", quantity="10.000", rate="100.0000"
        )
        item_b = await _add_item(
            client,
            headers,
            bill["id"],
            description="Item B",
            quantity="5.000",
            rate="50.0000",
            tax_rate="10.00",
        )

        # item A: 10*100=1000; item B: 5*50=250, tax 10% = 25, line_total=275
        after_add = await client.get(f"/api/v1/purchase/{bill['id']}", headers=headers)
        body = after_add.json()
        assert body["subtotal"] == "1275.00"
        assert body["tax_amount"] == "25.00"
        assert body["total_amount"] == "1275.00"
        assert body["balance_amount"] == "1275.00"

        await client.put(
            f"/api/v1/purchase/{bill['id']}/items/{item_b['id']}",
            json={"quantity": "10.000"},
            headers=headers,
        )
        # item B now 10*50=500, tax 10% = 50, line_total=550; subtotal = 1000+550=1550
        after_update = await client.get(f"/api/v1/purchase/{bill['id']}", headers=headers)
        assert after_update.json()["subtotal"] == "1550.00"
        assert after_update.json()["total_amount"] == "1550.00"

        await client.delete(f"/api/v1/purchase/{bill['id']}/items/{item_a['id']}", headers=headers)
        # only item B (550.00) remains
        after_delete = await client.get(f"/api/v1/purchase/{bill['id']}", headers=headers)
        body = after_delete.json()
        assert body["subtotal"] == "550.00"
        assert body["total_amount"] == "550.00"
        assert body["balance_amount"] == "550.00"

    async def test_deleting_the_only_item_zeroes_bill_totals(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        item = await _add_item(client, headers, bill["id"])

        await client.delete(f"/api/v1/purchase/{bill['id']}/items/{item['id']}", headers=headers)

        response = await client.get(f"/api/v1/purchase/{bill['id']}", headers=headers)
        body = response.json()
        assert body["subtotal"] == "0.00"
        assert body["taxable_amount"] == "0.00"
        assert body["tax_amount"] == "0.00"
        assert body["total_amount"] == "0.00"
        assert body["balance_amount"] == "0.00"
        assert body["paid_amount"] == "0.00"

    async def test_half_up_rounding_through_the_api(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)

        # gross = 2 * 0.625 = 1.25; discount = 1.25 * 50% = 0.625 exactly ->
        # HALF_UP rounds to 0.63, not 0.62 (banker's rounding would).
        item = await _add_item(
            client,
            headers,
            bill["id"],
            quantity="2.000",
            rate="0.6250",
            discount_percent="50.00",
        )
        assert item["discount_amount"] == "0.63"
        assert item["taxable_amount"] == "0.62"

    async def test_negative_quantity_and_rate_are_rejected_before_calculation(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)

        negative_quantity = await client.post(
            f"/api/v1/purchase/{bill['id']}/items",
            json={**_ITEM_PAYLOAD, "quantity": "-1"},
            headers=headers,
        )
        assert negative_quantity.status_code == 422

        negative_rate = await client.post(
            f"/api/v1/purchase/{bill['id']}/items",
            json={**_ITEM_PAYLOAD, "rate": "-1"},
            headers=headers,
        )
        assert negative_rate.status_code == 422

        # No item was ever created, so the bill's totals are untouched at 0.
        response = await client.get(f"/api/v1/purchase/{bill['id']}", headers=headers)
        assert response.json()["total_amount"] == "0.00"

    async def test_multiple_items_with_mixed_discount_and_tax_sum_correctly(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)

        await _add_item(
            client,
            headers,
            bill["id"],
            description="Pomfret",
            quantity="50.000",
            rate="450.0000",
            tax_rate="5.00",
        )
        await _add_item(
            client,
            headers,
            bill["id"],
            description="Sardine",
            quantity="20.000",
            rate="100.0000",
            discount_percent="10.00",
            tax_rate="12.00",
        )

        # Pomfret: 22500.00 taxable, 1125.00 tax, 23625.00 line_total
        # Sardine: gross 2000.00, discount 200.00, taxable 1800.00,
        #          tax 216.00, line_total 2016.00
        response = await client.get(f"/api/v1/purchase/{bill['id']}", headers=headers)
        body = response.json()
        assert body["subtotal"] == "25641.00"
        assert body["discount_amount"] == "200.00"
        assert body["taxable_amount"] == "24300.00"
        assert body["tax_amount"] == "1341.00"
        assert body["total_amount"] == "25641.00"
