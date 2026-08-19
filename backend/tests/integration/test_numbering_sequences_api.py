import datetime as dt
import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.invoices.models import InvoiceSequence
from app.modules.purchase_orders.models import PurchaseOrderSequence

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"


def _current_fiscal_year() -> str:
    today = dt.date.today()
    start_year = today.year if today.month >= 4 else today.year - 1
    return f"{start_year}-{(start_year + 1) % 100:02d}"


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _make_tenant_with_headers(
    db_session: AsyncSession, permissions: list[str], name: str = "Numbering Test Co"
) -> tuple[uuid.UUID, dict[str, str]]:
    tenant = Tenant(name=name, slug=f"{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    await db_session.commit()

    user = User(
        tenant_id=tenant.id,
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
    return tenant.id, {"Authorization": f"Bearer {token}"}


class TestListNumberingSequences:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/numbering-sequences")
        assert response.status_code == 401

    async def test_requires_settings_manage_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        _tenant_id, headers = await _make_tenant_with_headers(db_session, [])
        response = await client.get("/api/v1/numbering-sequences", headers=headers)
        assert response.status_code == 403

    async def test_fresh_tenant_has_no_documents_issued_yet(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        _tenant_id, headers = await _make_tenant_with_headers(db_session, ["settings:manage"])
        response = await client.get("/api/v1/numbering-sequences", headers=headers)
        assert response.status_code == 200

        body = response.json()
        assert {item["document_type"] for item in body} == {
            "invoice",
            "purchase_bill",
            "purchase_order",
            "customer_payment",
            "supplier_payment",
            "delivery_challan",
        }
        for item in body:
            assert item["current_number"] == 0
            assert item["next_number"] == 1
            assert item["status"] == "not_started"

        invoice = next(item for item in body if item["document_type"] == "invoice")
        assert invoice["prefix"] == "INV"
        assert invoice["fiscal_year"] == _current_fiscal_year()
        assert invoice["next_number_formatted"] == f"INV/{_current_fiscal_year()}/00001"

    async def test_reflects_the_real_sequence_row_when_documents_exist(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id, headers = await _make_tenant_with_headers(db_session, ["settings:manage"])
        fiscal_year = _current_fiscal_year()
        db_session.add(
            InvoiceSequence(
                tenant_id=tenant_id, prefix="INV", fiscal_year=fiscal_year, last_number=24
            )
        )
        db_session.add(
            PurchaseOrderSequence(
                tenant_id=tenant_id, prefix="PO", fiscal_year=fiscal_year, last_number=4
            )
        )
        await db_session.commit()

        response = await client.get("/api/v1/numbering-sequences", headers=headers)
        assert response.status_code == 200
        body = response.json()

        invoice = next(item for item in body if item["document_type"] == "invoice")
        assert invoice["current_number"] == 24
        assert invoice["next_number"] == 25
        assert invoice["next_number_formatted"] == f"INV/{fiscal_year}/00025"
        assert invoice["status"] == "active"

        purchase_order = next(item for item in body if item["document_type"] == "purchase_order")
        assert purchase_order["current_number"] == 4
        assert purchase_order["next_number"] == 5
        assert purchase_order["status"] == "active"

        # Untouched sequences for this same tenant stay unaffected.
        customer_payment = next(
            item for item in body if item["document_type"] == "customer_payment"
        )
        assert customer_payment["current_number"] == 0
        assert customer_payment["status"] == "not_started"

    async def test_tenant_isolation(self, client: AsyncClient, db_session: AsyncSession) -> None:
        tenant_a, headers_a = await _make_tenant_with_headers(
            db_session, ["settings:manage"], name="Tenant A"
        )
        _tenant_b, headers_b = await _make_tenant_with_headers(
            db_session, ["settings:manage"], name="Tenant B"
        )
        fiscal_year = _current_fiscal_year()
        db_session.add(
            InvoiceSequence(
                tenant_id=tenant_a, prefix="INV", fiscal_year=fiscal_year, last_number=99
            )
        )
        await db_session.commit()

        response_a = await client.get("/api/v1/numbering-sequences", headers=headers_a)
        response_b = await client.get("/api/v1/numbering-sequences", headers=headers_b)

        invoice_a = next(item for item in response_a.json() if item["document_type"] == "invoice")
        invoice_b = next(item for item in response_b.json() if item["document_type"] == "invoice")
        assert invoice_a["current_number"] == 99
        assert invoice_b["current_number"] == 0

    async def test_superuser_can_view_without_explicit_permission(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/numbering-sequences", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 6
