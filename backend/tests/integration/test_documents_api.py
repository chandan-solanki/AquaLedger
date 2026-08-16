"""Integration tests for GET /api/v1/documents and GET /api/v1/documents/
{id}/download (Sprint 12 Session 6: Document Center foundation).

Session 6 deliberately did not wire any existing generation endpoint
(Invoice/Purchase Bill/Payment/Supplier Payment) to create DocumentRecord
rows (see the Session 6 deliverable's "Document Generation Integration
Decision") - so most tests here seed history rows directly via
DocumentRecordService.record_generated_document(), then exercise the real
HTTP list/download endpoints against that seeded data.

Session 7 wired all four business modules to the Document Center (see
app.modules.documents.service.DocumentRecordService.generate_store_and_record
and each of test_invoice_document_api.py/test_purchase_bill_document_api.py/
test_customer_payment_document_api.py/test_supplier_payment_document_api.py's
own new TestDocumentCenterIntegration classes, which each verify their own
document type end to end). TestRealGenerationFlowsPopulateTheDocumentCenter
below is the one addition here: it proves multiple *different* real
document types, generated through their own real endpoints, coexist and
remain correctly distinguishable in one shared list - something no
single per-module file can demonstrate on its own.
"""

import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.document_engine.document_types import DocumentType
from app.core.document_engine.storage import LocalStorageService
from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.documents.constants import PartyType, SourceType
from app.modules.documents.schemas import DocumentRecordCreate
from app.modules.documents.service import DocumentRecordService

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"


async def _login(client: AsyncClient) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
    )
    result: dict[str, Any] = response.json()
    return result


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    body = await _login(client)
    return {"Authorization": f"Bearer {body['access_token']}"}


async def _admin_tenant_id(client: AsyncClient) -> uuid.UUID:
    body = await _login(client)
    return uuid.UUID(body["user"]["tenant_id"])


async def _admin_user_id(client: AsyncClient) -> uuid.UUID:
    body = await _login(client)
    return uuid.UUID(body["user"]["id"])


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


async def _seed_document(
    db_session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    generated_by: uuid.UUID,
    save_file: bool = True,
    **overrides: Any,
) -> dict[str, Any]:
    """Seeds one DocumentRecord via the real service call, optionally
    writing real bytes to the real configured storage root (`save_file`)
    so the download endpoint's StorageService.load() succeeds end to end
    - the same LocalStorageService a production caller would use."""
    document_type = overrides.pop("document_type", DocumentType.INVOICE)
    document_number = overrides.pop("document_number", f"INV/2026-27/{uuid.uuid4().hex[:5]}")
    file_name = overrides.pop("file_name", f"Invoice_{document_number.replace('/', '')}.pdf")
    storage_key = f"{tenant_id}/documents/{document_type.value}/{file_name}"

    if save_file:
        LocalStorageService().save(
            storage_key, b"%PDF-1.4 fake document center bytes", content_type="application/pdf"
        )

    service = DocumentRecordService(db_session)
    payload = {
        "tenant_id": tenant_id,
        "document_type": document_type,
        "document_number": document_number,
        "file_name": file_name,
        "file_extension": "pdf",
        "content_type": "application/pdf",
        "storage_key": storage_key,
        "file_size": 42,
        "generated_by": generated_by,
        **overrides,
    }
    response = await service.record_generated_document(DocumentRecordCreate(**payload))
    return response.model_dump(mode="json")


class TestAuthentication:
    async def test_list_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/documents")
        assert response.status_code == 401

    async def test_download_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/documents/{uuid.uuid4()}/download")
        assert response.status_code == 401


