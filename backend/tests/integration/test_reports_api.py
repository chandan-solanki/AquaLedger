import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.boats.models import Boat
from app.modules.companies.models import Company
from app.modules.fish.models import Fish
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.models import Invoice, InvoiceItem
from app.modules.payments.constants import PaymentMethod, PaymentStatus
from app.modules.payments.models import Payment
from app.modules.purchase.constants import PurchaseStatus
from app.modules.purchase.models import PurchaseBill
from app.modules.supplier_payments.constants import PaymentMethod as SupplierPaymentMethod
from app.modules.supplier_payments.constants import SupplierPaymentStatus
from app.modules.supplier_payments.models import SupplierPayment
from app.modules.suppliers.models import Supplier
from app.modules.trip_catches.models import TripCatch
from app.modules.trip_expenses.models import TripExpense
from app.modules.trips.constants import TripStatus, TripType
from app.modules.trips.models import Trip

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
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    company_id: uuid.UUID,
    **overrides: Any,
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


async def _make_payment(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    company_id: uuid.UUID,
    **overrides: Any,
) -> Payment:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "company_id": company_id,
        "payment_number": f"PAY-{uuid.uuid4().hex[:8]}",
        "payment_date": date(2026, 7, 1),
        "payment_method": PaymentMethod.CASH,
        "amount": Decimal("1000.00"),
        "allocated_amount": Decimal("0"),
        "unallocated_amount": Decimal("1000.00"),
        "status": PaymentStatus.POSTED,
    }
    defaults.update(overrides)
    payment = Payment(**defaults)
    db_session.add(payment)
    await db_session.commit()
    return payment


async def _make_supplier(
    db_session: AsyncSession, tenant_id: uuid.UUID, **overrides: Any
) -> Supplier:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "code": f"SUP-{uuid.uuid4().hex[:8]}",
        "name": f"Supplier {uuid.uuid4().hex[:8]}",
    }
    defaults.update(overrides)
    supplier = Supplier(**defaults)
    db_session.add(supplier)
    await db_session.commit()
    return supplier


async def _make_purchase_bill(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID,
    **overrides: Any,
) -> PurchaseBill:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "supplier_id": supplier_id,
        "bill_number": f"PB-{uuid.uuid4().hex[:8]}",
        "bill_date": date(2026, 7, 1),
        "status": PurchaseStatus.POSTED,
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
    bill = PurchaseBill(**defaults)
    db_session.add(bill)
    await db_session.commit()
    return bill


async def _make_supplier_payment(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID,
    **overrides: Any,
) -> SupplierPayment:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "supplier_id": supplier_id,
        "payment_number": f"SPAY-{uuid.uuid4().hex[:8]}",
        "payment_date": date(2026, 7, 1),
        "payment_method": SupplierPaymentMethod.CASH,
        "amount": Decimal("1000.00"),
        "allocated_amount": Decimal("0"),
        "unallocated_amount": Decimal("1000.00"),
        "status": SupplierPaymentStatus.POSTED,
    }
    defaults.update(overrides)
    payment = SupplierPayment(**defaults)
    db_session.add(payment)
    await db_session.commit()
    return payment


class TestCustomerLedgerAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/reports/customer-ledger?customer_id={uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_reports_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id)
        headers = await _make_user_headers(db_session, tenant_id, ["invoice:view"])

        response = await client.get(
            f"/api/v1/reports/customer-ledger?customer_id={company.id}", headers=headers
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_reports_view_permission_is_sufficient(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id)
        headers = await _make_user_headers(db_session, tenant_id, ["reports:view"])

        response = await client.get(
            f"/api/v1/reports/customer-ledger?customer_id={company.id}", headers=headers
        )
        assert response.status_code == 200, response.text


class TestCustomerLedgerValidation:
    async def test_unknown_customer_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/customer-ledger?customer_id={uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "REPORT_CUSTOMER_NOT_FOUND"

    async def test_customer_belonging_to_another_tenant_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Other Reports API Tenant", slug=f"other-reports-api-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_company = await _make_company(db_session, other_tenant.id)

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/customer-ledger?customer_id={other_company.id}", headers=headers
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "REPORT_CUSTOMER_NOT_FOUND"

    async def test_invalid_date_range_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id)
        headers = await _admin_headers(client)

        response = await client.get(
            f"/api/v1/reports/customer-ledger?customer_id={company.id}"
            "&from_date=2026-07-31&to_date=2026-07-01",
            headers=headers,
        )
        assert response.status_code == 422

    async def test_missing_customer_id_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/reports/customer-ledger", headers=headers)
        assert response.status_code == 422

    async def test_invalid_transaction_type_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id)
        headers = await _admin_headers(client)

        response = await client.get(
            f"/api/v1/reports/customer-ledger?customer_id={company.id}&transaction_type=refund",
            headers=headers,
        )
        assert response.status_code == 422


