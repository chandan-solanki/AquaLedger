import csv
import io
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

import openpyxl
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.report_export.registry import registry as export_registry
from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.companies.models import Company
from app.modules.fish.models import Fish
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.models import Invoice, InvoiceItem

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"


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


async def _make_company(
    db_session: AsyncSession, tenant_id: uuid.UUID, **overrides: Any
) -> Company:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "code": f"CO-{uuid.uuid4().hex[:8]}",
        "name": f"Company {uuid.uuid4().hex[:8]}",
        "company_type": "customer",
    }
    defaults.update(overrides)
    company = Company(**defaults)
    db_session.add(company)
    await db_session.commit()
    return company


async def _make_invoice(
    db_session: AsyncSession, tenant_id: uuid.UUID, company_id: uuid.UUID, **overrides: Any
) -> Invoice:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "company_id": company_id,
        "invoice_number": f"INV-{uuid.uuid4().hex[:8]}",
        "invoice_date": date(2026, 7, 1),
        "status": InvoiceStatus.ISSUED,
        "subtotal": Decimal("0"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("0"),
        "tax_amount": Decimal("0"),
        "transport_charge": Decimal("0"),
        "other_charge": Decimal("0"),
        "round_off": Decimal("0"),
        "total_amount": Decimal("1000.00"),
        "paid_amount": Decimal("0"),
        "balance_amount": Decimal("1000.00"),
    }
    defaults.update(overrides)
    invoice = Invoice(**defaults)
    db_session.add(invoice)
    await db_session.commit()
    return invoice


async def _make_fish(db_session: AsyncSession, tenant_id: uuid.UUID, **overrides: Any) -> Fish:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "code": f"FISH-{uuid.uuid4().hex[:8]}",
        "name": f"Fish {uuid.uuid4().hex[:8]}",
    }
    defaults.update(overrides)
    fish = Fish(**defaults)
    db_session.add(fish)
    await db_session.commit()
    return fish


async def _make_plain_invoice_item(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
    fish_id: uuid.UUID,
    **overrides: Any,
) -> InvoiceItem:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "fish_id": fish_id,
        "line_number": 1,
        "quantity": Decimal("50.000"),
        "unit": "kg",
        "rate": Decimal("100.0000"),
        "discount_percent": Decimal("0"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("5000.00"),
        "tax_rate": Decimal("0"),
        "tax_amount": Decimal("0"),
        "line_total": Decimal("5000.00"),
    }
    defaults.update(overrides)
    item = InvoiceItem(**defaults)
    db_session.add(item)
    await db_session.commit()
    return item


class TestExportAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/reports/export?report=fish_sales&format=csv")
        assert response.status_code == 401

    async def test_requires_reports_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["fish:view"])

        response = await client.get(
            "/api/v1/reports/export?report=fish_sales&format=csv", headers=headers
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_reports_view_permission_is_sufficient(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["reports:view"])

        response = await client.get(
            "/api/v1/reports/export?report=fish_sales&format=csv", headers=headers
        )
        assert response.status_code == 200


class TestExportValidation:
    async def test_missing_report_param_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/reports/export?format=csv", headers=headers)
        assert response.status_code == 422

    async def test_missing_format_param_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/reports/export?report=fish_sales", headers=headers)
        assert response.status_code == 422

    async def test_unknown_report_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/export?report=not_a_real_report&format=csv", headers=headers
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "UNSUPPORTED_REPORT"

    async def test_unknown_format_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/export?report=fish_sales&format=not_a_real_format", headers=headers
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "UNSUPPORTED_EXPORT_FORMAT"

    async def test_customer_ledger_export_without_required_customer_id_is_422(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/export?report=customer_ledger&format=csv", headers=headers
        )
        assert response.status_code == 422


class TestExportCSVDownload:
    async def test_fish_sales_csv_contains_seeded_row(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id, name="Export CSV Co")
        fish = await _make_fish(db_session, tenant_id, name="Export CSV Pomfret")
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        await _make_plain_invoice_item(
            db_session,
            tenant_id,
            invoice.id,
            fish.id,
            quantity=Decimal("100.000"),
            line_total=Decimal("10000.00"),
        )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/export?report=fish_sales&format=csv&fish_id={fish.id}",
            headers=headers,
        )

        assert response.status_code == 200
        assert "csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        assert ".csv" in response.headers["content-disposition"]

        reader = csv.reader(io.StringIO(response.text))
        rows = list(reader)
        assert rows[0][0] == "Fish"
        assert any(row[0] == "Export CSV Pomfret" for row in rows[1:])


class TestExportExcelDownload:
    async def test_fish_sales_excel_contains_seeded_row(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id, name="Export Excel Co")
        fish = await _make_fish(db_session, tenant_id, name="Export Excel Surmai")
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        await _make_plain_invoice_item(
            db_session,
            tenant_id,
            invoice.id,
            fish.id,
            quantity=Decimal("20.000"),
            line_total=Decimal("2000.00"),
        )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/export?report=fish_sales&format=excel&fish_id={fish.id}",
            headers=headers,
        )

        assert response.status_code == 200
        assert "spreadsheetml" in response.headers["content-type"]
        assert ".xlsx" in response.headers["content-disposition"]

        workbook = openpyxl.load_workbook(io.BytesIO(response.content))
        worksheet = workbook.active
        values = [cell.value for row in worksheet.iter_rows() for cell in row]
        assert "Export Excel Surmai" in values


