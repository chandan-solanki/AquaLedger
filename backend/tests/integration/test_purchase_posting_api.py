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

# _create_purchase_bill provisions a fresh supplier via the API by default,
# so test users need supplier:create access too for that setup to succeed,
# plus purchase:post itself.
_ALL_POST_PERMISSIONS = [
    "purchase:view",
    "purchase:create",
    "purchase:edit",
    "purchase:delete",
    "purchase:post",
    "supplier:view",
    "supplier:create",
]
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
        "code": f"POSTSUP-{uuid.uuid4().hex[:8]}",
        "name": f"Post Supplier {uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/suppliers", json=payload, headers=headers)
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


async def _add_item(
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


async def _post_bill(client: AsyncClient, headers: dict[str, str], bill_id: str) -> Any:
    return await client.post(f"/api/v1/purchase/{bill_id}/post", headers=headers)


async def _draft_bill_with_item(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    supplier_id: str | None = None,
    **item_overrides: Any,
) -> dict[str, Any]:
    bill = await _create_purchase_bill(client, headers, supplier_id=supplier_id)
    await _add_item(client, headers, bill["id"], **item_overrides)
    return bill


class TestPostEndpointAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(f"/api/v1/purchase/{uuid.uuid4()}/post")
        assert response.status_code == 401

    async def test_requires_post_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """A user with every other purchase permission (view/create/edit/
        delete) but not purchase:post must still be rejected - post is its
        own route-level permission, distinct from purchase:edit, since
        posted bills can never be reached through the edit path."""
        tenant_id = await _admin_tenant_id(client)
        admin_headers = await _admin_headers(client)
        bill = await _draft_bill_with_item(client, admin_headers)

        permissions_without_post = [p for p in _ALL_POST_PERMISSIONS if p != "purchase:post"]
        limited_headers = await _make_user_headers(db_session, tenant_id, permissions_without_post)

        response = await _post_bill(client, limited_headers, bill["id"])
        assert response.status_code == 403


class TestSuccessfulPost:
    async def test_posts_a_draft_purchase_bill(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _draft_bill_with_item(
            client, headers, quantity="20.000", rate="500.0000", tax_rate="5.00"
        )

        response = await _post_bill(client, headers, bill["id"])

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "posted"
        assert body["bill_number"] is not None
        assert body["bill_number"].startswith("PUR/")
        assert body["posted_at"] is not None
        assert body["total_amount"] == "10500.00"
        assert body["balance_amount"] == "10500.00"

    async def test_posted_bill_is_visible_via_get(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _draft_bill_with_item(client, headers)
        await _post_bill(client, headers, bill["id"])

        response = await client.get(f"/api/v1/purchase/{bill['id']}", headers=headers)

        assert response.status_code == 200
        assert response.json()["status"] == "posted"

    async def test_returns_404_for_an_unknown_bill(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await _post_bill(client, headers, str(uuid.uuid4()))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_FOUND"

    async def test_returns_404_for_a_soft_deleted_draft_bill(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        delete_response = await client.delete(f"/api/v1/purchase/{bill['id']}", headers=headers)
        assert delete_response.status_code == 204

        response = await _post_bill(client, headers, bill["id"])
        assert response.status_code == 404

    async def test_increases_supplier_outstanding(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        bill = await _draft_bill_with_item(
            client, headers, supplier_id=supplier["id"], quantity="10.000", rate="100.0000"
        )

        response = await _post_bill(client, headers, bill["id"])
        assert response.status_code == 200

        supplier_row = (
            await db_session.execute(
                select(Supplier).where(Supplier.id == uuid.UUID(supplier["id"]))
            )
        ).scalar_one()
        assert supplier_row.outstanding_amount == Decimal(response.json()["balance_amount"])


class TestTenantIsolation:
    async def test_returns_404_for_a_bill_belonging_to_another_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Other Post Tenant", slug=f"other-post-tenant-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, _ALL_POST_PERMISSIONS)
        other_bill = await _draft_bill_with_item(client, other_headers)

        admin_headers = await _admin_headers(client)
        response = await _post_bill(client, admin_headers, other_bill["id"])
        assert response.status_code == 404


class TestBusinessRuleFailures:
    async def test_posting_twice_returns_409(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _draft_bill_with_item(client, headers)
        first = await _post_bill(client, headers, bill["id"])
        assert first.status_code == 200

        second = await _post_bill(client, headers, bill["id"])
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "PURCHASE_BILL_NOT_DRAFT"

    async def test_empty_bill_returns_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)

        response = await _post_bill(client, headers, bill["id"])
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PURCHASE_BILL_EMPTY"


class TestImmutabilityAfterPost:
    async def test_posted_bill_cannot_be_updated(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _draft_bill_with_item(client, headers)
        await _post_bill(client, headers, bill["id"])

        response = await client.put(
            f"/api/v1/purchase/{bill['id']}",
            json={"remarks": "Trying to edit a posted bill"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_DRAFT"

    async def test_posted_bill_cannot_be_deleted(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _draft_bill_with_item(client, headers)
        await _post_bill(client, headers, bill["id"])

        response = await client.delete(f"/api/v1/purchase/{bill['id']}", headers=headers)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_DRAFT"

    async def test_cannot_add_an_item_to_a_posted_bill(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _draft_bill_with_item(client, headers)
        await _post_bill(client, headers, bill["id"])

        response = await client.post(
            f"/api/v1/purchase/{bill['id']}/items",
            json={"description": "New", "quantity": "1.000", "unit": "KG", "rate": "1.0000"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_DRAFT"

    async def test_cannot_update_an_item_on_a_posted_bill(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        item = await _add_item(client, headers, bill["id"])
        await _post_bill(client, headers, bill["id"])

        response = await client.put(
            f"/api/v1/purchase/{bill['id']}/items/{item['id']}",
            json={"quantity": "1.000"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_DRAFT"

    async def test_cannot_delete_an_item_on_a_posted_bill(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        item = await _add_item(client, headers, bill["id"])
        await _post_bill(client, headers, bill["id"])

        response = await client.delete(
            f"/api/v1/purchase/{bill['id']}/items/{item['id']}", headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_DRAFT"