class TestCustomerLedgerHappyPath:
    async def test_full_response_shape_and_values(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id, name="Ledger Test Co", code="LTC-01")
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            invoice_number="INV-A",
            invoice_date=date(2026, 7, 1),
            total_amount=Decimal("1000.00"),
            balance_amount=Decimal("1000.00"),
        )
        await _make_payment(
            db_session,
            tenant_id,
            company.id,
            payment_number="PAY-B",
            payment_date=date(2026, 7, 5),
            amount=Decimal("400.00"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            invoice_number="INV-C",
            invoice_date=date(2026, 7, 10),
            total_amount=Decimal("500.00"),
            balance_amount=Decimal("500.00"),
        )
        # Must never appear or affect any total.
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            invoice_date=date(2026, 7, 1),
            status=InvoiceStatus.DRAFT,
        )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/customer-ledger?customer_id={company.id}", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert body["customer"] == {
            "id": str(company.id),
            "name": "Ledger Test Co",
            "code": "LTC-01",
        }
        assert body["summary"] == {
            "opening_balance": "0.00",
            "total_debit": "1500.00",
            "total_credit": "400.00",
            "closing_balance": "1100.00",
            "invoice_count": 2,
            "payment_count": 1,
        }
        assert [e["reference_number"] for e in body["entries"]] == ["INV-A", "PAY-B", "INV-C"]
        assert [e["running_balance"] for e in body["entries"]] == [
            "1000.00",
            "600.00",
            "1100.00",
        ]
        assert body["pagination"]["total_records"] == 3
        assert body["pagination"]["current_page"] == 1

    async def test_from_date_sets_opening_balance_and_narrows_entries(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id)
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            invoice_date=date(2026, 7, 1),
            total_amount=Decimal("1000.00"),
        )
        await _make_payment(
            db_session,
            tenant_id,
            company.id,
            payment_date=date(2026, 7, 5),
            amount=Decimal("400.00"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            invoice_number="INV-C",
            invoice_date=date(2026, 7, 10),
            total_amount=Decimal("500.00"),
        )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/customer-ledger?customer_id={company.id}&from_date=2026-07-10",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert body["summary"]["opening_balance"] == "600.00"
        assert body["summary"]["closing_balance"] == "1100.00"
        assert len(body["entries"]) == 1
        assert body["entries"][0]["reference_number"] == "INV-C"
        assert body["entries"][0]["running_balance"] == "1100.00"

    async def test_transaction_type_filter_narrows_entries_only(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id)
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            invoice_date=date(2026, 7, 1),
            total_amount=Decimal("1000.00"),
        )
        await _make_payment(
            db_session,
            tenant_id,
            company.id,
            payment_date=date(2026, 7, 5),
            amount=Decimal("400.00"),
        )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/customer-ledger?customer_id={company.id}&transaction_type=invoice",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert len(body["entries"]) == 1
        assert body["entries"][0]["transaction_type"] == "invoice"
        # The summary must NOT be narrowed by the type filter - it always
        # reflects the true full account balance (confirmed design decision).
        assert body["summary"]["total_credit"] == "400.00"
        assert body["summary"]["payment_count"] == 1
        assert body["summary"]["closing_balance"] == "600.00"

    async def test_pagination_params_respected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id)
        for i in range(3):
            await _make_invoice(
                db_session, tenant_id, company.id, invoice_date=date(2026, 7, 1 + i)
            )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/customer-ledger?customer_id={company.id}&page=2&page_size=2",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert len(body["entries"]) == 1
        assert body["pagination"]["current_page"] == 2
        assert body["pagination"]["page_size"] == 2
        assert body["pagination"]["total_records"] == 3
        assert body["pagination"]["total_pages"] == 2
        assert body["pagination"]["has_previous"] is True
        assert body["pagination"]["has_next"] is False

    async def test_inactive_customer_is_still_viewable(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id, status="inactive")
        await _make_invoice(db_session, tenant_id, company.id, invoice_date=date(2026, 7, 1))

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/customer-ledger?customer_id={company.id}", headers=headers
        )
        assert response.status_code == 200, response.text


