"""Integration tests for GET /api/v1/purchase/{id}/document (Sprint 12
Session 3). Mirrors test_purchase_posting_api.py's own helper style - a
fresh supplier/purchase-bill/item chain is provisioned per test via the
real API, then posted, so the document endpoint is exercised against a
genuinely posted bill with a real bill_number. Much simpler setup than
the Invoice document API tests (test_invoice_document_api.py): a
purchase bill item has no fish/trip-catch chain to provision.

Assertions on the rendered PDF are deliberately structural (the `%PDF`
signature, non-empty bytes, the bill number/supplier name appearing
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

# _create_purchase_bill provisions a fresh supplier via the API by default, so
# test users need supplier:create access too for that setup to succeed, plus
# purchase:post itself.
_ALL_DOCUMENT_PERMISSIONS = [
    "purchase:view",
    "purchase:create",
    "purchase:edit",
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
        "code": f"DOCSUP-{uuid.uuid4().hex[:8]}",
        "name": f"Document Supplier {uuid.uuid4().hex[:8]}",
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


async def _posted_bill_with_item(
    client: AsyncClient, headers: dict[str, str], *, supplier_id: str | None = None
) -> dict[str, Any]:
    bill = await _create_purchase_bill(client, headers, supplier_id=supplier_id)
    await _add_item(client, headers, bill["id"])
    response = await client.post(f"/api/v1/purchase/{bill['id']}/post", headers=headers)
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


async def _get_document(client: AsyncClient, headers: dict[str, str], bill_id: str) -> Any:
    return await client.get(f"/api/v1/purchase/{bill_id}/document", headers=headers)


class TestDocumentEndpointAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/purchase/{uuid.uuid4()}/document")
        assert response.status_code == 401

    async def test_requires_purchase_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        admin_headers = await _admin_headers(client)
        bill = await _posted_bill_with_item(client, admin_headers)

        no_view_headers = await _make_user_headers(db_session, tenant_id, [])
        response = await _get_document(client, no_view_headers, bill["id"])
        assert response.status_code == 403

    async def test_purchase_view_permission_alone_is_sufficient(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """purchase:view alone (no purchase:create/edit/post) must be
        enough to download the document - no new permission (purchase:
        export/download/document:purchase) is introduced by this
        endpoint."""
        tenant_id = await _admin_tenant_id(client)
        admin_headers = await _admin_headers(client)
        bill = await _posted_bill_with_item(client, admin_headers)

        view_only_headers = await _make_user_headers(db_session, tenant_id, ["purchase:view"])
        response = await _get_document(client, view_only_headers, bill["id"])
        assert response.status_code == 200


class TestSuccessfulDownload:
    async def test_downloads_a_pdf_for_a_posted_purchase_bill(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _posted_bill_with_item(client, headers)

        response = await _get_document(client, headers, bill["id"])

        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")
        assert len(response.content) > 0

    async def test_content_type_is_application_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _posted_bill_with_item(client, headers)

        response = await _get_document(client, headers, bill["id"])

        assert response.headers["content-type"] == "application/pdf"

    async def test_content_disposition_is_attachment_with_the_expected_filename(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        bill = await _posted_bill_with_item(client, headers)

        response = await _get_document(client, headers, bill["id"])

        expected_filename = build_document_filename(
            DocumentType.PURCHASE_BILL, bill["bill_number"], extension="pdf"
        )
        content_disposition = response.headers["content-disposition"]
        assert content_disposition.startswith("attachment;")
        assert f'filename="{expected_filename}"' in content_disposition

    async def test_bill_number_appears_in_the_rendered_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        bill = await _posted_bill_with_item(client, headers)

        response = await _get_document(client, headers, bill["id"])

        assert bill["bill_number"] is not None
        assert bill["bill_number"].encode() in response.content

    async def test_supplier_name_appears_in_the_rendered_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers, name="Konkan Seafoods Supply Co")
        bill = await _posted_bill_with_item(client, headers, supplier_id=supplier["id"])

        response = await _get_document(client, headers, bill["id"])

        assert b"Konkan Seafoods Supply Co" in response.content

    async def test_multi_item_purchase_bill_downloads_successfully(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        for i in range(12):
            await _add_item(client, headers, bill["id"], description=f"Item {i}")
        post_response = await client.post(f"/api/v1/purchase/{bill['id']}/post", headers=headers)
        assert post_response.status_code == 200, post_response.text

        response = await _get_document(client, headers, bill["id"])
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")


class TestNotFoundAndBusinessRuleFailures:
    async def test_returns_404_for_an_unknown_purchase_bill(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await _get_document(client, headers, str(uuid.uuid4()))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_FOUND"

    async def test_returns_422_for_a_draft_purchase_bill(self, client: AsyncClient) -> None:
        """A draft purchase bill has no bill_number yet - there is
        nothing to print, and the endpoint must fail cleanly rather
        than generate a document with a missing/fake number."""
        headers = await _admin_headers(client)
        bill = await _create_purchase_bill(client, headers)
        await _add_item(client, headers, bill["id"])

        response = await _get_document(client, headers, bill["id"])

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PURCHASE_BILL_DOCUMENT_NOT_AVAILABLE"


class TestTenantIsolation:
    async def test_returns_404_for_a_purchase_bill_belonging_to_another_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Other Purchase Document Tenant",
            slug=f"other-purchase-document-tenant-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_DOCUMENT_PERMISSIONS
        )
        other_bill = await _posted_bill_with_item(client, other_headers)

        admin_headers = await _admin_headers(client)
        response = await _get_document(client, admin_headers, other_bill["id"])
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PURCHASE_BILL_NOT_FOUND"


class TestDocumentCenterIntegration:
    """Sprint 12 Session 7: downloading a purchase bill's PDF must now
    also create a DocumentRecord, visible and re-downloadable through the
    Document Center - not just a one-off PDF response."""

    async def test_downloading_the_document_creates_a_document_center_record(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers, name="Document Center Supplier Co")
        bill = await _posted_bill_with_item(client, headers, supplier_id=supplier["id"])

        pdf_response = await _get_document(client, headers, bill["id"])
        assert pdf_response.status_code == 200

        list_response = await client.get(
            "/api/v1/documents", params={"q": bill["bill_number"]}, headers=headers
        )
        assert list_response.status_code == 200
        items = list_response.json()["data"]
        assert len(items) == 1
        record = items[0]
        assert record["document_type"] == "purchase_bill"
        assert record["document_number"] == bill["bill_number"]
        assert record["party_type"] == "supplier"
        assert record["party_id"] == supplier["id"]
        assert record["party_name"] == "Document Center Supplier Co"
        assert record["file_extension"] == "pdf"
        assert record["content_type"] == "application/pdf"
        assert record["file_size"] == len(pdf_response.content)
        assert record["generated_by_name"]
        assert record["generated_by_name"] != "System"
        assert record["source_type"] == "purchase_bill"
        assert record["source_id"] == bill["id"]

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
        bill = await _posted_bill_with_item(client, headers)

        await _get_document(client, headers, bill["id"])
        await _get_document(client, headers, bill["id"])
        await _get_document(client, headers, bill["id"])

        list_response = await client.get(
            "/api/v1/documents",
            params={"q": bill["bill_number"], "page_size": 50},
            headers=headers,
        )
        assert list_response.status_code == 200
        assert len(list_response.json()["data"]) == 3
