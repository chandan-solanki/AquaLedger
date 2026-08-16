"""Integration tests for GET /api/v1/purchase-orders/{id}/document (Sprint
12 Session 11). Mirrors test_purchase_bill_document_api.py's own helper
style - a fresh supplier/purchase-order/item chain is provisioned per test
via the real API, then confirmed, so the document endpoint is exercised
against a genuinely confirmed order with a real po_number.

Assertions on the rendered PDF are deliberately structural (the `%PDF`
signature, non-empty bytes, the PO number/supplier name appearing
somewhere in the bytes) rather than any pixel-level layout check.
"""

import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.document_engine.document_types import DocumentType
from app.core.document_engine.filename import build_document_filename
from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

# _create_purchase_order provisions a fresh supplier via the API by default, so
# test users need supplier:create access too for that setup to succeed, plus
# purchase_order:confirm itself.
_ALL_DOCUMENT_PERMISSIONS = [
    "purchase_order:view",
    "purchase_order:create",
    "purchase_order:edit",
    "purchase_order:confirm",
    "purchase_order:cancel",
    "supplier:view",
    "supplier:create",
]
_ORDER_DATE = "2026-07-22"


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
        "code": f"DOCSUP-{uuid.uuid4().hex[:8]}",
        "name": f"Document Supplier {uuid.uuid4().hex[:8]}",
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


async def _confirmed_order_with_item(
    client: AsyncClient, headers: dict[str, str], *, supplier_id: str | None = None
) -> dict[str, Any]:
    order = await _create_purchase_order(client, headers, supplier_id=supplier_id)
    await _add_item(client, headers, order["id"])
    response = await client.post(f"/api/v1/purchase-orders/{order['id']}/confirm", headers=headers)
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


async def _get_document(client: AsyncClient, headers: dict[str, str], order_id: str) -> Any:
    return await client.get(f"/api/v1/purchase-orders/{order_id}/document", headers=headers)


class TestDocumentEndpointAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/purchase-orders/{uuid.uuid4()}/document")
        assert response.status_code == 401

    async def test_requires_purchase_order_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        admin_headers = await _admin_headers(client)
        order = await _confirmed_order_with_item(client, admin_headers)

        no_view_headers = await _make_user_headers(db_session, tenant_id, [])
        response = await _get_document(client, no_view_headers, order["id"])
        assert response.status_code == 403

    async def test_purchase_order_view_permission_alone_is_sufficient(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """purchase_order:view alone (no create/edit/confirm) must be
        enough to download the document - no new permission
        (purchase_order:export/download/document) is introduced by this
        endpoint."""
        tenant_id = await _admin_tenant_id(client)
        admin_headers = await _admin_headers(client)
        order = await _confirmed_order_with_item(client, admin_headers)

        view_only_headers = await _make_user_headers(db_session, tenant_id, ["purchase_order:view"])
        response = await _get_document(client, view_only_headers, order["id"])
        assert response.status_code == 200


class TestSuccessfulDownload:
    async def test_downloads_a_pdf_for_a_confirmed_purchase_order(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        order = await _confirmed_order_with_item(client, headers)

        response = await _get_document(client, headers, order["id"])

        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")
        assert len(response.content) > 0

    async def test_content_type_is_application_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        order = await _confirmed_order_with_item(client, headers)

        response = await _get_document(client, headers, order["id"])

        assert response.headers["content-type"] == "application/pdf"

    async def test_content_disposition_is_attachment_with_the_expected_filename(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        order = await _confirmed_order_with_item(client, headers)

        response = await _get_document(client, headers, order["id"])

        expected_filename = build_document_filename(
            DocumentType.PURCHASE_ORDER, order["po_number"], extension="pdf"
        )
        content_disposition = response.headers["content-disposition"]
        assert content_disposition.startswith("attachment;")
        assert f'filename="{expected_filename}"' in content_disposition

    async def test_po_number_appears_in_the_rendered_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        order = await _confirmed_order_with_item(client, headers)

        response = await _get_document(client, headers, order["id"])

        assert order["po_number"] is not None
        assert order["po_number"].encode() in response.content

    async def test_supplier_name_appears_in_the_rendered_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers, name="Konkan Seafoods Supply Co")
        order = await _confirmed_order_with_item(client, headers, supplier_id=supplier["id"])

        response = await _get_document(client, headers, order["id"])

        assert b"Konkan Seafoods Supply Co" in response.content

    async def test_rendered_pdf_carries_no_payment_or_outstanding_information(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        order = await _confirmed_order_with_item(client, headers)

        response = await _get_document(client, headers, order["id"])

        assert b"Paid" not in response.content
        assert b"Balance" not in response.content
        assert b"Outstanding" not in response.content

    async def test_multi_item_purchase_order_downloads_successfully(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        order = await _create_purchase_order(client, headers)
        for i in range(12):
            await _add_item(client, headers, order["id"], description=f"Item {i}")
        confirm_response = await client.post(
            f"/api/v1/purchase-orders/{order['id']}/confirm", headers=headers
        )
        assert confirm_response.status_code == 200, confirm_response.text

        response = await _get_document(client, headers, order["id"])
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")


class TestNotFoundAndBusinessRuleFailures:
    async def test_returns_404_for_an_unknown_purchase_order(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await _get_document(client, headers, str(uuid.uuid4()))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_ORDER_NOT_FOUND"

    async def test_returns_422_for_a_draft_purchase_order(self, client: AsyncClient) -> None:
        """A draft purchase order has no po_number yet - there is nothing
        to print, and the endpoint must fail cleanly rather than generate
        a document with a missing/fake number."""
        headers = await _admin_headers(client)
        order = await _create_purchase_order(client, headers)
        await _add_item(client, headers, order["id"])

        response = await _get_document(client, headers, order["id"])

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PURCHASE_ORDER_DOCUMENT_NOT_AVAILABLE"

    async def test_returns_422_for_a_purchase_order_cancelled_directly_from_draft(
        self, client: AsyncClient
    ) -> None:
        """A purchase order cancelled straight from draft never received a
        po_number either - this is the one lifecycle branch Purchase Bill
        can't reach but Purchase Order can (cancel is DRAFT|CONFIRMED ->
        CANCELLED), so it needs its own explicit coverage."""
        headers = await _admin_headers(client)
        order = await _create_purchase_order(client, headers)
        await _add_item(client, headers, order["id"])
        cancel_response = await client.post(
            f"/api/v1/purchase-orders/{order['id']}/cancel", headers=headers
        )
        assert cancel_response.status_code == 200, cancel_response.text

        response = await _get_document(client, headers, order["id"])

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PURCHASE_ORDER_DOCUMENT_NOT_AVAILABLE"

    async def test_returns_200_for_a_purchase_order_cancelled_after_confirmation(
        self, client: AsyncClient
    ) -> None:
        """A purchase order confirmed and then cancelled keeps its
        po_number - the "cancelled finalized records keep their document"
        precedent means it should still be printable."""
        headers = await _admin_headers(client)
        order = await _confirmed_order_with_item(client, headers)
        cancel_response = await client.post(
            f"/api/v1/purchase-orders/{order['id']}/cancel", headers=headers
        )
        assert cancel_response.status_code == 200, cancel_response.text

        response = await _get_document(client, headers, order["id"])
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")


class TestTenantIsolation:
    async def test_returns_404_for_a_purchase_order_belonging_to_another_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Other Purchase Order Document Tenant",
            slug=f"other-purchase-order-document-tenant-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_DOCUMENT_PERMISSIONS
        )
        other_order = await _confirmed_order_with_item(client, other_headers)

        admin_headers = await _admin_headers(client)
        response = await _get_document(client, admin_headers, other_order["id"])
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_ORDER_NOT_FOUND"


class TestDocumentCenterIntegration:
    """Sprint 12 Session 11: downloading a purchase order's PDF must also
    create a DocumentRecord, visible and re-downloadable through the
    Document Center - not just a one-off PDF response."""

    async def test_downloading_the_document_creates_a_document_center_record(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers, name="Document Center Supplier Co")
        order = await _confirmed_order_with_item(client, headers, supplier_id=supplier["id"])

        pdf_response = await _get_document(client, headers, order["id"])
        assert pdf_response.status_code == 200

        list_response = await client.get(
            "/api/v1/documents", params={"q": order["po_number"]}, headers=headers
        )
        assert list_response.status_code == 200
        items = list_response.json()["data"]
        assert len(items) == 1
        record = items[0]
        assert record["document_type"] == "purchase_order"
        assert record["document_number"] == order["po_number"]
        assert record["party_type"] == "supplier"
        assert record["party_id"] == supplier["id"]
        assert record["party_name"] == "Document Center Supplier Co"
        assert record["file_extension"] == "pdf"
        assert record["content_type"] == "application/pdf"
        assert record["file_size"] == len(pdf_response.content)
        assert record["generated_by_name"]
        assert record["generated_by_name"] != "System"
        assert record["source_type"] == "purchase_order"
        assert record["source_id"] == order["id"]

        download_response = await client.get(
            f"/api/v1/documents/{record['id']}/download", headers=headers
        )
        assert download_response.status_code == 200
        assert download_response.content == pdf_response.content
        assert download_response.headers["content-type"] == "application/pdf"
        assert (
            download_response.headers["content-disposition"]
            == pdf_response.headers["content-disposition"]
        )

    async def test_each_document_download_creates_a_separate_document_center_record(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        order = await _confirmed_order_with_item(client, headers)

        await _get_document(client, headers, order["id"])
        await _get_document(client, headers, order["id"])
        await _get_document(client, headers, order["id"])

        list_response = await client.get(
            "/api/v1/documents",
            params={"q": order["po_number"], "page_size": 50},
            headers=headers,
        )
        assert list_response.status_code == 200
        assert len(list_response.json()["data"]) == 3
