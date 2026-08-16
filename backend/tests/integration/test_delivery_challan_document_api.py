"""Integration tests for GET /api/v1/delivery-challans/{id}/document (Sprint
12 Session 16). Mirrors test_purchase_order_document_api.py's own helper
style - a fresh company/invoice/item/challan chain is provisioned per test
via the real API, then dispatched, so the document endpoint is exercised
against a genuinely dispatched challan with a real challan_number. Helper
functions mirror test_delivery_challan_lifecycle_api.py's own shape.

Assertions on the rendered PDF are deliberately structural (the `%PDF`
signature, non-empty bytes, the challan number/customer name/invoice number/
item description/quantity appearing somewhere in the bytes) rather than any
pixel-level layout check.
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
    "delivery_challan:view",
    "delivery_challan:create",
    "delivery_challan:dispatch",
    "delivery_challan:cancel",
    "invoice:view",
    "invoice:create",
    "invoice:issue",
    "company:view",
    "company:create",
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
_CHALLAN_DATE = "2026-08-16"
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
        "name": f"Document Fish {uuid.uuid4().hex[:8]}",
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
    boat = await _create_boat(client, headers)
    payload: dict[str, Any] = {
        "boat_id": boat["id"],
        "trip_number": f"DOCTRIP-{uuid.uuid4().hex[:8]}",
        "trip_type": "fishing",
        "departure_datetime": _DEPARTURE,
    }
    payload.update(overrides)
    response = await client.post("/api/v1/trips", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    trip: dict[str, Any] = response.json()
    update_response = await client.put(
        f"/api/v1/trips/{trip['id']}",
        json={"status": "returned", "actual_return_datetime": _RETURN},
        headers=headers,
    )
    assert update_response.status_code == 200, update_response.text
    result: dict[str, Any] = update_response.json()
    return result


async def _create_trip_catch(
    client: AsyncClient, headers: dict[str, str], *, fish_id: str | None = None, **overrides: Any
) -> dict[str, Any]:
    trip = await _create_returned_trip(client, headers)
    if fish_id is None:
        fish_id = (await _create_fish(client, headers))["id"]
    payload: dict[str, Any] = {
        "trip_id": trip["id"],
        "fish_id": fish_id,
        "quantity_caught": "100.000",
        "landing_date": _LANDING_DATE,
    }
    payload.update(overrides)
    response = await client.post("/api/v1/trip-catches", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _create_invoice(
    client: AsyncClient, headers: dict[str, str], *, company_id: str | None = None, **overrides: Any
) -> dict[str, Any]:
    if company_id is None:
        company_id = (await _create_company(client, headers))["id"]
    payload: dict[str, Any] = {"company_id": company_id, "invoice_date": _INVOICE_DATE}
    payload.update(overrides)
    response = await client.post("/api/v1/invoices", json=payload, headers=headers)
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
        "quantity": "100.000",
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


async def _issued_invoice_with_items(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    company_id: str | None = None,
    item_count: int = 2,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    invoice = await _create_invoice(client, headers, company_id=company_id)
    items = [
        await _create_invoice_item(client, headers, invoice["id"], description=f"Grade {i}")
        for i in range(item_count)
    ]
    issue_response = await client.post(f"/api/v1/invoices/{invoice['id']}/issue", headers=headers)
    assert issue_response.status_code == 200, issue_response.text
    issued: dict[str, Any] = issue_response.json()
    return issued, items


async def _create_delivery_challan(
    client: AsyncClient, headers: dict[str, str], *, invoice_id: str, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"invoice_id": invoice_id, "challan_date": _CHALLAN_DATE}
    payload.update(overrides)
    response = await client.post("/api/v1/delivery-challans", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _add_delivery_challan_item(
    client: AsyncClient,
    headers: dict[str, str],
    challan_id: str,
    *,
    invoice_item_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"invoice_item_id": invoice_item_id, "quantity": "40.000"}
    payload.update(overrides)
    response = await client.post(
        f"/api/v1/delivery-challans/{challan_id}/items", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def _dispatched_challan_with_items(
    client: AsyncClient, headers: dict[str, str], *, company_id: str | None = None
) -> dict[str, Any]:
    """A dispatched challan with two items against a two-item invoice - the
    realistic scenario this session's own real-data verification asks for."""
    invoice, items = await _issued_invoice_with_items(client, headers, company_id=company_id)
    challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
    for item in items:
        await _add_delivery_challan_item(client, headers, challan["id"], invoice_item_id=item["id"])
    dispatch_response = await client.post(
        f"/api/v1/delivery-challans/{challan['id']}/dispatch", headers=headers
    )
    assert dispatch_response.status_code == 200, dispatch_response.text
    result: dict[str, Any] = dispatch_response.json()
    return result


