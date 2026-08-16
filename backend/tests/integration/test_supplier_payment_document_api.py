"""Integration tests for GET /api/v1/supplier-payments/{id}/document
(Sprint 12 Session 4). Mirrors test_customer_payment_document_api.py's
own style, simplified: a supplier payment allocation only needs a
posted purchase bill (no fish/trip-catch chain - a purchase bill item
is plain description/quantity/unit/rate, per Session 3's own findings).

Assertions on the rendered PDF are deliberately structural (the `%PDF`
signature, non-empty bytes, the payment number/supplier name appearing
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

_ALL_DOCUMENT_PERMISSIONS = [
    "supplier_payment:view",
    "supplier_payment:create",
    "supplier_payment:edit",
    "supplier_payment:post",
    "supplier:view",
    "supplier:create",
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
        "code": f"DOCSUP-{uuid.uuid4().hex[:8]}",
        "name": f"Document Supplier {uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/suppliers", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_posted_purchase_bill(
    client: AsyncClient, headers: dict[str, str], *, supplier_id: str
) -> dict[str, Any]:
    bill_response = await client.post(
        "/api/v1/purchase",
        json={"supplier_id": supplier_id, "bill_date": _BILL_DATE},
        headers=headers,
    )
    assert bill_response.status_code == 201, bill_response.text
    bill: dict[str, Any] = bill_response.json()

    item_response = await client.post(
        f"/api/v1/purchase/{bill['id']}/items",
        json={
            "description": "Pomfret - Grade A",
            "quantity": "10.000",
            "unit": "KG",
            "rate": "100.0000",
        },
        headers=headers,
    )
    assert item_response.status_code == 201, item_response.text

    posted = await client.post(f"/api/v1/purchase/{bill['id']}/post", headers=headers)
    assert posted.status_code == 200, posted.text
    result: dict[str, Any] = posted.json()
    return result


async def _create_supplier_payment(
    client: AsyncClient, headers: dict[str, str], *, supplier_id: str, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "supplier_id": supplier_id,
        "payment_date": _PAYMENT_DATE,
        "payment_method": "cheque",
        "reference_number": "778821",
        "bank_name": "State Bank",
        "amount": "1000.00",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/supplier-payments", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_allocation(
    client: AsyncClient,
    headers: dict[str, str],
    supplier_payment_id: str,
    purchase_bill_id: str,
    amount: str,
) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/supplier-payments/{supplier_payment_id}/allocations",
        json={"purchase_bill_id": purchase_bill_id, "allocated_amount": amount},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _posted_supplier_payment_with_allocation(
    client: AsyncClient, headers: dict[str, str], *, supplier_id: str | None = None
) -> dict[str, Any]:
    if supplier_id is None:
        supplier_id = (await _create_supplier(client, headers))["id"]
    purchase_bill = await _create_posted_purchase_bill(client, headers, supplier_id=supplier_id)
    payment = await _create_supplier_payment(
        client, headers, supplier_id=supplier_id, amount="1000.00"
    )
    await _create_allocation(client, headers, payment["id"], purchase_bill["id"], "1000.00")
    response = await client.post(f"/api/v1/supplier-payments/{payment['id']}/post", headers=headers)
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


async def _get_document(
    client: AsyncClient, headers: dict[str, str], supplier_payment_id: str
) -> Any:
    return await client.get(
        f"/api/v1/supplier-payments/{supplier_payment_id}/document", headers=headers
    )


class TestDocumentEndpointAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/supplier-payments/{uuid.uuid4()}/document")
        assert response.status_code == 401

    async def test_requires_supplier_payment_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        admin_headers = await _admin_headers(client)
        payment = await _posted_supplier_payment_with_allocation(client, admin_headers)

        no_view_headers = await _make_user_headers(db_session, tenant_id, [])
        response = await _get_document(client, no_view_headers, payment["id"])
        assert response.status_code == 403

    async def test_supplier_payment_view_permission_alone_is_sufficient(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """supplier_payment:view alone (no create/edit/post) must be
        enough to download the receipt - no new permission is
        introduced by this endpoint."""
        tenant_id = await _admin_tenant_id(client)
        admin_headers = await _admin_headers(client)
        payment = await _posted_supplier_payment_with_allocation(client, admin_headers)

        view_only_headers = await _make_user_headers(
            db_session, tenant_id, ["supplier_payment:view"]
        )
        response = await _get_document(client, view_only_headers, payment["id"])
        assert response.status_code == 200


class TestSuccessfulDownload:
    async def test_downloads_a_pdf_for_a_posted_supplier_payment(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _posted_supplier_payment_with_allocation(client, headers)

        response = await _get_document(client, headers, payment["id"])

        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")
        assert len(response.content) > 0

    async def test_content_type_is_application_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _posted_supplier_payment_with_allocation(client, headers)

        response = await _get_document(client, headers, payment["id"])

        assert response.headers["content-type"] == "application/pdf"

    async def test_content_disposition_is_attachment_with_the_expected_filename(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _posted_supplier_payment_with_allocation(client, headers)

        response = await _get_document(client, headers, payment["id"])

        expected_filename = build_document_filename(
            DocumentType.SUPPLIER_PAYMENT_RECEIPT, payment["payment_number"], extension="pdf"
        )
        content_disposition = response.headers["content-disposition"]
        assert content_disposition.startswith("attachment;")
        assert f'filename="{expected_filename}"' in content_disposition

    async def test_payment_number_appears_in_the_rendered_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _posted_supplier_payment_with_allocation(client, headers)

        response = await _get_document(client, headers, payment["id"])

        assert payment["payment_number"] is not None
        assert payment["payment_number"].encode() in response.content

    async def test_supplier_name_appears_in_the_rendered_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers, name="Konkan Seafoods Supply Co")
        payment = await _posted_supplier_payment_with_allocation(
            client, headers, supplier_id=supplier["id"]
        )

        response = await _get_document(client, headers, payment["id"])

        assert b"Konkan Seafoods Supply Co" in response.content

    async def test_allocated_bill_number_appears_in_the_rendered_pdf(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        purchase_bill = await _create_posted_purchase_bill(
            client, headers, supplier_id=supplier["id"]
        )
        payment = await _create_supplier_payment(
            client, headers, supplier_id=supplier["id"], amount="1000.00"
        )
        await _create_allocation(client, headers, payment["id"], purchase_bill["id"], "1000.00")
        post_response = await client.post(
            f"/api/v1/supplier-payments/{payment['id']}/post", headers=headers
        )
        assert post_response.status_code == 200, post_response.text
        posted_payment: dict[str, Any] = post_response.json()

        response = await _get_document(client, headers, posted_payment["id"])

        assert purchase_bill["bill_number"] is not None
        assert purchase_bill["bill_number"].encode() in response.content


class TestNotFoundAndBusinessRuleFailures:
    async def test_returns_404_for_an_unknown_supplier_payment(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await _get_document(client, headers, str(uuid.uuid4()))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_NOT_FOUND"

    async def test_returns_422_for_a_draft_supplier_payment(self, client: AsyncClient) -> None:
        """A draft supplier payment has no payment_number yet - there is
        nothing to print, and the endpoint must fail cleanly rather than
        generate a document with a missing/fake number."""
        headers = await _admin_headers(client)
        supplier = await _create_supplier(client, headers)
        payment = await _create_supplier_payment(client, headers, supplier_id=supplier["id"])

        response = await _get_document(client, headers, payment["id"])

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_DOCUMENT_NOT_AVAILABLE"


class TestTenantIsolation:
    async def test_returns_404_for_a_supplier_payment_belonging_to_another_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Other Supplier Payment Document Tenant",
            slug=f"other-supplier-payment-document-tenant-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_DOCUMENT_PERMISSIONS
        )
        other_payment = await _posted_supplier_payment_with_allocation(client, other_headers)

        admin_headers = await _admin_headers(client)
        response = await _get_document(client, admin_headers, other_payment["id"])
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SUPPLIER_PAYMENT_NOT_FOUND"


class TestDocumentCenterIntegration:
    """Sprint 12 Session 7: downloading a supplier payment receipt PDF
    must now also create a DocumentRecord, visible and re-downloadable
    through the Document Center - not just a one-off PDF response."""

    async def test_downloading_the_document_creates_a_document_center_record(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        supplier = await _create_supplier(
            client, headers, name="Document Center Supplier Receipt Co"
        )
        payment = await _posted_supplier_payment_with_allocation(
            client, headers, supplier_id=supplier["id"]
        )

        pdf_response = await _get_document(client, headers, payment["id"])
        assert pdf_response.status_code == 200

        list_response = await client.get(
            "/api/v1/documents", params={"q": payment["payment_number"]}, headers=headers
        )
        assert list_response.status_code == 200
        items = list_response.json()["data"]
        assert len(items) == 1
        record = items[0]
        assert record["document_type"] == "supplier_payment_receipt"
        assert record["document_number"] == payment["payment_number"]
        assert record["party_type"] == "supplier"
        assert record["party_id"] == supplier["id"]
        assert record["party_name"] == "Document Center Supplier Receipt Co"
        assert record["file_extension"] == "pdf"
        assert record["content_type"] == "application/pdf"
        assert record["file_size"] == len(pdf_response.content)
        assert record["generated_by_name"]
        assert record["generated_by_name"] != "System"
        assert record["source_type"] == "supplier_payment"
        assert record["source_id"] == payment["id"]

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
        payment = await _posted_supplier_payment_with_allocation(client, headers)

        await _get_document(client, headers, payment["id"])
        await _get_document(client, headers, payment["id"])
        await _get_document(client, headers, payment["id"])

        list_response = await client.get(
            "/api/v1/documents",
            params={"q": payment["payment_number"], "page_size": 50},
            headers=headers,
        )
        assert list_response.status_code == 200
        assert len(list_response.json()["data"]) == 3
