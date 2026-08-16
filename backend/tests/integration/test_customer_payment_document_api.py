"""Integration tests for GET /api/v1/payments/{id}/document (Sprint 12
Session 4). Mirrors test_invoice_document_api.py's own helper style for
the invoice-issuing chain (a payment allocation needs a genuinely
issued invoice to allocate against), plus a new payment-creation/
allocation/posting chain mirroring test_payment_outstanding_engine_api.py's
own conventions.

Assertions on the rendered PDF are deliberately structural (the `%PDF`
signature, non-empty bytes, the payment number/customer name appearing
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

# _create_issued_invoice provisions a fresh company/fish/boat/trip/trip-catch
# chain and issues the resulting invoice via the API, so this file's tests
# need the full chain's access, plus payment:create/post.
_ALL_DOCUMENT_PERMISSIONS = [
    "payment:view",
    "payment:create",
    "payment:edit",
    "payment:post",
    "company:view",
    "company:create",
    "company:edit",
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
        "code": f"DOCCO-{uuid.uuid4().hex[:8]}",
        "name": f"Document Customer {uuid.uuid4().hex[:8]}",
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


async def _create_issued_invoice(
    client: AsyncClient, headers: dict[str, str], *, company_id: str
) -> dict[str, Any]:
    invoice_response = await client.post(
        "/api/v1/invoices",
        json={"company_id": company_id, "invoice_date": _INVOICE_DATE},
        headers=headers,
    )
    assert invoice_response.status_code == 201, invoice_response.text
    invoice: dict[str, Any] = invoice_response.json()

    trip_catch = await _create_trip_catch(client, headers)
    item_response = await client.post(
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
    assert item_response.status_code == 201, item_response.text

    issued = await client.post(f"/api/v1/invoices/{invoice['id']}/issue", headers=headers)
    assert issued.status_code == 200, issued.text
    result: dict[str, Any] = issued.json()
    return result


async def _create_payment(
    client: AsyncClient, headers: dict[str, str], *, company_id: str, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "company_id": company_id,
        "payment_date": _PAYMENT_DATE,
        "payment_method": "cheque",
        "reference_number": "445512",
        "bank_name": "State Bank",
        "amount": "1000.00",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/payments", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_allocation(
    client: AsyncClient, headers: dict[str, str], payment_id: str, invoice_id: str, amount: str
) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/payments/{payment_id}/allocations",
        json={"invoice_id": invoice_id, "allocated_amount": amount},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _posted_payment_with_allocation(
    client: AsyncClient, headers: dict[str, str], *, company_id: str | None = None
) -> dict[str, Any]:
    if company_id is None:
        company_id = (await _create_company(client, headers))["id"]
    invoice = await _create_issued_invoice(client, headers, company_id=company_id)
    payment = await _create_payment(client, headers, company_id=company_id, amount="1000.00")
    await _create_allocation(client, headers, payment["id"], invoice["id"], "1000.00")
    response = await client.post(f"/api/v1/payments/{payment['id']}/post", headers=headers)
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


async def _get_document(client: AsyncClient, headers: dict[str, str], payment_id: str) -> Any:
    return await client.get(f"/api/v1/payments/{payment_id}/document", headers=headers)


class TestDocumentEndpointAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/payments/{uuid.uuid4()}/document")
        assert response.status_code == 401

    async def test_requires_payment_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        admin_headers = await _admin_headers(client)
        payment = await _posted_payment_with_allocation(client, admin_headers)

        no_view_headers = await _make_user_headers(db_session, tenant_id, [])
        response = await _get_document(client, no_view_headers, payment["id"])
        assert response.status_code == 403

    async def test_payment_view_permission_alone_is_sufficient(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """payment:view alone (no payment:create/edit/post) must be
        enough to download the receipt - no new permission (customer_
        payment:view/payment:export/receipt:download) is introduced by
        this endpoint."""
        tenant_id = await _admin_tenant_id(client)
        admin_headers = await _admin_headers(client)
        payment = await _posted_payment_with_allocation(client, admin_headers)

        view_only_headers = await _make_user_headers(db_session, tenant_id, ["payment:view"])
        response = await _get_document(client, view_only_headers, payment["id"])
        assert response.status_code == 200


class TestSuccessfulDownload:
    async def test_downloads_a_pdf_for_a_posted_payment(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _posted_payment_with_allocation(client, headers)

        response = await _get_document(client, headers, payment["id"])

        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")
        assert len(response.content) > 0

    async def test_content_type_is_application_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _posted_payment_with_allocation(client, headers)

        response = await _get_document(client, headers, payment["id"])

        assert response.headers["content-type"] == "application/pdf"

    async def test_content_disposition_is_attachment_with_the_expected_filename(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        payment = await _posted_payment_with_allocation(client, headers)

        response = await _get_document(client, headers, payment["id"])

        expected_filename = build_document_filename(
            DocumentType.CUSTOMER_PAYMENT_RECEIPT, payment["payment_number"], extension="pdf"
        )
        content_disposition = response.headers["content-disposition"]
        assert content_disposition.startswith("attachment;")
        assert f'filename="{expected_filename}"' in content_disposition

    async def test_payment_number_appears_in_the_rendered_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        payment = await _posted_payment_with_allocation(client, headers)

        response = await _get_document(client, headers, payment["id"])

        assert payment["payment_number"] is not None
        assert payment["payment_number"].encode() in response.content

    async def test_customer_name_appears_in_the_rendered_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers, name="Konkan Seafoods Traders")
        payment = await _posted_payment_with_allocation(client, headers, company_id=company["id"])

        response = await _get_document(client, headers, payment["id"])

        assert b"Konkan Seafoods Traders" in response.content

    async def test_allocated_invoice_number_appears_in_the_rendered_pdf(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        invoice = await _create_issued_invoice(client, headers, company_id=company["id"])
        payment = await _create_payment(client, headers, company_id=company["id"], amount="1000.00")
        await _create_allocation(client, headers, payment["id"], invoice["id"], "1000.00")
        post_response = await client.post(f"/api/v1/payments/{payment['id']}/post", headers=headers)
        assert post_response.status_code == 200, post_response.text
        posted_payment: dict[str, Any] = post_response.json()

        response = await _get_document(client, headers, posted_payment["id"])

        assert invoice["invoice_number"] is not None
        assert invoice["invoice_number"].encode() in response.content


class TestNotFoundAndBusinessRuleFailures:
    async def test_returns_404_for_an_unknown_payment(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await _get_document(client, headers, str(uuid.uuid4()))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_NOT_FOUND"

    async def test_returns_422_for_a_draft_payment(self, client: AsyncClient) -> None:
        """A draft payment has no payment_number yet - there is nothing
        to print, and the endpoint must fail cleanly rather than
        generate a document with a missing/fake number."""
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        payment = await _create_payment(client, headers, company_id=company["id"])

        response = await _get_document(client, headers, payment["id"])

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "PAYMENT_DOCUMENT_NOT_AVAILABLE"


class TestTenantIsolation:
    async def test_returns_404_for_a_payment_belonging_to_another_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Other Payment Document Tenant",
            slug=f"other-payment-document-tenant-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_DOCUMENT_PERMISSIONS
        )
        other_payment = await _posted_payment_with_allocation(client, other_headers)

        admin_headers = await _admin_headers(client)
        response = await _get_document(client, admin_headers, other_payment["id"])
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_NOT_FOUND"


class TestDocumentCenterIntegration:
    """Sprint 12 Session 7: downloading a customer payment receipt PDF
    must now also create a DocumentRecord, visible and re-downloadable
    through the Document Center - not just a one-off PDF response."""

    async def test_downloading_the_document_creates_a_document_center_record(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers, name="Document Center Receipt Co")
        payment = await _posted_payment_with_allocation(client, headers, company_id=company["id"])

        pdf_response = await _get_document(client, headers, payment["id"])
        assert pdf_response.status_code == 200

        list_response = await client.get(
            "/api/v1/documents", params={"q": payment["payment_number"]}, headers=headers
        )
        assert list_response.status_code == 200
        items = list_response.json()["data"]
        assert len(items) == 1
        record = items[0]
        assert record["document_type"] == "customer_payment_receipt"
        assert record["document_number"] == payment["payment_number"]
        assert record["party_type"] == "customer"
        assert record["party_id"] == company["id"]
        assert record["party_name"] == "Document Center Receipt Co"
        assert record["file_extension"] == "pdf"
        assert record["content_type"] == "application/pdf"
        assert record["file_size"] == len(pdf_response.content)
        assert record["generated_by_name"]
        assert record["generated_by_name"] != "System"
        assert record["source_type"] == "payment"
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
        payment = await _posted_payment_with_allocation(client, headers)

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