class TestPermission:
    async def test_list_requires_document_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get("/api/v1/documents", headers=headers)
        assert response.status_code == 403

    async def test_document_view_permission_alone_is_sufficient_to_list(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["document:view"])
        response = await client.get("/api/v1/documents", headers=headers)
        assert response.status_code == 200

    async def test_document_view_permission_alone_is_sufficient_to_download(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        admin_id = await _admin_user_id(client)
        record = await _seed_document(db_session, tenant_id=tenant_id, generated_by=admin_id)

        headers = await _make_user_headers(db_session, tenant_id, ["document:view"])
        response = await client.get(f"/api/v1/documents/{record['id']}/download", headers=headers)
        assert response.status_code == 200


class TestListDocuments:
    async def test_lists_a_seeded_document(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        admin_id = await _admin_user_id(client)
        record = await _seed_document(db_session, tenant_id=tenant_id, generated_by=admin_id)

        response = await client.get("/api/v1/documents", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert any(item["id"] == record["id"] for item in body["data"])
        assert "storage_key" not in body["data"][0]

    async def test_filters_by_document_type(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        admin_id = await _admin_user_id(client)
        invoice = await _seed_document(
            db_session,
            tenant_id=tenant_id,
            generated_by=admin_id,
            document_type=DocumentType.INVOICE,
        )
        await _seed_document(
            db_session,
            tenant_id=tenant_id,
            generated_by=admin_id,
            document_type=DocumentType.PURCHASE_BILL,
            document_number=f"PB/2026-27/{uuid.uuid4().hex[:5]}",
        )

        response = await client.get(
            "/api/v1/documents", params={"document_type": "invoice"}, headers=headers
        )

        assert response.status_code == 200
        body = response.json()
        assert all(item["document_type"] == "invoice" for item in body["data"])
        assert any(item["id"] == invoice["id"] for item in body["data"])

    async def test_filters_by_party(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        admin_id = await _admin_user_id(client)
        party_id = uuid.uuid4()
        target = await _seed_document(
            db_session,
            tenant_id=tenant_id,
            generated_by=admin_id,
            party_type=PartyType.CUSTOMER,
            party_id=party_id,
            party_name="ABC Sea Food",
        )
        await _seed_document(
            db_session,
            tenant_id=tenant_id,
            generated_by=admin_id,
            party_type=PartyType.CUSTOMER,
            party_id=uuid.uuid4(),
            party_name="Someone Else",
        )

        response = await client.get(
            "/api/v1/documents",
            params={"party_type": "customer", "party_id": str(party_id)},
            headers=headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["id"] == target["id"]

    async def test_search_matches_document_number(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        admin_id = await _admin_user_id(client)
        unique_number = f"INV/2026-27/{uuid.uuid4().hex[:8]}"
        target = await _seed_document(
            db_session, tenant_id=tenant_id, generated_by=admin_id, document_number=unique_number
        )

        response = await client.get(
            "/api/v1/documents", params={"q": unique_number}, headers=headers
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["id"] == target["id"]

    async def test_pagination_response_shape(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        admin_id = await _admin_user_id(client)
        await _seed_document(db_session, tenant_id=tenant_id, generated_by=admin_id)

        response = await client.get(
            "/api/v1/documents", params={"page": 1, "page_size": 1}, headers=headers
        )

        assert response.status_code == 200
        meta = response.json()["meta"]
        assert meta["current_page"] == 1
        assert meta["page_size"] == 1
        assert meta["total_records"] >= 1

    async def test_empty_result_for_a_search_that_matches_nothing(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        admin_id = await _admin_user_id(client)
        await _seed_document(db_session, tenant_id=tenant_id, generated_by=admin_id)

        response = await client.get(
            "/api/v1/documents", params={"q": "no-such-document-exists"}, headers=headers
        )

        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert body["meta"]["total_records"] == 0


class TestSourceMetadata:
    """Sprint 12 Session 8: source_type/source_id let the frontend link
    Document Number straight to its source record's own detail page."""

    async def test_source_metadata_is_returned_when_set(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        admin_id = await _admin_user_id(client)
        source_id = uuid.uuid4()
        record = await _seed_document(
            db_session,
            tenant_id=tenant_id,
            generated_by=admin_id,
            source_type=SourceType.INVOICE,
            source_id=source_id,
        )

        response = await client.get("/api/v1/documents", headers=headers)

        assert response.status_code == 200
        item = next(i for i in response.json()["data"] if i["id"] == record["id"])
        assert item["source_type"] == "invoice"
        assert item["source_id"] == str(source_id)

    async def test_old_records_with_null_source_fields_remain_valid(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Every DocumentRecord created before Session 8 (Sessions 6/7)
        has no source_type/source_id at all - it must still list,
        filter and download exactly as before, with source fields simply
        null rather than an error."""
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        admin_id = await _admin_user_id(client)
        record = await _seed_document(db_session, tenant_id=tenant_id, generated_by=admin_id)

        list_response = await client.get("/api/v1/documents", headers=headers)
        assert list_response.status_code == 200
        item = next(i for i in list_response.json()["data"] if i["id"] == record["id"])
        assert item["source_type"] is None
        assert item["source_id"] is None

        download_response = await client.get(
            f"/api/v1/documents/{record['id']}/download", headers=headers
        )
        assert download_response.status_code == 200


class TestSuccessfulDownload:
    async def test_downloads_the_stored_bytes(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        admin_id = await _admin_user_id(client)
        record = await _seed_document(db_session, tenant_id=tenant_id, generated_by=admin_id)

        response = await client.get(f"/api/v1/documents/{record['id']}/download", headers=headers)

        assert response.status_code == 200
        assert response.content == b"%PDF-1.4 fake document center bytes"

    async def test_content_type_matches_the_stored_content_type(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        admin_id = await _admin_user_id(client)
        record = await _seed_document(db_session, tenant_id=tenant_id, generated_by=admin_id)

        response = await client.get(f"/api/v1/documents/{record['id']}/download", headers=headers)

        assert response.headers["content-type"] == "application/pdf"

    async def test_content_disposition_uses_the_stored_file_name(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        admin_id = await _admin_user_id(client)
        record = await _seed_document(db_session, tenant_id=tenant_id, generated_by=admin_id)

        response = await client.get(f"/api/v1/documents/{record['id']}/download", headers=headers)

        content_disposition = response.headers["content-disposition"]
        assert content_disposition.startswith("attachment;")
        assert f'filename="{record["file_name"]}"' in content_disposition


class TestNotFoundAndMissingFile:
    async def test_returns_404_for_an_unknown_document_id(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(f"/api/v1/documents/{uuid.uuid4()}/download", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DOCUMENT_RECORD_NOT_FOUND"

    async def test_returns_404_when_the_record_exists_but_its_file_does_not(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        admin_id = await _admin_user_id(client)
        record = await _seed_document(
            db_session, tenant_id=tenant_id, generated_by=admin_id, save_file=False
        )

        response = await client.get(f"/api/v1/documents/{record['id']}/download", headers=headers)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DOCUMENT_FILE_MISSING"


class TestTenantIsolation:
    async def test_another_tenants_document_never_appears_in_the_list(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Other Documents Tenant", slug=f"other-documents-tenant-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_user = User(
            tenant_id=other_tenant.id,
            email=f"user-{uuid.uuid4().hex[:8]}@fisherp.local",
            username=f"user-{uuid.uuid4().hex[:8]}",
            password_hash=hash_password("Whatever@123"),
            full_name="Other Tenant User",
            status=AccountStatus.ACTIVE,
            is_superuser=False,
        )
        db_session.add(other_user)
        await db_session.commit()
        other_record = await _seed_document(
            db_session, tenant_id=other_tenant.id, generated_by=other_user.id
        )

        admin_headers = await _admin_headers(client)
        response = await client.get("/api/v1/documents", headers=admin_headers)

        assert response.status_code == 200
        ids = {item["id"] for item in response.json()["data"]}
        assert other_record["id"] not in ids

    async def test_returns_404_downloading_another_tenants_document(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Other Documents Download Tenant",
            slug=f"other-documents-download-tenant-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_user = User(
            tenant_id=other_tenant.id,
            email=f"user-{uuid.uuid4().hex[:8]}@fisherp.local",
            username=f"user-{uuid.uuid4().hex[:8]}",
            password_hash=hash_password("Whatever@123"),
            full_name="Other Tenant User",
            status=AccountStatus.ACTIVE,
            is_superuser=False,
        )
        db_session.add(other_user)
        await db_session.commit()
        other_record = await _seed_document(
            db_session, tenant_id=other_tenant.id, generated_by=other_user.id
        )

        admin_headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/documents/{other_record['id']}/download", headers=admin_headers
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DOCUMENT_RECORD_NOT_FOUND"


class TestRealGenerationFlowsPopulateTheDocumentCenter:
    """Sprint 12 Session 7. Every other test in this file seeds a
    DocumentRecord directly via record_generated_document() - this class
    is the one exception: it drives two real business flows (an issued
    invoice, a posted purchase bill) through their own real document
    endpoints, then confirms both show up correctly distinguished in one
    shared /api/v1/documents list. Each per-module integration test
    (test_invoice_document_api.py etc.) already verifies its own single
    type end to end; this proves they coexist correctly together."""

    async def test_a_real_invoice_and_a_real_purchase_bill_both_appear_distinctly(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)

        company_response = await client.post(
            "/api/v1/companies",
            json={
                "code": f"RDCO-{uuid.uuid4().hex[:8]}",
                "name": "Real Flow Customer Co",
                "company_type": "customer",
            },
            headers=headers,
        )
        assert company_response.status_code == 201, company_response.text
        company = company_response.json()

        invoice_response = await client.post(
            "/api/v1/invoices",
            json={"company_id": company["id"], "invoice_date": "2026-08-15"},
            headers=headers,
        )
        assert invoice_response.status_code == 201, invoice_response.text
        invoice = invoice_response.json()

        boat_response = await client.post(
            "/api/v1/boats",
            json={
                "code": f"RDB-{uuid.uuid4().hex[:8]}",
                "name": "Real Flow Boat",
                "registration_number": f"RDREG-{uuid.uuid4().hex[:8]}",
            },
            headers=headers,
        )
        assert boat_response.status_code == 201, boat_response.text
        boat = boat_response.json()

        trip_response = await client.post(
            "/api/v1/trips",
            json={
                "boat_id": boat["id"],
                "trip_number": f"RDTRIP-{uuid.uuid4().hex[:8]}",
                "trip_type": "fishing",
                "departure_datetime": "2026-06-01T04:00:00Z",
            },
            headers=headers,
        )
        assert trip_response.status_code == 201, trip_response.text
        trip = trip_response.json()
        returned_trip_response = await client.put(
            f"/api/v1/trips/{trip['id']}",
            json={"status": "returned", "actual_return_datetime": "2026-06-10T10:00:00Z"},
            headers=headers,
        )
        assert returned_trip_response.status_code == 200, returned_trip_response.text

        fish_response = await client.post(
            "/api/v1/fish",
            json={"code": f"RDFISH-{uuid.uuid4().hex[:8]}", "name": "Real Flow Pomfret"},
            headers=headers,
        )
        assert fish_response.status_code == 201, fish_response.text
        fish = fish_response.json()

        trip_catch_response = await client.post(
            "/api/v1/trip-catches",
            json={
                "trip_id": trip["id"],
                "fish_id": fish["id"],
                "quantity_caught": "100.000",
                "landing_date": "2026-06-05",
            },
            headers=headers,
        )
        assert trip_catch_response.status_code == 201, trip_catch_response.text
        trip_catch = trip_catch_response.json()

        item_response = await client.post(
            f"/api/v1/invoices/{invoice['id']}/items",
            json={
                "trip_catch_id": trip_catch["id"],
                "fish_id": fish["id"],
                "quantity": "10.000",
                "unit": "kg",
                "rate": "100.0000",
            },
            headers=headers,
        )
        assert item_response.status_code == 201, item_response.text

        issue_response = await client.post(
            f"/api/v1/invoices/{invoice['id']}/issue", headers=headers
        )
        assert issue_response.status_code == 200, issue_response.text
        invoice = issue_response.json()

        invoice_pdf_response = await client.get(
            f"/api/v1/invoices/{invoice['id']}/document", headers=headers
        )
        assert invoice_pdf_response.status_code == 200

        supplier_response = await client.post(
            "/api/v1/suppliers",
            json={"code": f"RDSUP-{uuid.uuid4().hex[:8]}", "name": "Real Flow Supplier Co"},
            headers=headers,
        )
        assert supplier_response.status_code == 201, supplier_response.text
        supplier = supplier_response.json()

        bill_response = await client.post(
            "/api/v1/purchase",
            json={"supplier_id": supplier["id"], "bill_date": "2026-08-15"},
            headers=headers,
        )
        assert bill_response.status_code == 201, bill_response.text
        bill = bill_response.json()

        bill_item_response = await client.post(
            f"/api/v1/purchase/{bill['id']}/items",
            json={
                "description": "Pomfret - Grade A",
                "quantity": "10.000",
                "unit": "KG",
                "rate": "100.0000",
            },
            headers=headers,
        )
        assert bill_item_response.status_code == 201, bill_item_response.text

        post_bill_response = await client.post(
            f"/api/v1/purchase/{bill['id']}/post", headers=headers
        )
        assert post_bill_response.status_code == 200, post_bill_response.text
        bill = post_bill_response.json()

        bill_pdf_response = await client.get(
            f"/api/v1/purchase/{bill['id']}/document", headers=headers
        )
        assert bill_pdf_response.status_code == 200

        list_response = await client.get(
            "/api/v1/documents", params={"page_size": 50}, headers=headers
        )
        assert list_response.status_code == 200
        items = list_response.json()["data"]
        invoice_record = next(r for r in items if r["document_number"] == invoice["invoice_number"])
        bill_record = next(r for r in items if r["document_number"] == bill["bill_number"])
        assert invoice_record["document_type"] == "invoice"
        assert invoice_record["party_type"] == "customer"
        assert invoice_record["source_type"] == "invoice"
        assert invoice_record["source_id"] == invoice["id"]
        assert bill_record["document_type"] == "purchase_bill"
        assert bill_record["party_type"] == "supplier"
        assert bill_record["source_type"] == "purchase_bill"
        assert bill_record["source_id"] == bill["id"]

        invoice_type_response = await client.get(
            "/api/v1/documents",
            params={"document_type": "invoice", "page_size": 50},
            headers=headers,
        )
        invoice_type_items = invoice_type_response.json()["data"]
        assert all(r["document_type"] == "invoice" for r in invoice_type_items)
        assert any(r["id"] == invoice_record["id"] for r in invoice_type_items)
        assert not any(r["id"] == bill_record["id"] for r in invoice_type_items)
