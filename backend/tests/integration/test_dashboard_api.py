import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.companies.models import Company
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.models import Invoice

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
        "outstanding_amount": Decimal("0"),
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
        "invoice_date": date.today(),
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


class TestGetDashboardAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/dashboard")
        assert response.status_code == 401

    async def test_requires_dashboard_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["company:view"])
        response = await client.get("/api/v1/dashboard", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_user_with_dashboard_view_permission_succeeds(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["dashboard:view"])
        response = await client.get("/api/v1/dashboard", headers=headers)
        assert response.status_code == 200

    async def test_superuser_bypasses_permission_check(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/dashboard", headers=headers)
        assert response.status_code == 200


class TestGetDashboardShape:
    async def test_response_has_the_five_documented_sections(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/dashboard", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {
            "kpis",
            "operations",
            "financial",
            "recent_activity",
            "alerts",
            "charts",
            "widgets",
        }
        assert set(body["kpis"].keys()) == {
            "todays_sales",
            "monthly_sales",
            "customer_payments_today",
            "supplier_payments_today",
            "active_trips",
            "boats_at_sea",
            "todays_catch_quantity",
            "draft_invoices",
            "draft_payments",
        }
        assert set(body["operations"].keys()) == {
            "trips_today",
            "trips_active",
            "trips_completed_today",
            "boats_available",
            "boats_at_sea",
            "boats_maintenance",
        }
        assert set(body["financial"].keys()) == {
            "customer_outstanding",
            "supplier_outstanding",
            "invoices_issued_this_month",
            "purchase_bills_this_month",
        }
        assert isinstance(body["recent_activity"], list)
        assert isinstance(body["alerts"], list)

        assert set(body["charts"].keys()) == {
            "monthly_sales",
            "monthly_purchases",
            "fish_sales",
            "trip_status",
        }
        assert len(body["charts"]["monthly_sales"]) == 12
        assert set(body["charts"]["monthly_sales"][0].keys()) == {
            "month",
            "sales_amount",
            "invoice_count",
        }
        assert len(body["charts"]["monthly_purchases"]) == 12
        assert set(body["charts"]["monthly_purchases"][0].keys()) == {
            "month",
            "purchase_amount",
            "purchase_bill_count",
        }
        assert isinstance(body["charts"]["fish_sales"], list)
        assert len(body["charts"]["fish_sales"]) <= 10
        assert len(body["charts"]["trip_status"]) == 4
        assert {point["status"] for point in body["charts"]["trip_status"]} == {
            "Active",
            "Completed",
            "Cancelled",
            "Draft",
        }

        assert set(body["widgets"].keys()) == {
            "top_customers",
            "top_suppliers",
            "top_fish",
            "outstanding_summary",
        }
        assert isinstance(body["widgets"]["top_customers"], list)
        assert len(body["widgets"]["top_customers"]) <= 5
        assert isinstance(body["widgets"]["top_suppliers"], list)
        assert len(body["widgets"]["top_suppliers"]) <= 5
        assert isinstance(body["widgets"]["top_fish"], list)
        assert len(body["widgets"]["top_fish"]) <= 5
        assert set(body["widgets"]["outstanding_summary"].keys()) == {
            "customer_outstanding",
            "customer_overdue",
            "supplier_outstanding",
            "supplier_overdue",
        }


class TestGetDashboardWidgets:
    async def test_top_customers_reflects_issued_invoices(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["dashboard:view"])
        company = await _make_company(
            db_session, tenant_id, name="Konkan Seafoods", outstanding_amount=Decimal("500.00")
        )
        await _make_invoice(db_session, tenant_id, company.id, total_amount=Decimal("2500.00"))

        response = await client.get("/api/v1/dashboard", headers=headers)
        body = response.json()

        top_customers = body["widgets"]["top_customers"]
        assert any(
            row["company_name"] == "Konkan Seafoods"
            and Decimal(row["total_sales"]) >= Decimal("2500.00")
            for row in top_customers
        )


class TestGetDashboardTenantIsolation:
    async def test_todays_sales_only_reflects_the_caller_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        admin_tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, admin_tenant_id, ["dashboard:view"])

        baseline = await client.get("/api/v1/dashboard", headers=headers)
        baseline_sales = Decimal(baseline.json()["kpis"]["todays_sales"])

        other_tenant = Tenant(
            name="Other Dashboard Tenant", slug=f"dash-api-other-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_company = await _make_company(db_session, other_tenant.id)
        await _make_invoice(
            db_session, other_tenant.id, other_company.id, total_amount=Decimal("999999.00")
        )

        after_other_tenant_invoice = await client.get("/api/v1/dashboard", headers=headers)
        after_sales = Decimal(after_other_tenant_invoice.json()["kpis"]["todays_sales"])

        assert after_sales == baseline_sales