class TestSupplierLedgerAuth:
    """Mirrors TestCustomerLedgerAuth exactly, on the buy side."""

    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/reports/supplier-ledger?supplier_id={uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_reports_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        supplier = await _make_supplier(db_session, tenant_id)
        headers = await _make_user_headers(db_session, tenant_id, ["purchase:view"])

        response = await client.get(
            f"/api/v1/reports/supplier-ledger?supplier_id={supplier.id}", headers=headers
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_reports_view_permission_is_sufficient(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        supplier = await _make_supplier(db_session, tenant_id)
        headers = await _make_user_headers(db_session, tenant_id, ["reports:view"])

        response = await client.get(
            f"/api/v1/reports/supplier-ledger?supplier_id={supplier.id}", headers=headers
        )
        assert response.status_code == 200, response.text


class TestSupplierLedgerValidation:
    """Mirrors TestCustomerLedgerValidation exactly, on the buy side."""

    async def test_unknown_supplier_is_404(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/supplier-ledger?supplier_id={uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "REPORT_SUPPLIER_NOT_FOUND"

    async def test_supplier_belonging_to_another_tenant_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        other_tenant = Tenant(
            name="Other Supplier Reports API Tenant",
            slug=f"other-supplier-reports-api-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_supplier = await _make_supplier(db_session, other_tenant.id)

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/supplier-ledger?supplier_id={other_supplier.id}", headers=headers
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "REPORT_SUPPLIER_NOT_FOUND"

    async def test_invalid_date_range_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        supplier = await _make_supplier(db_session, tenant_id)
        headers = await _admin_headers(client)

        response = await client.get(
            f"/api/v1/reports/supplier-ledger?supplier_id={supplier.id}"
            "&from_date=2026-07-31&to_date=2026-07-01",
            headers=headers,
        )
        assert response.status_code == 422

    async def test_missing_supplier_id_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/reports/supplier-ledger", headers=headers)
        assert response.status_code == 422

    async def test_invalid_transaction_type_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        supplier = await _make_supplier(db_session, tenant_id)
        headers = await _admin_headers(client)

        response = await client.get(
            f"/api/v1/reports/supplier-ledger?supplier_id={supplier.id}&transaction_type=refund",
            headers=headers,
        )
        assert response.status_code == 422


class TestSupplierLedgerHappyPath:
    """Mirrors TestCustomerLedgerHappyPath exactly, on the buy side."""

    async def test_full_response_shape_and_values(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        supplier = await _make_supplier(
            db_session, tenant_id, name="Ledger Test Supplier", code="LTS-01"
        )
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            bill_number="PB-A",
            bill_date=date(2026, 7, 1),
            total_amount=Decimal("1000.00"),
            balance_amount=Decimal("1000.00"),
        )
        await _make_supplier_payment(
            db_session,
            tenant_id,
            supplier.id,
            payment_number="SPAY-B",
            payment_date=date(2026, 7, 5),
            amount=Decimal("400.00"),
        )
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            bill_number="PB-C",
            bill_date=date(2026, 7, 10),
            total_amount=Decimal("500.00"),
            balance_amount=Decimal("500.00"),
        )
        # Must never appear or affect any total.
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            bill_date=date(2026, 7, 1),
            status=PurchaseStatus.DRAFT,
        )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/supplier-ledger?supplier_id={supplier.id}", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert body["supplier"] == {
            "id": str(supplier.id),
            "name": "Ledger Test Supplier",
            "code": "LTS-01",
        }
        assert body["summary"] == {
            "opening_balance": "0.00",
            "total_debit": "1500.00",
            "total_credit": "400.00",
            "closing_balance": "1100.00",
            "purchase_bill_count": 2,
            "supplier_payment_count": 1,
        }
        assert [e["reference_number"] for e in body["entries"]] == ["PB-A", "SPAY-B", "PB-C"]
        assert [e["running_balance"] for e in body["entries"]] == [
            "1000.00",
            "600.00",
            "1100.00",
        ]
        assert body["pagination"]["total_records"] == 3
        assert body["pagination"]["current_page"] == 1

    async def test_from_date_sets_opening_balance_and_narrows_entries(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        supplier = await _make_supplier(db_session, tenant_id)
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            bill_date=date(2026, 7, 1),
            total_amount=Decimal("1000.00"),
        )
        await _make_supplier_payment(
            db_session,
            tenant_id,
            supplier.id,
            payment_date=date(2026, 7, 5),
            amount=Decimal("400.00"),
        )
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            bill_number="PB-C",
            bill_date=date(2026, 7, 10),
            total_amount=Decimal("500.00"),
        )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/supplier-ledger?supplier_id={supplier.id}&from_date=2026-07-10",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert body["summary"]["opening_balance"] == "600.00"
        assert body["summary"]["closing_balance"] == "1100.00"
        assert len(body["entries"]) == 1
        assert body["entries"][0]["reference_number"] == "PB-C"
        assert body["entries"][0]["running_balance"] == "1100.00"

    async def test_transaction_type_filter_narrows_entries_only(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        supplier = await _make_supplier(db_session, tenant_id)
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            bill_date=date(2026, 7, 1),
            total_amount=Decimal("1000.00"),
        )
        await _make_supplier_payment(
            db_session,
            tenant_id,
            supplier.id,
            payment_date=date(2026, 7, 5),
            amount=Decimal("400.00"),
        )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/supplier-ledger?supplier_id={supplier.id}"
            "&transaction_type=purchase_bill",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert len(body["entries"]) == 1
        assert body["entries"][0]["transaction_type"] == "purchase_bill"
        # The summary must NOT be narrowed by the type filter - it always
        # reflects the true full account balance (confirmed design decision).
        assert body["summary"]["total_credit"] == "400.00"
        assert body["summary"]["supplier_payment_count"] == 1
        assert body["summary"]["closing_balance"] == "600.00"

    async def test_pagination_params_respected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        supplier = await _make_supplier(db_session, tenant_id)
        for i in range(3):
            await _make_purchase_bill(
                db_session, tenant_id, supplier.id, bill_date=date(2026, 7, 1 + i)
            )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/supplier-ledger?supplier_id={supplier.id}&page=2&page_size=2",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert len(body["entries"]) == 1
        assert body["pagination"]["current_page"] == 2
        assert body["pagination"]["page_size"] == 2
        assert body["pagination"]["total_records"] == 3
        assert body["pagination"]["total_pages"] == 2
        assert body["pagination"]["has_previous"] is True
        assert body["pagination"]["has_next"] is False

    async def test_inactive_supplier_is_still_viewable(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        supplier = await _make_supplier(db_session, tenant_id, status="inactive")
        await _make_purchase_bill(db_session, tenant_id, supplier.id, bill_date=date(2026, 7, 1))

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/supplier-ledger?supplier_id={supplier.id}", headers=headers
        )
        assert response.status_code == 200, response.text


class TestSalesReportAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/reports/sales")
        assert response.status_code == 401

    async def test_requires_reports_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["invoice:view"])

        response = await client.get("/api/v1/reports/sales", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_reports_view_permission_is_sufficient(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["reports:view"])

        response = await client.get("/api/v1/reports/sales", headers=headers)
        assert response.status_code == 200, response.text


class TestSalesReportValidation:
    async def test_invalid_date_range_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/sales?from_date=2026-07-31&to_date=2026-07-01", headers=headers
        )
        assert response.status_code == 422

    async def test_invalid_status_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/reports/sales?status=refunded", headers=headers)
        assert response.status_code == 422

    async def test_invalid_paid_status_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/reports/sales?paid_status=overdue", headers=headers)
        assert response.status_code == 422

    async def test_unmatched_customer_id_yields_empty_result_not_404(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/sales?customer_id={uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 200, response.text
        assert response.json()["pagination"]["total_records"] == 0


class TestSalesReportHappyPath:
    async def test_full_response_shape_and_values(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id, name="Ledger Test Co", code="LTC-02")
        invoice = await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            invoice_number="INV-A",
            invoice_date=date(2026, 7, 1),
            due_date=date(2026, 7, 15),
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("400.00"),
            balance_amount=Decimal("600.00"),
            status=InvoiceStatus.PARTIALLY_PAID,
        )
        # Must never appear or affect any total.
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            invoice_date=date(2026, 7, 1),
            status=InvoiceStatus.DRAFT,
        )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/sales?customer_id={company.id}", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert body["summary"] == {
            "total_sales": "1000.00",
            "total_paid": "400.00",
            "outstanding": "600.00",
            "invoice_count": 1,
            "average_invoice": "1000.00",
            "largest_invoice": "1000.00",
        }
        assert len(body["rows"]) == 1
        row = body["rows"][0]
        assert row["invoice_id"] == str(invoice.id)
        assert row["invoice_number"] == "INV-A"
        assert row["customer_name"] == "Ledger Test Co"
        assert row["invoice_amount"] == "1000.00"
        assert row["paid_amount"] == "400.00"
        assert row["outstanding_amount"] == "600.00"
        assert row["status"] == "partially_paid"
        assert body["pagination"]["total_records"] == 1

    async def test_sorted_invoice_date_desc_invoice_number_desc(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id)
        await _make_invoice(
            db_session, tenant_id, company.id, invoice_number="INV-A", invoice_date=date(2026, 7, 1)
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            invoice_number="INV-C",
            invoice_date=date(2026, 7, 10),
        )
        await _make_invoice(
            db_session, tenant_id, company.id, invoice_number="INV-B", invoice_date=date(2026, 7, 5)
        )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/sales?customer_id={company.id}", headers=headers
        )
        assert response.status_code == 200, response.text
        assert [r["invoice_number"] for r in response.json()["rows"]] == [
            "INV-C",
            "INV-B",
            "INV-A",
        ]

    async def test_paid_status_filter_narrows_rows_and_page_but_not_used_alone_for_summary(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id)
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            invoice_number="UNPAID",
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("0"),
            balance_amount=Decimal("1000.00"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            invoice_number="PAID",
            total_amount=Decimal("500.00"),
            paid_amount=Decimal("500.00"),
            balance_amount=Decimal("0"),
        )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/sales?customer_id={company.id}&paid_status=paid", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["rows"]) == 1
        assert body["rows"][0]["invoice_number"] == "PAID"
        assert body["summary"]["invoice_count"] == 1
        assert body["summary"]["total_sales"] == "500.00"

    async def test_pagination_params_respected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id)
        for i in range(3):
            await _make_invoice(
                db_session, tenant_id, company.id, invoice_date=date(2026, 7, 1 + i)
            )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/sales?customer_id={company.id}&page=2&page_size=2", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["rows"]) == 1
        assert body["pagination"]["current_page"] == 2
        assert body["pagination"]["total_records"] == 3
        assert body["pagination"]["total_pages"] == 2


class TestPurchaseReportAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/reports/purchases")
        assert response.status_code == 401

    async def test_requires_reports_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["purchase:view"])

        response = await client.get("/api/v1/reports/purchases", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_reports_view_permission_is_sufficient(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["reports:view"])

        response = await client.get("/api/v1/reports/purchases", headers=headers)
        assert response.status_code == 200, response.text


class TestPurchaseReportValidation:
    async def test_invalid_date_range_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/purchases?from_date=2026-07-31&to_date=2026-07-01", headers=headers
        )
        assert response.status_code == 422

    async def test_invalid_status_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/reports/purchases?status=refunded", headers=headers)
        assert response.status_code == 422

    async def test_unmatched_supplier_id_yields_empty_result_not_404(
        self, client: AsyncClient
    ) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/purchases?supplier_id={uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 200, response.text
        assert response.json()["pagination"]["total_records"] == 0


class TestPurchaseReportHappyPath:
    async def test_full_response_shape_and_values(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        supplier = await _make_supplier(
            db_session, tenant_id, name="Ledger Test Supplier", code="LTS-02"
        )
        bill = await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            bill_number="PB-A",
            bill_date=date(2026, 7, 1),
            due_date=date(2026, 7, 31),
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("400.00"),
            balance_amount=Decimal("600.00"),
            status=PurchaseStatus.PARTIALLY_PAID,
        )
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            bill_date=date(2026, 7, 1),
            status=PurchaseStatus.DRAFT,
        )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/purchases?supplier_id={supplier.id}", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert body["summary"] == {
            "total_purchases": "1000.00",
            "total_paid": "400.00",
            "outstanding": "600.00",
            "bill_count": 1,
            "average_bill": "1000.00",
            "largest_bill": "1000.00",
        }
        assert len(body["rows"]) == 1
        row = body["rows"][0]
        assert row["bill_id"] == str(bill.id)
        assert row["bill_number"] == "PB-A"
        assert row["supplier_name"] == "Ledger Test Supplier"
        assert row["bill_amount"] == "1000.00"
        assert row["paid_amount"] == "400.00"
        assert row["outstanding_amount"] == "600.00"
        assert row["status"] == "partially_paid"
        assert body["pagination"]["total_records"] == 1

    async def test_sorted_bill_date_desc_bill_number_desc(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        supplier = await _make_supplier(db_session, tenant_id)
        await _make_purchase_bill(
            db_session, tenant_id, supplier.id, bill_number="PB-A", bill_date=date(2026, 7, 1)
        )
        await _make_purchase_bill(
            db_session, tenant_id, supplier.id, bill_number="PB-C", bill_date=date(2026, 7, 10)
        )
        await _make_purchase_bill(
            db_session, tenant_id, supplier.id, bill_number="PB-B", bill_date=date(2026, 7, 5)
        )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/purchases?supplier_id={supplier.id}", headers=headers
        )
        assert response.status_code == 200, response.text
        assert [r["bill_number"] for r in response.json()["rows"]] == ["PB-C", "PB-B", "PB-A"]

    async def test_pagination_params_respected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        supplier = await _make_supplier(db_session, tenant_id)
        for i in range(3):
            await _make_purchase_bill(
                db_session, tenant_id, supplier.id, bill_date=date(2026, 7, 1 + i)
            )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/purchases?supplier_id={supplier.id}&page=2&page_size=2",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["rows"]) == 1
        assert body["pagination"]["current_page"] == 2
        assert body["pagination"]["total_records"] == 3
        assert body["pagination"]["total_pages"] == 2


class TestOutstandingReportAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/reports/outstanding")
        assert response.status_code == 401

    async def test_requires_reports_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["invoice:view"])

        response = await client.get("/api/v1/reports/outstanding", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_reports_view_permission_is_sufficient(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["reports:view"])

        response = await client.get("/api/v1/reports/outstanding", headers=headers)
        assert response.status_code == 200, response.text


class TestOutstandingReportValidation:
    async def test_defaults_to_customer_tab(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/reports/outstanding", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["entity_type"] == "customer"

    async def test_invalid_entity_type_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/outstanding?entity_type=vendor", headers=headers
        )
        assert response.status_code == 422

    async def test_invalid_date_range_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/outstanding?from_date=2026-07-31&to_date=2026-07-01",
            headers=headers,
        )
        assert response.status_code == 422

    async def test_invalid_risk_level_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/outstanding?risk_level=critical", headers=headers
        )
        assert response.status_code == 422


class TestOutstandingReportHappyPath:
    async def test_full_response_shape_and_values_customer_tab(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(
            db_session, tenant_id, name="Outstanding Test Co", code="OTC-01"
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            invoice_date=date.today() - timedelta(days=20),
            due_date=date.today() - timedelta(days=15),
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("0"),
            balance_amount=Decimal("1000.00"),
        )

        headers = await _admin_headers(client)
        response = await client.get("/api/v1/reports/outstanding", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["entity_type"] == "customer"

        row = next(r for r in body["rows"] if r["entity_id"] == str(company.id))
        assert row["entity_name"] == "Outstanding Test Co"
        assert row["entity_code"] == "OTC-01"
        assert row["outstanding_amount"] == "1000.00"
        assert row["overdue_amount"] == "1000.00"
        assert row["current_amount"] == "0.00"
        assert row["pending_count"] == 1
        assert row["risk_level"] == "medium"

        assert Decimal(body["summary"]["accounts_receivable"]) >= Decimal("1000.00")
        assert "accounts_payable" in body["summary"]
        assert "net_position" in body["summary"]

    async def test_supplier_tab(self, client: AsyncClient, db_session: AsyncSession) -> None:
        tenant_id = await _admin_tenant_id(client)
        supplier = await _make_supplier(
            db_session, tenant_id, name="Outstanding Test Supplier", code="OTS-01"
        )
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            due_date=date.today() + timedelta(days=10),
            total_amount=Decimal("500.00"),
            paid_amount=Decimal("0"),
            balance_amount=Decimal("500.00"),
        )

        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/outstanding?entity_type=supplier", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["entity_type"] == "supplier"

        row = next(r for r in body["rows"] if r["entity_id"] == str(supplier.id))
        assert row["entity_name"] == "Outstanding Test Supplier"
        assert row["outstanding_amount"] == "500.00"
        assert row["overdue_amount"] == "0.00"
        assert row["current_amount"] == "500.00"
        assert row["risk_level"] == "low"

    async def test_summary_unaffected_by_row_filters(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id, name="Filter Unaffected Co")
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            total_amount=Decimal("1000.00"),
            balance_amount=Decimal("1000.00"),
        )

        headers = await _admin_headers(client)
        unfiltered = await client.get("/api/v1/reports/outstanding", headers=headers)
        filtered = await client.get(
            "/api/v1/reports/outstanding?q=zzz-no-such-entity-zzz", headers=headers
        )
        assert unfiltered.status_code == 200, unfiltered.text
        assert filtered.status_code == 200, filtered.text
        assert filtered.json()["rows"] == []
        assert unfiltered.json()["summary"] == filtered.json()["summary"]

    async def test_outstanding_only_and_overdue_only_and_risk_level_filters(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        paid_co = await _make_company(db_session, tenant_id, name="Fully Paid Co")
        await _make_invoice(
            db_session,
            tenant_id,
            paid_co.id,
            total_amount=Decimal("100.00"),
            paid_amount=Decimal("100.00"),
            balance_amount=Decimal("0"),
        )
        overdue_co = await _make_company(db_session, tenant_id, name="Very Overdue Co")
        await _make_invoice(
            db_session,
            tenant_id,
            overdue_co.id,
            due_date=date.today() - timedelta(days=100),
            total_amount=Decimal("200.00"),
            balance_amount=Decimal("200.00"),
        )

        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/outstanding?outstanding_only=true&overdue_only=true"
            "&risk_level=high&q=Very%20Overdue",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["rows"]) == 1
        assert body["rows"][0]["entity_name"] == "Very Overdue Co"

    async def test_pagination_params_respected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        for i in range(3):
            company = await _make_company(
                db_session, tenant_id, name=f"Outstanding Pagination Co {i}"
            )
            await _make_invoice(
                db_session, tenant_id, company.id, balance_amount=Decimal(f"{100 * (i + 1)}.00")
            )

        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/outstanding?page=1&page_size=1", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["rows"]) == 1
        assert body["pagination"]["page_size"] == 1


class TestAgingReportAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/reports/aging")
        assert response.status_code == 401

    async def test_requires_reports_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["purchase:view"])

        response = await client.get("/api/v1/reports/aging", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_reports_view_permission_is_sufficient(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["reports:view"])

        response = await client.get("/api/v1/reports/aging", headers=headers)
        assert response.status_code == 200, response.text


class TestAgingReportValidation:
    async def test_defaults_to_customer_tab(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/reports/aging", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["entity_type"] == "customer"

    async def test_invalid_entity_type_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/reports/aging?entity_type=vendor", headers=headers)
        assert response.status_code == 422

    async def test_invalid_risk_level_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/reports/aging?risk_level=critical", headers=headers)
        assert response.status_code == 422

    async def test_has_no_date_range_query_params(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        # from_date/to_date simply aren't declared fields - passing them is
        # silently ignored (FastAPI drops unknown query params), not a 422.
        response = await client.get("/api/v1/reports/aging?from_date=2026-07-01", headers=headers)
        assert response.status_code == 200, response.text


class TestAgingReportHappyPath:
    async def test_full_response_shape_and_bucket_allocation(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id, name="Aging Test Co", code="ATC-01")
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            invoice_number="AGING-1",
            due_date=date.today() - timedelta(days=45),
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("0"),
            balance_amount=Decimal("1000.00"),
        )

        headers = await _admin_headers(client)
        response = await client.get("/api/v1/reports/aging", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["entity_type"] == "customer"

        row = next(r for r in body["rows"] if r["entity_id"] == str(company.id))
        assert row["entity_name"] == "Aging Test Co"
        assert row["entity_code"] == "ATC-01"
        assert row["current_amount"] == "0.00"
        assert row["days_1_30"] == "0.00"
        assert row["days_31_60"] == "1000.00"
        assert row["days_61_90"] == "0.00"
        assert row["days_90_plus"] == "0.00"
        assert row["total"] == "1000.00"

        assert body["summary"]["grand_total"] != "0.00"

    async def test_summary_reflects_filtered_set(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id, name="Aging Filter Co")
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            total_amount=Decimal("1000.00"),
            balance_amount=Decimal("1000.00"),
        )

        headers = await _admin_headers(client)
        filtered = await client.get(
            "/api/v1/reports/aging?q=zzz-no-such-entity-zzz", headers=headers
        )
        assert filtered.status_code == 200, filtered.text
        body = filtered.json()
        assert body["rows"] == []
        assert body["summary"]["grand_total"] == "0.00"

    async def test_supplier_tab(self, client: AsyncClient, db_session: AsyncSession) -> None:
        tenant_id = await _admin_tenant_id(client)
        supplier = await _make_supplier(db_session, tenant_id, name="Aging Test Supplier")
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            due_date=date.today() + timedelta(days=10),
            total_amount=Decimal("400.00"),
            paid_amount=Decimal("0"),
            balance_amount=Decimal("400.00"),
        )

        headers = await _admin_headers(client)
        response = await client.get("/api/v1/reports/aging?entity_type=supplier", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["entity_type"] == "supplier"

        row = next(r for r in body["rows"] if r["entity_id"] == str(supplier.id))
        assert row["current_amount"] == "400.00"
        assert row["total"] == "400.00"

    async def test_pagination_params_respected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        for i in range(3):
            company = await _make_company(db_session, tenant_id, name=f"Aging Pagination Co {i}")
            await _make_invoice(
                db_session, tenant_id, company.id, balance_amount=Decimal(f"{100 * (i + 1)}.00")
            )

        headers = await _admin_headers(client)
        response = await client.get("/api/v1/reports/aging?page=1&page_size=1", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["rows"]) == 1
        assert body["pagination"]["page_size"] == 1


# -- Trip Profitability / Boat Profitability (TASKS.md Sprint 11 Session 4
# Phase A) --------------------------------------------------------------


async def _make_boat(db_session: AsyncSession, tenant_id: uuid.UUID, **overrides: Any) -> Boat:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "code": f"B-{uuid.uuid4().hex[:8]}",
        "name": f"Boat {uuid.uuid4().hex[:8]}",
        "registration_number": f"REG-{uuid.uuid4().hex[:8]}",
        "is_active": True,
    }
    defaults.update(overrides)
    boat = Boat(**defaults)
    db_session.add(boat)
    await db_session.commit()
    return boat


async def _make_trip(
    db_session: AsyncSession, tenant_id: uuid.UUID, boat_id: uuid.UUID, **overrides: Any
) -> Trip:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "boat_id": boat_id,
        "trip_number": f"TRIP-{uuid.uuid4().hex[:8]}",
        "trip_type": TripType.FISHING,
        "departure_datetime": datetime(2026, 7, 1, 4, 0, tzinfo=UTC),
        "actual_return_datetime": datetime(2026, 7, 5, 18, 0, tzinfo=UTC),
        "status": TripStatus.RETURNED,
    }
    defaults.update(overrides)
    trip = Trip(**defaults)
    db_session.add(trip)
    await db_session.commit()
    return trip


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


async def _make_trip_catch(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    trip_id: uuid.UUID,
    fish_id: uuid.UUID,
    **overrides: Any,
) -> TripCatch:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "trip_id": trip_id,
        "fish_id": fish_id,
        "quantity_caught": Decimal("100.000"),
        "available_quantity": Decimal("0"),
        "sold_quantity": Decimal("100.000"),
        "waste_quantity": Decimal("0"),
        "landing_date": date(2026, 7, 3),
    }
    defaults.update(overrides)
    trip_catch = TripCatch(**defaults)
    db_session.add(trip_catch)
    await db_session.commit()
    return trip_catch


async def _make_trip_expense(
    db_session: AsyncSession, tenant_id: uuid.UUID, trip_id: uuid.UUID, **overrides: Any
) -> TripExpense:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "trip_id": trip_id,
        "expense_type": "diesel",
        "amount": Decimal("500.00"),
        "expense_date": date(2026, 7, 2),
    }
    defaults.update(overrides)
    expense = TripExpense(**defaults)
    db_session.add(expense)
    await db_session.commit()
    return expense


async def _make_trip_invoice_item(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
    fish_id: uuid.UUID,
    trip_catch_id: uuid.UUID,
    **overrides: Any,
) -> InvoiceItem:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "fish_id": fish_id,
        "trip_catch_id": trip_catch_id,
        "line_number": 1,
        "quantity": Decimal("100.000"),
        "unit": "kg",
        "rate": Decimal("100.0000"),
        "discount_percent": Decimal("0"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("10000.00"),
        "tax_rate": Decimal("0"),
        "tax_amount": Decimal("0"),
        "line_total": Decimal("10000.00"),
    }
    defaults.update(overrides)
    item = InvoiceItem(**defaults)
    db_session.add(item)
    await db_session.commit()
    return item


async def _seed_trip_revenue(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    company_id: uuid.UUID,
    trip_id: uuid.UUID,
    fish_id: uuid.UUID,
    *,
    line_total: Decimal,
) -> None:
    catch = await _make_trip_catch(db_session, tenant_id, trip_id, fish_id)
    invoice = await _make_invoice(db_session, tenant_id, company_id)
    await _make_trip_invoice_item(
        db_session, tenant_id, invoice.id, fish_id, catch.id, line_total=line_total
    )


class TestTripProfitabilityAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/reports/trip-profitability")
        assert response.status_code == 401

    async def test_requires_reports_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["trip:view"])

        response = await client.get("/api/v1/reports/trip-profitability", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_reports_view_permission_is_sufficient(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["reports:view"])

        response = await client.get("/api/v1/reports/trip-profitability", headers=headers)
        assert response.status_code == 200, response.text


class TestTripProfitabilityValidation:
    async def test_invalid_date_range_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/trip-profitability?from_date=2026-07-31&to_date=2026-07-01",
            headers=headers,
        )
        assert response.status_code == 422

    async def test_invalid_profitability_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/trip-profitability?profitability=break-even", headers=headers
        )
        assert response.status_code == 422

    async def test_invalid_boat_id_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/trip-profitability?boat_id=not-a-uuid", headers=headers
        )
        assert response.status_code == 422


class TestTripProfitabilityHappyPath:
    async def test_full_response_shape_and_values(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id, name="Trip Profit Test Co")
        fish = await _make_fish(db_session, tenant_id)
        boat = await _make_boat(db_session, tenant_id, name="Trip Profit Test Boat")
        trip = await _make_trip(db_session, tenant_id, boat.id, trip_number="TRIP-API-001")
        await _seed_trip_revenue(
            db_session, tenant_id, company.id, trip.id, fish.id, line_total=Decimal("10000.00")
        )
        await _make_trip_expense(db_session, tenant_id, trip.id, amount=Decimal("4000.00"))

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/trip-profitability?boat_id={boat.id}", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()

        row = next(r for r in body["rows"] if r["trip_id"] == str(trip.id))
        assert row["trip_number"] == "TRIP-API-001"
        assert row["boat_name"] == "Trip Profit Test Boat"
        assert row["status"] == "returned"
        assert row["revenue"] == "10000.00"
        assert row["expenses"] == "4000.00"
        assert row["profit"] == "6000.00"
        assert row["profit_margin_percent"] == "60.00"

        assert Decimal(body["summary"]["total_revenue"]) >= Decimal("10000.00")
        assert body["summary"]["most_profitable_trip_number"] is not None

    async def test_profitability_filter(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        boat = await _make_boat(db_session, tenant_id, name="Loss Filter Boat")
        loss_trip = await _make_trip(db_session, tenant_id, boat.id, trip_number="TRIP-API-LOSS")
        await _make_trip_expense(db_session, tenant_id, loss_trip.id, amount=Decimal("999.00"))

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/trip-profitability?boat_id={boat.id}&profitability=loss",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["rows"]) == 1
        assert body["rows"][0]["trip_number"] == "TRIP-API-LOSS"

    async def test_pagination_params_respected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        boat = await _make_boat(db_session, tenant_id, name="Trip Pagination Boat")
        for i in range(3):
            await _make_trip(
                db_session,
                tenant_id,
                boat.id,
                actual_return_datetime=datetime(2026, 7, 1 + i, 12, 0, tzinfo=UTC),
            )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/trip-profitability?boat_id={boat.id}&page=1&page_size=1",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["rows"]) == 1
        assert body["pagination"]["page_size"] == 1
        assert body["pagination"]["total_records"] == 3


class TestBoatProfitabilityAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/reports/boat-profitability")
        assert response.status_code == 401

    async def test_requires_reports_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["boat:view"])

        response = await client.get("/api/v1/reports/boat-profitability", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_reports_view_permission_is_sufficient(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["reports:view"])

        response = await client.get("/api/v1/reports/boat-profitability", headers=headers)
        assert response.status_code == 200, response.text


class TestBoatProfitabilityValidation:
    async def test_invalid_date_range_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/boat-profitability?from_date=2026-07-31&to_date=2026-07-01",
            headers=headers,
        )
        assert response.status_code == 422

    async def test_invalid_profitability_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/boat-profitability?profitability=break-even", headers=headers
        )
        assert response.status_code == 422

    async def test_min_trips_below_one_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/boat-profitability?min_trips=0", headers=headers
        )
        assert response.status_code == 422


class TestBoatProfitabilityHappyPath:
    async def test_full_response_shape_and_values(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id, name="Boat Profit Test Co")
        fish = await _make_fish(db_session, tenant_id)
        boat = await _make_boat(
            db_session, tenant_id, name="Boat Profit Test Boat", registration_number="REG-API-01"
        )
        trip = await _make_trip(db_session, tenant_id, boat.id)
        await _seed_trip_revenue(
            db_session, tenant_id, company.id, trip.id, fish.id, line_total=Decimal("8000.00")
        )
        await _make_trip_expense(db_session, tenant_id, trip.id, amount=Decimal("2000.00"))

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/boat-profitability?boat_id={boat.id}", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()

        row = next(r for r in body["rows"] if r["boat_id"] == str(boat.id))
        assert row["boat_name"] == "Boat Profit Test Boat"
        assert row["registration_number"] == "REG-API-01"
        assert row["total_trips"] == 1
        assert row["revenue"] == "8000.00"
        assert row["expenses"] == "2000.00"
        assert row["profit"] == "6000.00"
        assert row["profit_margin_percent"] == "75.00"
        assert row["best_trip_profit"] == "6000.00"
        assert row["worst_trip_profit"] == "6000.00"

        assert body["summary"]["total_boats"] == 1
        assert body["summary"]["active_boats"] == 1
        assert body["summary"]["most_profitable_boat_name"] == "Boat Profit Test Boat"

    async def test_min_trips_filter(self, client: AsyncClient, db_session: AsyncSession) -> None:
        tenant_id = await _admin_tenant_id(client)
        boat = await _make_boat(db_session, tenant_id, name="Single Trip Boat")
        await _make_trip(db_session, tenant_id, boat.id)

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/boat-profitability?boat_id={boat.id}&min_trips=2", headers=headers
        )
        assert response.status_code == 200, response.text
        assert response.json()["rows"] == []

    async def test_pagination_params_respected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        for i in range(2):
            boat = await _make_boat(db_session, tenant_id, name=f"Boat Pagination {i}")
            await _make_trip(db_session, tenant_id, boat.id)

        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/boat-profitability?page=1&page_size=1", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["rows"]) == 1
        assert body["pagination"]["page_size"] == 1