async def _invoice_id_for(
    client: AsyncClient, headers: dict[str, str], challan: dict[str, Any]
) -> str:
    challan_response = await client.get(
        f"/api/v1/delivery-challans/{challan['id']}", headers=headers
    )
    invoice_id: str = challan_response.json()["invoice_id"]
    return invoice_id


async def _get_document(client: AsyncClient, headers: dict[str, str], challan_id: str) -> Any:
    return await client.get(f"/api/v1/delivery-challans/{challan_id}/document", headers=headers)


class TestDocumentEndpointAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/delivery-challans/{uuid.uuid4()}/document")
        assert response.status_code == 401

    async def test_requires_delivery_challan_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        admin_headers = await _admin_headers(client)
        challan = await _dispatched_challan_with_items(client, admin_headers)

        no_view_headers = await _make_user_headers(db_session, tenant_id, [])
        response = await _get_document(client, no_view_headers, challan["id"])
        assert response.status_code == 403

    async def test_delivery_challan_view_permission_alone_is_sufficient(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """delivery_challan:view alone (no create/dispatch) must be enough
        to download the document - no new permission
        (delivery_challan:export/download/document) is introduced by this
        endpoint."""
        tenant_id = await _admin_tenant_id(client)
        admin_headers = await _admin_headers(client)
        challan = await _dispatched_challan_with_items(client, admin_headers)

        view_only_headers = await _make_user_headers(
            db_session, tenant_id, ["delivery_challan:view"]
        )
        response = await _get_document(client, view_only_headers, challan["id"])
        assert response.status_code == 200


class TestSuccessfulDownload:
    async def test_downloads_a_pdf_for_a_dispatched_challan(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        challan = await _dispatched_challan_with_items(client, headers)

        response = await _get_document(client, headers, challan["id"])

        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")
        assert len(response.content) > 0

    async def test_content_type_is_application_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        challan = await _dispatched_challan_with_items(client, headers)

        response = await _get_document(client, headers, challan["id"])

        assert response.headers["content-type"] == "application/pdf"

    async def test_content_disposition_is_attachment_with_the_expected_filename(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        challan = await _dispatched_challan_with_items(client, headers)

        response = await _get_document(client, headers, challan["id"])

        expected_filename = build_document_filename(
            DocumentType.DELIVERY_CHALLAN, challan["challan_number"], extension="pdf"
        )
        content_disposition = response.headers["content-disposition"]
        assert content_disposition.startswith("attachment;")
        assert f'filename="{expected_filename}"' in content_disposition

    async def test_challan_number_appears_in_the_rendered_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        challan = await _dispatched_challan_with_items(client, headers)

        response = await _get_document(client, headers, challan["id"])

        assert challan["challan_number"] is not None
        assert challan["challan_number"].encode() in response.content

    async def test_customer_name_appears_in_the_rendered_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers, name="Konkan Seafoods Buyer Co")
        challan = await _dispatched_challan_with_items(client, headers, company_id=company["id"])

        response = await _get_document(client, headers, challan["id"])

        assert b"Konkan Seafoods Buyer Co" in response.content

    async def test_invoice_number_appears_in_the_rendered_pdf(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        challan = await _dispatched_challan_with_items(client, headers)

        invoice_response = await client.get(
            f"/api/v1/invoices/{await _invoice_id_for(client, headers, challan)}", headers=headers
        )
        invoice_number = invoice_response.json()["invoice_number"]

        response = await _get_document(client, headers, challan["id"])
        assert invoice_number.encode() in response.content

    async def test_item_description_and_quantity_appear_in_the_rendered_pdf(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        invoice, items = await _issued_invoice_with_items(client, headers, item_count=1)
        fish_response = await client.get(f"/api/v1/fish/{items[0]['fish_id']}", headers=headers)
        fish_name = fish_response.json()["name"]
        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        await _add_delivery_challan_item(
            client, headers, challan["id"], invoice_item_id=items[0]["id"], quantity="35.500"
        )
        dispatch_response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/dispatch", headers=headers
        )
        assert dispatch_response.status_code == 200, dispatch_response.text
        dispatched = dispatch_response.json()

        response = await _get_document(client, headers, dispatched["id"])

        assert fish_name.encode() in response.content
        assert b"35.500" in response.content

    async def test_remarks_appear_in_the_rendered_pdf_when_present(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        invoice, items = await _issued_invoice_with_items(client, headers, item_count=1)
        challan = await _create_delivery_challan(
            client, headers, invoice_id=invoice["id"], remarks="Fragile - handle with care"
        )
        await _add_delivery_challan_item(
            client, headers, challan["id"], invoice_item_id=items[0]["id"]
        )
        dispatch_response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/dispatch", headers=headers
        )
        assert dispatch_response.status_code == 200, dispatch_response.text

        response = await _get_document(client, headers, challan["id"])
        assert b"Fragile - handle with care" in response.content

    async def test_rendered_pdf_carries_no_payment_or_outstanding_information(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        challan = await _dispatched_challan_with_items(client, headers)

        response = await _get_document(client, headers, challan["id"])

        assert b"Paid" not in response.content
        assert b"Balance" not in response.content
        assert b"Outstanding" not in response.content

    async def test_multi_item_challan_downloads_successfully(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        invoice, items = await _issued_invoice_with_items(client, headers, item_count=8)
        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        for item in items:
            await _add_delivery_challan_item(
                client, headers, challan["id"], invoice_item_id=item["id"], quantity="5.000"
            )
        dispatch_response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/dispatch", headers=headers
        )
        assert dispatch_response.status_code == 200, dispatch_response.text

        response = await _get_document(client, headers, challan["id"])
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")


class TestNotFoundAndBusinessRuleFailures:
    async def test_returns_404_for_an_unknown_delivery_challan(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await _get_document(client, headers, str(uuid.uuid4()))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_NOT_FOUND"

    async def test_returns_422_for_a_draft_delivery_challan(self, client: AsyncClient) -> None:
        """A draft delivery challan has no challan_number yet - there is
        nothing to print, and the endpoint must fail cleanly rather than
        generate a document with a missing/fake number."""
        headers = await _admin_headers(client)
        invoice, items = await _issued_invoice_with_items(client, headers, item_count=1)
        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        await _add_delivery_challan_item(
            client, headers, challan["id"], invoice_item_id=items[0]["id"]
        )

        response = await _get_document(client, headers, challan["id"])

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_DOCUMENT_NOT_AVAILABLE"

    async def test_returns_422_for_a_delivery_challan_cancelled_directly_from_draft(
        self, client: AsyncClient
    ) -> None:
        """A delivery challan cancelled straight from draft never received a
        challan_number either - this is one of the two CANCELLED branches
        this module can reach (DRAFT|DISPATCHED -> CANCELLED), and this
        session's own documented decision is to gate purely on the number,
        not the status - mirroring PurchaseOrderDocumentNotAvailableError's
        own precedent exactly."""
        headers = await _admin_headers(client)
        invoice, _ = await _issued_invoice_with_items(client, headers, item_count=1)
        challan = await _create_delivery_challan(client, headers, invoice_id=invoice["id"])
        cancel_response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/cancel", headers=headers
        )
        assert cancel_response.status_code == 200, cancel_response.text

        response = await _get_document(client, headers, challan["id"])

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_DOCUMENT_NOT_AVAILABLE"

    async def test_returns_200_for_a_delivery_challan_cancelled_after_dispatch(
        self, client: AsyncClient
    ) -> None:
        """A delivery challan dispatched and then cancelled keeps its
        challan_number - the same "cancelled finalized records keep their
        document" precedent PurchaseOrder established means it should still
        be printable. This is this session's documented decision for the
        CANCELLED lifecycle branch (see this session's own report)."""
        headers = await _admin_headers(client)
        challan = await _dispatched_challan_with_items(client, headers)
        cancel_response = await client.post(
            f"/api/v1/delivery-challans/{challan['id']}/cancel", headers=headers
        )
        assert cancel_response.status_code == 200, cancel_response.text

        response = await _get_document(client, headers, challan["id"])
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")


class TestTenantIsolation:
    async def test_returns_404_for_a_delivery_challan_belonging_to_another_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Other Delivery Challan Document Tenant",
            slug=f"other-delivery-challan-document-tenant-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(
            db_session, other_tenant.id, _ALL_DOCUMENT_PERMISSIONS
        )
        other_challan = await _dispatched_challan_with_items(client, other_headers)

        admin_headers = await _admin_headers(client)
        response = await _get_document(client, admin_headers, other_challan["id"])
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DELIVERY_CHALLAN_NOT_FOUND"


class TestFinancialFiguresUnaffected:
    """This session's own explicit requirement: generating a delivery
    challan's document must never change the linked invoice's totals or the
    billed company's outstanding amount - it is a read-only render."""

    async def test_invoice_and_company_figures_unchanged_after_document_generation(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers)
        challan = await _dispatched_challan_with_items(client, headers, company_id=company["id"])
        invoice_id = await _invoice_id_for(client, headers, challan)

        before_invoice = (
            await client.get(f"/api/v1/invoices/{invoice_id}", headers=headers)
        ).json()
        before_company = (
            await client.get(f"/api/v1/companies/{company['id']}", headers=headers)
        ).json()

        await _get_document(client, headers, challan["id"])

        after_invoice = (await client.get(f"/api/v1/invoices/{invoice_id}", headers=headers)).json()
        after_company = (
            await client.get(f"/api/v1/companies/{company['id']}", headers=headers)
        ).json()

        assert after_invoice["total_amount"] == before_invoice["total_amount"]
        assert after_invoice["paid_amount"] == before_invoice["paid_amount"]
        assert after_invoice["balance_amount"] == before_invoice["balance_amount"]
        assert after_company["outstanding_amount"] == before_company["outstanding_amount"]


class TestDocumentCenterIntegration:
    """Sprint 12 Session 16: downloading a delivery challan's PDF must also
    create a DocumentRecord, visible and re-downloadable through the
    Document Center - not just a one-off PDF response."""

    async def test_downloading_the_document_creates_a_document_center_record(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        company = await _create_company(client, headers, name="Document Center Buyer Co")
        challan = await _dispatched_challan_with_items(client, headers, company_id=company["id"])

        pdf_response = await _get_document(client, headers, challan["id"])
        assert pdf_response.status_code == 200

        list_response = await client.get(
            "/api/v1/documents", params={"q": challan["challan_number"]}, headers=headers
        )
        assert list_response.status_code == 200
        items = list_response.json()["data"]
        assert len(items) == 1
        record = items[0]
        assert record["document_type"] == "delivery_challan"
        assert record["document_number"] == challan["challan_number"]
        assert record["party_type"] == "customer"
        assert record["party_id"] == company["id"]
        assert record["party_name"] == "Document Center Buyer Co"
        assert record["file_extension"] == "pdf"
        assert record["content_type"] == "application/pdf"
        assert record["file_size"] == len(pdf_response.content)
        assert record["generated_by_name"]
        assert record["source_type"] == "delivery_challan"
        assert record["source_id"] == challan["id"]

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
        challan = await _dispatched_challan_with_items(client, headers)

        await _get_document(client, headers, challan["id"])
        await _get_document(client, headers, challan["id"])
        await _get_document(client, headers, challan["id"])

        list_response = await client.get(
            "/api/v1/documents",
            params={"q": challan["challan_number"], "page_size": 50},
            headers=headers,
        )
        assert list_response.status_code == 200
        assert len(list_response.json()["data"]) == 3