class TestExportPDFDownload:
    async def test_fish_sales_pdf_download(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        if not export_registry.is_registered("pdf"):
            pytest.skip("WeasyPrint native libraries are unavailable in this environment")

        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id, name="Export PDF Co")
        fish = await _make_fish(db_session, tenant_id, name="Export PDF Fish")
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        await _make_plain_invoice_item(db_session, tenant_id, invoice.id, fish.id)

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/export?report=fish_sales&format=pdf&fish_id={fish.id}",
            headers=headers,
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert ".pdf" in response.headers["content-disposition"]
        assert response.content.startswith(b"%PDF")


# A minimal real 2x2 PNG (generated via Pillow) - valid enough for
# WeasyPrint to embed as an actual image XObject, not just pass through
# as opaque base64 text.
_PNG_LOGO_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000002000000020802000000fdd4"
    "9a730000001349444154789c6364f8cfc0c0c0c004221818000c1e0103acd8"
    "8ba70000000049454e44ae426082"
)


class TestExportPDFCompanyProfileBranding:
    """Sprint 14: a tenant's uploaded logo appears in an exported PDF's
    header (report.html/report.css), replacing the initials placeholder -
    and CSV/Excel exports remain completely unaffected by it.

    Uses a fresh tenant, never the shared admin dev tenant: uploading and
    deleting a logo writes real bytes to the local filesystem storage
    root, which is not part of the per-test DB transaction rollback
    (`conftest.py`'s `create_savepoint` isolation only covers the
    database). Running these tests against the shared tenant would
    permanently overwrite, and then delete, whatever real logo a
    developer configured through the actual UI.
    """

    async def test_uploaded_logo_is_embedded_in_the_exported_pdf(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        if not export_registry.is_registered("pdf"):
            pytest.skip("WeasyPrint native libraries are unavailable in this environment")

        tenant = Tenant(name="Branding PDF Co", slug=f"branding-pdf-{uuid.uuid4().hex[:8]}")
        db_session.add(tenant)
        await db_session.commit()
        tenant_id = tenant.id
        fish = await _make_fish(db_session, tenant_id, name="Branding PDF Fish")
        company = await _make_company(db_session, tenant_id, name="Branding PDF Co")
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        await _make_plain_invoice_item(db_session, tenant_id, invoice.id, fish.id)

        headers = await _make_user_headers(
            db_session, tenant_id, ["settings:manage", "reports:view"]
        )
        upload = await client.post(
            "/api/v1/company-profile/logo",
            headers=headers,
            files={"file": ("logo.png", _PNG_LOGO_BYTES, "image/png")},
        )
        assert upload.status_code == 200

        response = await client.get(
            f"/api/v1/reports/export?report=fish_sales&format=pdf&fish_id={fish.id}",
            headers=headers,
        )
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF")
        assert b"/Subtype /Image" in response.content or b"/Subtype/Image" in response.content

    async def test_csv_export_is_unaffected_by_a_configured_logo(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = Tenant(name="Branding CSV Co", slug=f"branding-csv-{uuid.uuid4().hex[:8]}")
        db_session.add(tenant)
        await db_session.commit()
        tenant_id = tenant.id
        fish = await _make_fish(db_session, tenant_id, name="Branding CSV Fish")
        company = await _make_company(db_session, tenant_id, name="Branding CSV Co")
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        await _make_plain_invoice_item(db_session, tenant_id, invoice.id, fish.id)

        headers = await _make_user_headers(
            db_session, tenant_id, ["settings:manage", "reports:view"]
        )
        upload = await client.post(
            "/api/v1/company-profile/logo",
            headers=headers,
            files={"file": ("logo.png", _PNG_LOGO_BYTES, "image/png")},
        )
        assert upload.status_code == 200

        response = await client.get(
            f"/api/v1/reports/export?report=fish_sales&format=csv&fish_id={fish.id}",
            headers=headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")


class TestExportCustomerLedgerEntriesField:
    """Customer/Supplier Ledger use `entries`, not `rows` - the one place
    _fetch_all_rows's field-name parameter actually varies (TASKS.md
    Sprint 11 Session 5 Phase B)."""

    async def test_customer_ledger_csv_reflects_seeded_invoice(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id, name="Export Ledger Co")
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            total_amount=Decimal("4200.00"),
            balance_amount=Decimal("4200.00"),
        )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/export?report=customer_ledger&format=csv&customer_id={company.id}",
            headers=headers,
        )

        assert response.status_code == 200
        reader = csv.reader(io.StringIO(response.text))
        rows = list(reader)
        assert rows[0] == [
            "Date",
            "Reference",
            "Transaction Type",
            "Description",
            "Debit",
            "Credit",
            "Running Balance",
        ]
        assert any(row[4] == "4200.00" for row in rows[1:])


class TestExportPaginationAcrossRealPages:
    async def test_export_includes_rows_beyond_a_single_page(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Seeds more fish than one page (page_size=100 internally) would
        hold, proving the export endpoint's own pagination-flattening
        (export_dispatch._fetch_all_rows) actually walks every page - not
        just the first - against a real database, not a fake."""
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id, name="Export Pagination Co")
        marker = uuid.uuid4().hex[:8]
        for index in range(105):
            fish = await _make_fish(db_session, tenant_id, name=f"PageFish-{marker}-{index:03d}")
            invoice = await _make_invoice(db_session, tenant_id, company.id)
            await _make_plain_invoice_item(
                db_session, tenant_id, invoice.id, fish.id, line_total=Decimal("10.00")
            )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/export?report=fish_sales&format=csv&q=PageFish-{marker}",
            headers=headers,
        )

        assert response.status_code == 200
        reader = csv.reader(io.StringIO(response.text))
        rows = list(reader)
        assert len(rows) - 1 == 105
