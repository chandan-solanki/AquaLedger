"""Integration tests for GET /api/v1/invoices/{id}/document (Sprint 12
Session 2). Mirrors test_invoice_issue_api.py's own helper style exactly
- a fresh company/fish/boat/trip/trip-catch/invoice chain is provisioned
per test via the real API, then issued, so the document endpoint is
exercised against a genuinely issued invoice with a real invoice_number.

Assertions on the rendered PDF are deliberately structural (the `%PDF`
signature, non-empty bytes, the invoice number/customer name appearing
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

# _create_invoice_item provisions a fresh trip catch (and that trip catch's
# fish, trip, boat and company) via the API by default, so a user needs the
# full chain's access for that setup to succeed, plus invoice:issue itself -
# the same chain test_invoice_issue_api.py needs, since this file also issues
# every invoice it downloads a document for.
_ALL_DOCUMENT_PERMISSIONS = [
    "invoice:view",
    "invoice:create",
    "invoice:edit",
    "invoice:issue",
    "company:view",
    "company:create",
    "company:edit",
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
        "code": f"DOCCO-{uuid.uuid4().hex[:8]}",
        "name": f"Document Customer {uuid.uuid4().hex[:8]}",
        "company_type": "customer",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/companies", json=payload, headers=headers)
    assert response.status_code == 201, response.text
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
        "code": f"DOCFISH-{uuid.uuid4().hex[:8]}",
        "name": f"Pomfret {uuid.uuid4().hex[:8]}",
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
        "code": f"DOCB-{uuid.uuid4().hex[:8]}",
        "name": f"Document Boat {uuid.uuid4().hex[:8]}",
        "registration_number": f"DOCREG-{uuid.uuid4().hex[:8]}",
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
        "trip_number": f"DOCTRIP-{uuid.uuid4().hex[:8]}",
        "trip_type": "fishing",
        "departure_datetime": _DEPARTURE,
    }
    payload.update(overrides)
    response = await client.post("/api/v1/trips", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    trip: dict[str, Any] = response.json()

    response = await client.put(
        f"/api/v1/trips/{trip['id']}",
        json={"status": "returned", "actual_return_datetime": _RETURN},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
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


async def _create_invoice_item(
    client: AsyncClient, headers: dict[str, str], invoice_id: str, **overrides: Any
) -> dict[str, Any]:
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


async def _issued_invoice_with_item(
    client: AsyncClient, headers: dict[str, str], *, company_id: str | None = None
) -> dict[str, Any]:
    invoice = await _create_invoice(client, headers, company_id=company_id)
    await _create_invoice_item(client, headers, invoice["id"])
    response = await client.post(f"/api/v1/invoices/{invoice['id']}/issue", headers=headers)
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


async def _get_document(client: AsyncClient, headers: dict[str, str], invoice_id: str) -> Any:
    return await client.get(f"/api/v1/invoices/{invoice_id}/document", headers=headers)


class TestDocumentEndpointAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/invoices/{uuid.uuid4()}/document")
        assert response.status_code == 401

    async def test_requires_invoice_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        admin_headers = await _admin_headers(client)
        invoice = await _issued_invoice_with_item(client, admin_headers)

        no_view_headers = await _make_user_headers(db_session, tenant_id, [])
        response = await _get_document(client, no_view_headers, invoice["id"])
        assert response.status_code == 403

    async def test_invoice_view_permission_alone_is_sufficient(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """invoice:view alone (no invoice:create/edit/issue) must be
        enough to download the document - no new permission (invoice:
        export/download/document:invoice) is introduced by this
        endpoint."""
        tenant_id = await _admin_tenant_id(client)
        admin_headers = await _admin_headers(client)
        invoice = await _issued_invoice_with_item(client, admin_headers)

        view_only_headers = await _make_user_headers(db_session, tenant_id, ["invoice:view"])
        response = await _get_document(client, view_only_headers, invoice["id"])
        assert response.status_code == 200


class TestSuccessfulDownload:
    async def test_downloads_a_pdf_for_an_issued_invoice(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _issued_invoice_with_item(client, headers)

        response = await _get_document(client, headers, invoice["id"])

        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")
        assert len(response.content) > 0

    async def test_content_type_is_application_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _issued_invoice_with_item(client, headers)

        response = await _get_document(client, headers, invoice["id"])

        assert response.headers["content-type"] == "application/pdf"

    async def test_content_disposition_is_attachment_with_the_expected_filename(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        invoice = await _issued_invoice_with_item(client, headers)

        response = await _get_document(client, headers, invoice["id"])

        expected_filename = build_document_filename(
            DocumentType.INVOICE, invoice["invoice_number"], extension="pdf"
        )
        content_disposition = response.headers["content-disposition"]
        assert content_disposition.startswith("attachment;")
        assert f'filename="{expected_filename}"' in content_disposition

    async def test_invoice_number_appears_in_the_rendered_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice = await _issued_invoice_with_item(client, headers)

        response = await _get_document(client, headers, invoice["id"])

        assert invoice["invoice_number"] is not None
        assert invoice["invoice_number"].encode() in response.content

    async def test_customer_name_appears_in_the_rendered_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers, name="Konkan Seafoods Traders")
        invoice = await _issued_invoice_with_item(client, headers, company_id=company["id"])

        response = await _get_document(client, headers, invoice["id"])

        assert b"Konkan Seafoods Traders" in response.content


class TestNotFoundAndBusinessRuleFailures:
    async def test_returns_404_for_an_unknown_invoice(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await _get_document(client, headers, str(uuid.uuid4()))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVOICE_NOT_FOUND"

    async def test_returns_422_for_a_draft_invoice(self, client: AsyncClient) -> None:
        """A draft invoice has no invoice_number yet - there is nothing
        to print, and the endpoint must fail cleanly rather than
        generate a document with a missing/fake number."""
        headers = await _admin_headers(client)
        invoice = await _create_invoice(client, headers)
        await _create_invoice_item(client, headers, invoice["id"])

        response = await _get_document(client, headers, invoice["id"])

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVOICE_DOCUMENT_NOT_AVAILABLE"


class TestTenantIsolation:
    async def test_returns_404_for_an_invoice_belonging_to_another_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Other Document Tenant", slug=f"other-document-tenant-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_DOCUMENT_PERMISSIONS
        )
        other_invoice = await _issued_invoice_with_item(client, other_headers)

        admin_headers = await _admin_headers(client)
        response = await _get_document(client, admin_headers, other_invoice["id"])
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INVOICE_NOT_FOUND"


class TestDocumentCenterIntegration:
    """Sprint 12 Session 7: downloading an invoice's PDF must now also
    create a DocumentRecord, visible and re-downloadable through the
    Document Center - not just a one-off PDF response."""

    async def test_downloading_the_document_creates_a_document_center_record(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers, name="Document Center Invoice Co")
        invoice = await _issued_invoice_with_item(client, headers, company_id=company["id"])

        pdf_response = await _get_document(client, headers, invoice["id"])
        assert pdf_response.status_code == 200

        list_response = await client.get(
            "/api/v1/documents", params={"q": invoice["invoice_number"]}, headers=headers
        )
        assert list_response.status_code == 200
        items = list_response.json()["data"]
        assert len(items) == 1
        record = items[0]
        assert record["document_type"] == "invoice"
        assert record["document_number"] == invoice["invoice_number"]
        assert record["party_type"] == "customer"
        assert record["party_id"] == company["id"]
        assert record["party_name"] == "Document Center Invoice Co"
        assert record["file_extension"] == "pdf"
        assert record["content_type"] == "application/pdf"
        assert record["file_size"] == len(pdf_response.content)
        assert record["generated_by_name"]
        assert record["generated_by_name"] != "System"
        assert record["source_type"] == "invoice"
        assert record["source_id"] == invoice["id"]

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
        invoice = await _issued_invoice_with_item(client, headers)

        await _get_document(client, headers, invoice["id"])
        await _get_document(client, headers, invoice["id"])
        await _get_document(client, headers, invoice["id"])

        list_response = await client.get(
            "/api/v1/documents",
            params={"q": invoice["invoice_number"], "page_size": 50},
            headers=headers,
        )
        assert list_response.status_code == 200
        assert len(list_response.json()["data"]) == 3