# -- Fish Sales Analytics (TASKS.md Sprint 11 Session 4 Phase B) ---------


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


class TestFishSalesAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/reports/fish-sales")
        assert response.status_code == 401

    async def test_requires_reports_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["fish:view"])

        response = await client.get("/api/v1/reports/fish-sales", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_reports_view_permission_is_sufficient(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["reports:view"])

        response = await client.get("/api/v1/reports/fish-sales", headers=headers)
        assert response.status_code == 200, response.text


class TestFishSalesValidation:
    async def test_invalid_date_range_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/fish-sales?from_date=2026-07-31&to_date=2026-07-01",
            headers=headers,
        )
        assert response.status_code == 422

    async def test_negative_min_quantity_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/reports/fish-sales?min_quantity=-1", headers=headers)
        assert response.status_code == 422

    async def test_invalid_fish_id_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/fish-sales?fish_id=not-a-uuid", headers=headers
        )
        assert response.status_code == 422


class TestFishSalesHappyPath:
    async def test_full_response_shape_and_values(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id, name="Fish Sales Test Co")
        fish = await _make_fish(db_session, tenant_id, name="Fish Sales API Pomfret")
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
            f"/api/v1/reports/fish-sales?fish_id={fish.id}", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()

        row = next(r for r in body["rows"] if r["fish_id"] == str(fish.id))
        assert row["fish_name"] == "Fish Sales API Pomfret"
        assert row["quantity_sold"] == "100.000"
        assert row["revenue"] == "10000.00"
        assert row["average_selling_price"] == "100.0000"
        assert row["invoice_count"] == 1
        assert row["customer_count"] == 1

        assert Decimal(body["summary"]["total_revenue"]) >= Decimal("10000.00")
        assert body["summary"]["total_fish_types_sold"] >= 1

    async def test_min_quantity_and_min_revenue_filters(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id, name="Fish Sales Filter Co")
        fish = await _make_fish(db_session, tenant_id, name="Fish Sales Filter Fish")
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        await _make_plain_invoice_item(
            db_session,
            tenant_id,
            invoice.id,
            fish.id,
            quantity=Decimal("5.000"),
            line_total=Decimal("50.00"),
        )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/fish-sales?fish_id={fish.id}&min_quantity=1000",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["rows"] == []

    async def test_search_filter(self, client: AsyncClient, db_session: AsyncSession) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id, name="Fish Sales Search Co")
        fish = await _make_fish(db_session, tenant_id, name="Unique Search Fish Name")
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        await _make_plain_invoice_item(db_session, tenant_id, invoice.id, fish.id)

        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/fish-sales?q=Unique%20Search%20Fish", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["rows"]) == 1
        assert body["rows"][0]["fish_id"] == str(fish.id)

    async def test_pagination_params_respected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id, name="Fish Sales Pagination Co")
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        for i in range(3):
            fish = await _make_fish(db_session, tenant_id, name=f"Fish Sales Pagination Fish {i}")
            await _make_plain_invoice_item(
                db_session,
                tenant_id,
                invoice.id,
                fish.id,
                line_total=Decimal(f"{100 * (i + 1)}.00"),
            )

        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/fish-sales?page=1&page_size=1", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["rows"]) == 1
        assert body["pagination"]["page_size"] == 1


class TestFishSalesHistoryAuth:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/reports/fish-sales-history?fish_id={uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_reports_view_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["fish:view"])

        response = await client.get(
            f"/api/v1/reports/fish-sales-history?fish_id={uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_reports_view_permission_is_sufficient(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, ["reports:view"])

        response = await client.get(
            f"/api/v1/reports/fish-sales-history?fish_id={uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 200, response.text


class TestFishSalesHistoryValidation:
    async def test_missing_fish_id_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get("/api/v1/reports/fish-sales-history", headers=headers)
        assert response.status_code == 422

    async def test_invalid_fish_id_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.get(
            "/api/v1/reports/fish-sales-history?fish_id=not-a-uuid", headers=headers
        )
        assert response.status_code == 422


class TestFishSalesHistoryHappyPath:
    async def test_full_response_shape_and_values(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(db_session, tenant_id, name="Fish Sales History Test Co")
        fish = await _make_fish(db_session, tenant_id, name="Fish Sales History Fish")
        invoice = await _make_invoice(
            db_session, tenant_id, company.id, invoice_date=date(2026, 7, 15)
        )
        await _make_plain_invoice_item(
            db_session,
            tenant_id,
            invoice.id,
            fish.id,
            quantity=Decimal("20.000"),
            rate=Decimal("250.0000"),
            line_total=Decimal("5000.00"),
        )

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/fish-sales-history?fish_id={fish.id}", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["rows"]) == 1
        row = body["rows"][0]
        assert row["customer_name"] == "Fish Sales History Test Co"
        assert row["quantity"] == "20.000"
        assert row["unit_price"] == "250.0000"
        assert row["revenue"] == "5000.00"
        assert row["boat_name"] is None
        assert row["trip_number"] is None

    async def test_pagination_params_respected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        company = await _make_company(
            db_session, tenant_id, name="Fish Sales History Pagination Co"
        )
        fish = await _make_fish(db_session, tenant_id, name="Fish Sales History Pagination Fish")
        for i in range(3):
            invoice = await _make_invoice(
                db_session, tenant_id, company.id, invoice_date=date(2026, 7, 1 + i)
            )
            await _make_plain_invoice_item(db_session, tenant_id, invoice.id, fish.id)

        headers = await _admin_headers(client)
        response = await client.get(
            f"/api/v1/reports/fish-sales-history?fish_id={fish.id}&page=1&page_size=1",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["rows"]) == 1
        assert body["pagination"]["total_records"] == 3
