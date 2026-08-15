import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Tenant
from app.modules.boats.models import Boat
from app.modules.companies.models import Company
from app.modules.fish.models import Fish
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.models import Invoice, InvoiceItem
from app.modules.payments.constants import PaymentMethod, PaymentStatus
from app.modules.payments.models import Payment
from app.modules.purchase.constants import PurchaseStatus
from app.modules.purchase.models import PurchaseBill
from app.modules.reports.constants import (
    EntityType,
    PaidStatus,
    ProfitabilityFilter,
    RiskLevel,
    SupplierTransactionType,
    TransactionType,
)
from app.modules.reports.repository import ReportsRepository
from app.modules.supplier_payments.constants import PaymentMethod as SupplierPaymentMethod
from app.modules.supplier_payments.constants import SupplierPaymentStatus
from app.modules.supplier_payments.models import SupplierPayment
from app.modules.suppliers.models import Supplier
from app.modules.trip_catches.models import TripCatch
from app.modules.trip_expenses.models import TripExpense
from app.modules.trips.constants import TripStatus, TripType
from app.modules.trips.models import Trip

_D1 = date(2026, 7, 1)
_D2 = date(2026, 7, 5)
_D3 = date(2026, 7, 10)
_D4 = date(2026, 7, 15)


@pytest.fixture
async def repo(db_session: AsyncSession) -> ReportsRepository:
    return ReportsRepository(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - mirrors test_payment_repository.py's own
    fixture, for the same reason: the seeded default tenant may already
    carry invoices/payments from manual/exploratory testing."""
    tenant = Tenant(
        name="Reports Repo Test Tenant", slug=f"reports-repo-test-{uuid.uuid4().hex[:8]}"
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant.id


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


@pytest.fixture
async def company_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    company = await _make_company(db_session, tenant_id)
    return company.id


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
        "invoice_date": _D1,
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
        "payment_date": _D1,
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


@pytest.fixture
async def supplier_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    supplier = await _make_supplier(db_session, tenant_id)
    return supplier.id


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
        "bill_date": _D1,
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
        "payment_date": _D1,
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


class TestGetOpeningBalance:
    async def test_returns_zero_without_a_query_when_before_date_is_none(
        self, repo: ReportsRepository, tenant_id: uuid.UUID, company_id: uuid.UUID
    ) -> None:
        assert await repo.get_opening_balance(tenant_id, company_id, before_date=None) == Decimal(
            "0"
        )

    async def test_nets_invoices_minus_payments_strictly_before_the_date(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=_D1, total_amount=Decimal("1000.00")
        )
        await _make_payment(
            db_session, tenant_id, company_id, payment_date=_D2, amount=Decimal("400.00")
        )
        # On-or-after the boundary - must not be included.
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=_D3, total_amount=Decimal("500.00")
        )

        balance = await repo.get_opening_balance(tenant_id, company_id, before_date=_D3)
        assert balance == Decimal("600.00")

    async def test_zero_when_nothing_precedes_the_date(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(db_session, tenant_id, company_id, invoice_date=_D1)
        assert await repo.get_opening_balance(tenant_id, company_id, before_date=_D1) == Decimal(
            "0"
        )

    async def test_excludes_draft_invoices(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=_D1, status=InvoiceStatus.DRAFT
        )
        assert await repo.get_opening_balance(tenant_id, company_id, before_date=_D3) == Decimal(
            "0"
        )

    async def test_excludes_cancelled_invoices(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=_D1, status=InvoiceStatus.CANCELLED
        )
        assert await repo.get_opening_balance(tenant_id, company_id, before_date=_D3) == Decimal(
            "0"
        )

    async def test_excludes_draft_payments(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_payment(
            db_session, tenant_id, company_id, payment_date=_D1, status=PaymentStatus.DRAFT
        )
        assert await repo.get_opening_balance(tenant_id, company_id, before_date=_D3) == Decimal(
            "0"
        )

    async def test_excludes_soft_deleted_rows(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_date=_D1,
            deleted_at=datetime.now(UTC),
        )
        await _make_payment(
            db_session,
            tenant_id,
            company_id,
            payment_date=_D1,
            deleted_at=datetime.now(UTC),
        )
        assert await repo.get_opening_balance(tenant_id, company_id, before_date=_D3) == Decimal(
            "0"
        )

    async def test_scoped_to_one_company(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company_a = await _make_company(db_session, tenant_id)
        company_b = await _make_company(db_session, tenant_id)
        await _make_invoice(
            db_session, tenant_id, company_a.id, invoice_date=_D1, total_amount=Decimal("1000.00")
        )
        await _make_invoice(
            db_session, tenant_id, company_b.id, invoice_date=_D1, total_amount=Decimal("999.00")
        )

        balance = await repo.get_opening_balance(tenant_id, company_a.id, before_date=_D3)
        assert balance == Decimal("1000.00")

    async def test_scoped_to_one_tenant(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Reports Tenant", slug=f"other-reports-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_company = await _make_company(db_session, other_tenant.id)
        await _make_invoice(db_session, other_tenant.id, other_company.id, invoice_date=_D1)

        my_company = await _make_company(db_session, tenant_id)
        assert await repo.get_opening_balance(tenant_id, my_company.id, before_date=_D3) == Decimal(
            "0"
        )


class TestGetSummaryAggregates:
    async def test_sums_and_counts_within_the_date_range(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=_D1, total_amount=Decimal("1000.00")
        )
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=_D3, total_amount=Decimal("500.00")
        )
        await _make_payment(
            db_session, tenant_id, company_id, payment_date=_D2, amount=Decimal("400.00")
        )
        await _make_payment(
            db_session, tenant_id, company_id, payment_date=_D4, amount=Decimal("300.00")
        )

        aggregates = await repo.get_summary_aggregates(
            tenant_id, company_id, from_date=_D1, to_date=_D4
        )
        assert aggregates.total_debit == Decimal("1500.00")
        assert aggregates.total_credit == Decimal("700.00")
        assert aggregates.invoice_count == 2
        assert aggregates.payment_count == 2

    async def test_date_range_narrows_results(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=_D1, total_amount=Decimal("1000.00")
        )
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=_D3, total_amount=Decimal("500.00")
        )
        await _make_payment(
            db_session, tenant_id, company_id, payment_date=_D2, amount=Decimal("400.00")
        )
        await _make_payment(
            db_session, tenant_id, company_id, payment_date=_D4, amount=Decimal("300.00")
        )

        aggregates = await repo.get_summary_aggregates(
            tenant_id, company_id, from_date=_D2 + timedelta(days=1), to_date=_D4
        )
        assert aggregates.total_debit == Decimal("500.00")
        assert aggregates.total_credit == Decimal("300.00")
        assert aggregates.invoice_count == 1
        assert aggregates.payment_count == 1

    async def test_zero_and_no_dates_required(
        self, repo: ReportsRepository, tenant_id: uuid.UUID, company_id: uuid.UUID
    ) -> None:
        aggregates = await repo.get_summary_aggregates(
            tenant_id, company_id, from_date=None, to_date=None
        )
        assert aggregates.total_debit == Decimal("0")
        assert aggregates.total_credit == Decimal("0")
        assert aggregates.invoice_count == 0
        assert aggregates.payment_count == 0

    async def test_excludes_draft_and_cancelled_invoices_and_draft_payments(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=_D1, status=InvoiceStatus.DRAFT
        )
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=_D1, status=InvoiceStatus.CANCELLED
        )
        await _make_payment(
            db_session, tenant_id, company_id, payment_date=_D1, status=PaymentStatus.DRAFT
        )

        aggregates = await repo.get_summary_aggregates(
            tenant_id, company_id, from_date=_D1, to_date=_D4
        )
        assert aggregates.total_debit == Decimal("0")
        assert aggregates.total_credit == Decimal("0")
        assert aggregates.invoice_count == 0
        assert aggregates.payment_count == 0


class TestGetLedgerPage:
    async def _seed_alternating_transactions(
        self, db_session: AsyncSession, tenant_id: uuid.UUID, company_id: uuid.UUID
    ) -> tuple[Invoice, Payment, Invoice, Payment]:
        """Four transactions, chronologically A(debit) B(credit) C(debit)
        D(credit) - cumulative true balance: 1000, 600, 1100, 800."""
        invoice_a = await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_date=_D1,
            invoice_number="INV-A",
            total_amount=Decimal("1000.00"),
        )
        payment_b = await _make_payment(
            db_session,
            tenant_id,
            company_id,
            payment_date=_D2,
            payment_number="PAY-B",
            amount=Decimal("400.00"),
        )
        invoice_c = await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_date=_D3,
            invoice_number="INV-C",
            total_amount=Decimal("500.00"),
        )
        payment_d = await _make_payment(
            db_session,
            tenant_id,
            company_id,
            payment_date=_D4,
            payment_number="PAY-D",
            amount=Decimal("300.00"),
        )
        return invoice_a, payment_b, invoice_c, payment_d

    async def test_chronological_order_and_true_running_balance(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await self._seed_alternating_transactions(db_session, tenant_id, company_id)

        rows, total = await repo.get_ledger_page(
            tenant_id,
            company_id,
            from_date=None,
            to_date=None,
            transaction_type=None,
            page=1,
            page_size=10,
        )
        assert total == 4
        assert [r.reference_number for r in rows] == ["INV-A", "PAY-B", "INV-C", "PAY-D"]
        assert [r.cumulative for r in rows] == [
            Decimal("1000.00"),
            Decimal("600.00"),
            Decimal("1100.00"),
            Decimal("800.00"),
        ]

    async def test_transaction_type_filter_narrows_rows_but_keeps_true_cumulative(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        """The confirmed Session 1 design decision: filtering to Invoice
        only must not recompute the running balance from invoices alone -
        each returned row's cumulative must still reflect the true position
        in the full (invoice+payment) chronological sequence."""
        await self._seed_alternating_transactions(db_session, tenant_id, company_id)

        invoice_rows, invoice_total = await repo.get_ledger_page(
            tenant_id,
            company_id,
            from_date=None,
            to_date=None,
            transaction_type=TransactionType.INVOICE,
            page=1,
            page_size=10,
        )
        assert invoice_total == 2
        assert [r.reference_number for r in invoice_rows] == ["INV-A", "INV-C"]
        assert [r.cumulative for r in invoice_rows] == [Decimal("1000.00"), Decimal("1100.00")]

        payment_rows, payment_total = await repo.get_ledger_page(
            tenant_id,
            company_id,
            from_date=None,
            to_date=None,
            transaction_type=TransactionType.PAYMENT,
            page=1,
            page_size=10,
        )
        assert payment_total == 2
        assert [r.reference_number for r in payment_rows] == ["PAY-B", "PAY-D"]
        assert [r.cumulative for r in payment_rows] == [Decimal("600.00"), Decimal("800.00")]

    async def test_pagination_does_not_overlap_and_covers_all_rows(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await self._seed_alternating_transactions(db_session, tenant_id, company_id)

        page1, total1 = await repo.get_ledger_page(
            tenant_id,
            company_id,
            from_date=None,
            to_date=None,
            transaction_type=None,
            page=1,
            page_size=2,
        )
        page2, total2 = await repo.get_ledger_page(
            tenant_id,
            company_id,
            from_date=None,
            to_date=None,
            transaction_type=None,
            page=2,
            page_size=2,
        )
        assert total1 == 4
        assert total2 == 4
        assert [r.reference_number for r in page1] == ["INV-A", "PAY-B"]
        assert [r.reference_number for r in page2] == ["INV-C", "PAY-D"]

    async def test_page_past_the_end_returns_empty(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(db_session, tenant_id, company_id, invoice_date=_D1)

        rows, total = await repo.get_ledger_page(
            tenant_id,
            company_id,
            from_date=None,
            to_date=None,
            transaction_type=None,
            page=99,
            page_size=10,
        )
        assert total == 1
        assert rows == []

    async def test_excludes_draft_cancelled_and_deleted_rows(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=_D1, status=InvoiceStatus.DRAFT
        )
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=_D1, status=InvoiceStatus.CANCELLED
        )
        await _make_payment(
            db_session, tenant_id, company_id, payment_date=_D1, status=PaymentStatus.DRAFT
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_date=_D1,
            deleted_at=datetime.now(UTC),
        )

        rows, total = await repo.get_ledger_page(
            tenant_id,
            company_id,
            from_date=None,
            to_date=None,
            transaction_type=None,
            page=1,
            page_size=10,
        )
        assert total == 0
        assert rows == []

    async def test_scoped_to_one_tenant(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Ledger Page Tenant", slug=f"other-ledger-page-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_company = await _make_company(db_session, other_tenant.id)
        await _make_invoice(db_session, other_tenant.id, other_company.id, invoice_date=_D1)

        my_company = await _make_company(db_session, tenant_id)
        rows, total = await repo.get_ledger_page(
            tenant_id,
            my_company.id,
            from_date=None,
            to_date=None,
            transaction_type=None,
            page=1,
            page_size=10,
        )
        assert total == 0
        assert rows == []


class TestGetSupplierOpeningBalance:
    """Mirrors TestGetOpeningBalance exactly, on the buy side."""

    async def test_returns_zero_without_a_query_when_before_date_is_none(
        self, repo: ReportsRepository, tenant_id: uuid.UUID, supplier_id: uuid.UUID
    ) -> None:
        assert await repo.get_supplier_opening_balance(
            tenant_id, supplier_id, before_date=None
        ) == Decimal("0")

    async def test_nets_purchase_bills_minus_payments_strictly_before_the_date(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_date=_D1, total_amount=Decimal("1000.00")
        )
        await _make_supplier_payment(
            db_session, tenant_id, supplier_id, payment_date=_D2, amount=Decimal("400.00")
        )
        # On-or-after the boundary - must not be included.
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_date=_D3, total_amount=Decimal("500.00")
        )

        balance = await repo.get_supplier_opening_balance(tenant_id, supplier_id, before_date=_D3)
        assert balance == Decimal("600.00")

    async def test_excludes_draft_purchase_bills(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_date=_D1, status=PurchaseStatus.DRAFT
        )
        assert await repo.get_supplier_opening_balance(
            tenant_id, supplier_id, before_date=_D3
        ) == Decimal("0")

    async def test_excludes_cancelled_purchase_bills(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_date=_D1, status=PurchaseStatus.CANCELLED
        )
        assert await repo.get_supplier_opening_balance(
            tenant_id, supplier_id, before_date=_D3
        ) == Decimal("0")

    async def test_excludes_draft_supplier_payments(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_supplier_payment(
            db_session, tenant_id, supplier_id, payment_date=_D1, status=SupplierPaymentStatus.DRAFT
        )
        assert await repo.get_supplier_opening_balance(
            tenant_id, supplier_id, before_date=_D3
        ) == Decimal("0")

    async def test_excludes_soft_deleted_rows(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_date=_D1, deleted_at=datetime.now(UTC)
        )
        await _make_supplier_payment(
            db_session, tenant_id, supplier_id, payment_date=_D1, deleted_at=datetime.now(UTC)
        )
        assert await repo.get_supplier_opening_balance(
            tenant_id, supplier_id, before_date=_D3
        ) == Decimal("0")

    async def test_scoped_to_one_supplier(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier_a = await _make_supplier(db_session, tenant_id)
        supplier_b = await _make_supplier(db_session, tenant_id)
        await _make_purchase_bill(
            db_session, tenant_id, supplier_a.id, bill_date=_D1, total_amount=Decimal("1000.00")
        )
        await _make_purchase_bill(
            db_session, tenant_id, supplier_b.id, bill_date=_D1, total_amount=Decimal("999.00")
        )

        balance = await repo.get_supplier_opening_balance(tenant_id, supplier_a.id, before_date=_D3)
        assert balance == Decimal("1000.00")

    async def test_scoped_to_one_tenant(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Supplier Reports Tenant",
            slug=f"other-supplier-reports-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_supplier = await _make_supplier(db_session, other_tenant.id)
        await _make_purchase_bill(db_session, other_tenant.id, other_supplier.id, bill_date=_D1)

        my_supplier = await _make_supplier(db_session, tenant_id)
        assert await repo.get_supplier_opening_balance(
            tenant_id, my_supplier.id, before_date=_D3
        ) == Decimal("0")


class TestGetSupplierSummaryAggregates:
    """Mirrors TestGetSummaryAggregates exactly, on the buy side."""

    async def test_sums_and_counts_within_the_date_range(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_date=_D1, total_amount=Decimal("1000.00")
        )
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_date=_D3, total_amount=Decimal("500.00")
        )
        await _make_supplier_payment(
            db_session, tenant_id, supplier_id, payment_date=_D2, amount=Decimal("400.00")
        )
        await _make_supplier_payment(
            db_session, tenant_id, supplier_id, payment_date=_D4, amount=Decimal("300.00")
        )

        aggregates = await repo.get_supplier_summary_aggregates(
            tenant_id, supplier_id, from_date=_D1, to_date=_D4
        )
        assert aggregates.total_debit == Decimal("1500.00")
        assert aggregates.total_credit == Decimal("700.00")
        assert aggregates.purchase_bill_count == 2
        assert aggregates.supplier_payment_count == 2

    async def test_date_range_narrows_results(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_date=_D1, total_amount=Decimal("1000.00")
        )
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_date=_D3, total_amount=Decimal("500.00")
        )
        await _make_supplier_payment(
            db_session, tenant_id, supplier_id, payment_date=_D2, amount=Decimal("400.00")
        )
        await _make_supplier_payment(
            db_session, tenant_id, supplier_id, payment_date=_D4, amount=Decimal("300.00")
        )

        aggregates = await repo.get_supplier_summary_aggregates(
            tenant_id, supplier_id, from_date=_D2 + timedelta(days=1), to_date=_D4
        )
        assert aggregates.total_debit == Decimal("500.00")
        assert aggregates.total_credit == Decimal("300.00")
        assert aggregates.purchase_bill_count == 1
        assert aggregates.supplier_payment_count == 1

    async def test_zero_and_no_dates_required(
        self, repo: ReportsRepository, tenant_id: uuid.UUID, supplier_id: uuid.UUID
    ) -> None:
        aggregates = await repo.get_supplier_summary_aggregates(
            tenant_id, supplier_id, from_date=None, to_date=None
        )
        assert aggregates.total_debit == Decimal("0")
        assert aggregates.total_credit == Decimal("0")
        assert aggregates.purchase_bill_count == 0
        assert aggregates.supplier_payment_count == 0

    async def test_excludes_draft_and_cancelled_bills_and_draft_payments(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_date=_D1, status=PurchaseStatus.DRAFT
        )
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_date=_D1, status=PurchaseStatus.CANCELLED
        )
        await _make_supplier_payment(
            db_session, tenant_id, supplier_id, payment_date=_D1, status=SupplierPaymentStatus.DRAFT
        )

        aggregates = await repo.get_supplier_summary_aggregates(
            tenant_id, supplier_id, from_date=_D1, to_date=_D4
        )
        assert aggregates.total_debit == Decimal("0")
        assert aggregates.total_credit == Decimal("0")
        assert aggregates.purchase_bill_count == 0
        assert aggregates.supplier_payment_count == 0


class TestGetSupplierLedgerPage:
    """Mirrors TestGetLedgerPage exactly, on the buy side."""

    async def _seed_alternating_transactions(
        self, db_session: AsyncSession, tenant_id: uuid.UUID, supplier_id: uuid.UUID
    ) -> tuple[PurchaseBill, SupplierPayment, PurchaseBill, SupplierPayment]:
        """Four transactions, chronologically A(debit) B(credit) C(debit)
        D(credit) - cumulative true balance: 1000, 600, 1100, 800."""
        bill_a = await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier_id,
            bill_date=_D1,
            bill_number="PB-A",
            total_amount=Decimal("1000.00"),
        )
        payment_b = await _make_supplier_payment(
            db_session,
            tenant_id,
            supplier_id,
            payment_date=_D2,
            payment_number="SPAY-B",
            amount=Decimal("400.00"),
        )
        bill_c = await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier_id,
            bill_date=_D3,
            bill_number="PB-C",
            total_amount=Decimal("500.00"),
        )
        payment_d = await _make_supplier_payment(
            db_session,
            tenant_id,
            supplier_id,
            payment_date=_D4,
            payment_number="SPAY-D",
            amount=Decimal("300.00"),
        )
        return bill_a, payment_b, bill_c, payment_d

    async def test_chronological_order_and_true_running_balance(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await self._seed_alternating_transactions(db_session, tenant_id, supplier_id)

        rows, total = await repo.get_supplier_ledger_page(
            tenant_id,
            supplier_id,
            from_date=None,
            to_date=None,
            transaction_type=None,
            page=1,
            page_size=10,
        )
        assert total == 4
        assert [r.reference_number for r in rows] == ["PB-A", "SPAY-B", "PB-C", "SPAY-D"]
        assert [r.cumulative for r in rows] == [
            Decimal("1000.00"),
            Decimal("600.00"),
            Decimal("1100.00"),
            Decimal("800.00"),
        ]

    async def test_transaction_type_filter_narrows_rows_but_keeps_true_cumulative(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        """The same confirmed design decision as the Customer Ledger's own
        test: filtering to Purchase Bill only must not recompute the
        running balance from bills alone - each returned row's cumulative
        must still reflect the true position in the full (bill+payment)
        chronological sequence."""
        await self._seed_alternating_transactions(db_session, tenant_id, supplier_id)

        bill_rows, bill_total = await repo.get_supplier_ledger_page(
            tenant_id,
            supplier_id,
            from_date=None,
            to_date=None,
            transaction_type=SupplierTransactionType.PURCHASE_BILL,
            page=1,
            page_size=10,
        )
        assert bill_total == 2
        assert [r.reference_number for r in bill_rows] == ["PB-A", "PB-C"]
        assert [r.cumulative for r in bill_rows] == [Decimal("1000.00"), Decimal("1100.00")]

        payment_rows, payment_total = await repo.get_supplier_ledger_page(
            tenant_id,
            supplier_id,
            from_date=None,
            to_date=None,
            transaction_type=SupplierTransactionType.SUPPLIER_PAYMENT,
            page=1,
            page_size=10,
        )
        assert payment_total == 2
        assert [r.reference_number for r in payment_rows] == ["SPAY-B", "SPAY-D"]
        assert [r.cumulative for r in payment_rows] == [Decimal("600.00"), Decimal("800.00")]

    async def test_pagination_does_not_overlap_and_covers_all_rows(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await self._seed_alternating_transactions(db_session, tenant_id, supplier_id)

        page1, total1 = await repo.get_supplier_ledger_page(
            tenant_id,
            supplier_id,
            from_date=None,
            to_date=None,
            transaction_type=None,
            page=1,
            page_size=2,
        )
        page2, total2 = await repo.get_supplier_ledger_page(
            tenant_id,
            supplier_id,
            from_date=None,
            to_date=None,
            transaction_type=None,
            page=2,
            page_size=2,
        )
        assert total1 == 4
        assert total2 == 4
        assert [r.reference_number for r in page1] == ["PB-A", "SPAY-B"]
        assert [r.reference_number for r in page2] == ["PB-C", "SPAY-D"]

    async def test_page_past_the_end_returns_empty(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_purchase_bill(db_session, tenant_id, supplier_id, bill_date=_D1)

        rows, total = await repo.get_supplier_ledger_page(
            tenant_id,
            supplier_id,
            from_date=None,
            to_date=None,
            transaction_type=None,
            page=99,
            page_size=10,
        )
        assert total == 1
        assert rows == []

    async def test_excludes_draft_cancelled_and_deleted_rows(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_date=_D1, status=PurchaseStatus.DRAFT
        )
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_date=_D1, status=PurchaseStatus.CANCELLED
        )
        await _make_supplier_payment(
            db_session, tenant_id, supplier_id, payment_date=_D1, status=SupplierPaymentStatus.DRAFT
        )
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_date=_D1, deleted_at=datetime.now(UTC)
        )

        rows, total = await repo.get_supplier_ledger_page(
            tenant_id,
            supplier_id,
            from_date=None,
            to_date=None,
            transaction_type=None,
            page=1,
            page_size=10,
        )
        assert total == 0
        assert rows == []

    async def test_scoped_to_one_tenant(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Supplier Ledger Page Tenant",
            slug=f"other-supplier-ledger-page-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_supplier = await _make_supplier(db_session, other_tenant.id)
        await _make_purchase_bill(db_session, other_tenant.id, other_supplier.id, bill_date=_D1)

        my_supplier = await _make_supplier(db_session, tenant_id)
        rows, total = await repo.get_supplier_ledger_page(
            tenant_id,
            my_supplier.id,
            from_date=None,
            to_date=None,
            transaction_type=None,
            page=1,
            page_size=10,
        )
        assert total == 0
        assert rows == []


class TestGetSalesReport:
    """TASKS.md Sprint 11 Session 3 - one row per issued invoice, no
    running balance/UNION involved, unlike the Ledgers above."""

    async def test_lists_one_row_per_issued_invoice_newest_first(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_number="INV-A", invoice_date=_D1
        )
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_number="INV-C", invoice_date=_D3
        )
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_number="INV-B", invoice_date=_D2
        )

        rows, aggregates, total = await repo.get_sales_report(
            tenant_id,
            customer_id=None,
            status=None,
            paid_status=None,
            from_date=None,
            to_date=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 3
        assert aggregates.invoice_count == 3
        # invoice_date DESC, invoice_number DESC - the fixed SORTING order.
        assert [r.invoice_number for r in rows] == ["INV-C", "INV-B", "INV-A"]

    async def test_excludes_draft_invoices_always(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(db_session, tenant_id, company_id, status=InvoiceStatus.DRAFT)
        await _make_invoice(db_session, tenant_id, company_id, status=InvoiceStatus.ISSUED)

        rows, aggregates, total = await repo.get_sales_report(
            tenant_id,
            customer_id=None,
            status=None,
            paid_status=None,
            from_date=None,
            to_date=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert aggregates.invoice_count == 1

    async def test_excludes_draft_even_when_status_filter_requests_it(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(db_session, tenant_id, company_id, status=InvoiceStatus.DRAFT)

        rows, aggregates, total = await repo.get_sales_report(
            tenant_id,
            customer_id=None,
            status=InvoiceStatus.DRAFT,
            paid_status=None,
            from_date=None,
            to_date=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 0
        assert rows == []

    async def test_includes_cancelled_invoices_by_default(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        """Unlike the Ledger (which always excludes cancelled invoices for
        balance integrity), the Sales Report is a transactional audit list -
        a cancelled invoice was still issued at some point, so it stays
        visible unless the caller explicitly filters it out."""
        await _make_invoice(db_session, tenant_id, company_id, status=InvoiceStatus.CANCELLED)

        rows, aggregates, total = await repo.get_sales_report(
            tenant_id,
            customer_id=None,
            status=None,
            paid_status=None,
            from_date=None,
            to_date=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert aggregates.invoice_count == 1

    async def test_summary_reflects_full_filtered_set_not_just_the_page(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_date=_D1,
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("1000.00"),
            balance_amount=Decimal("0"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_date=_D2,
            total_amount=Decimal("500.00"),
            paid_amount=Decimal("0"),
            balance_amount=Decimal("500.00"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_date=_D3,
            total_amount=Decimal("2000.00"),
            paid_amount=Decimal("500.00"),
            balance_amount=Decimal("1500.00"),
        )

        rows, aggregates, total = await repo.get_sales_report(
            tenant_id,
            customer_id=None,
            status=None,
            paid_status=None,
            from_date=None,
            to_date=None,
            q=None,
            page=1,
            page_size=1,
        )
        assert len(rows) == 1
        assert total == 3
        assert aggregates.total_sales == Decimal("3500.00")
        assert aggregates.total_paid == Decimal("1500.00")
        assert aggregates.outstanding == Decimal("2000.00")
        assert aggregates.invoice_count == 3
        # Postgres' avg(numeric) carries extra fractional digits - quantize
        # before comparing, mirroring what ReportsService._money does before
        # this value ever reaches a response.
        assert aggregates.average_invoice.quantize(Decimal("0.01")) == Decimal("1166.67")
        assert aggregates.largest_invoice == Decimal("2000.00")

    async def test_zero_rows_summary_has_no_division_by_zero(
        self, repo: ReportsRepository, tenant_id: uuid.UUID
    ) -> None:
        rows, aggregates, total = await repo.get_sales_report(
            tenant_id,
            customer_id=None,
            status=None,
            paid_status=None,
            from_date=None,
            to_date=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 0
        assert aggregates.total_sales == Decimal("0")
        assert aggregates.average_invoice == Decimal("0")
        assert aggregates.largest_invoice == Decimal("0")

    async def test_customer_id_filter_narrows(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company_a = await _make_company(db_session, tenant_id)
        company_b = await _make_company(db_session, tenant_id)
        await _make_invoice(db_session, tenant_id, company_a.id, invoice_number="INV-A")
        await _make_invoice(db_session, tenant_id, company_b.id, invoice_number="INV-B")

        rows, aggregates, total = await repo.get_sales_report(
            tenant_id,
            customer_id=company_a.id,
            status=None,
            paid_status=None,
            from_date=None,
            to_date=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].invoice_number == "INV-A"

    async def test_unmatched_customer_id_yields_zero_rows_not_an_error(
        self, repo: ReportsRepository, tenant_id: uuid.UUID
    ) -> None:
        rows, aggregates, total = await repo.get_sales_report(
            tenant_id,
            customer_id=uuid.uuid4(),
            status=None,
            paid_status=None,
            from_date=None,
            to_date=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 0
        assert rows == []

    async def test_status_filter_narrows(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(db_session, tenant_id, company_id, status=InvoiceStatus.ISSUED)
        await _make_invoice(db_session, tenant_id, company_id, status=InvoiceStatus.PAID)

        rows, aggregates, total = await repo.get_sales_report(
            tenant_id,
            customer_id=None,
            status=InvoiceStatus.PAID,
            paid_status=None,
            from_date=None,
            to_date=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].status == InvoiceStatus.PAID

    async def test_paid_status_filter(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_number="UNPAID",
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("0"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_number="PARTIAL",
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("400.00"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_number="PAID",
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("1000.00"),
        )

        for paid_status, expected in (
            (PaidStatus.UNPAID, "UNPAID"),
            (PaidStatus.PARTIALLY_PAID, "PARTIAL"),
            (PaidStatus.PAID, "PAID"),
        ):
            rows, _aggregates, total = await repo.get_sales_report(
                tenant_id,
                customer_id=None,
                status=None,
                paid_status=paid_status,
                from_date=None,
                to_date=None,
                q=None,
                page=1,
                page_size=10,
            )
            assert total == 1, paid_status
            assert rows[0].invoice_number == expected

    async def test_date_range_narrows(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_number="INV-A", invoice_date=_D1
        )
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_number="INV-C", invoice_date=_D3
        )

        rows, aggregates, total = await repo.get_sales_report(
            tenant_id,
            customer_id=None,
            status=None,
            paid_status=None,
            from_date=_D2,
            to_date=_D4,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].invoice_number == "INV-C"

    async def test_q_searches_invoice_number_and_customer_name(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id, name="Konkan Seafoods")
        other_company = await _make_company(db_session, tenant_id, name="Malabar Traders")
        await _make_invoice(db_session, tenant_id, company.id, invoice_number="INV-XYZ")
        await _make_invoice(db_session, tenant_id, other_company.id, invoice_number="INV-OTHER")

        by_number = await repo.get_sales_report(
            tenant_id,
            customer_id=None,
            status=None,
            paid_status=None,
            from_date=None,
            to_date=None,
            q="XYZ",
            page=1,
            page_size=10,
        )
        assert by_number[2] == 1
        assert by_number[0][0].invoice_number == "INV-XYZ"

        by_name = await repo.get_sales_report(
            tenant_id,
            customer_id=None,
            status=None,
            paid_status=None,
            from_date=None,
            to_date=None,
            q="Konkan",
            page=1,
            page_size=10,
        )
        assert by_name[2] == 1
        assert by_name[0][0].invoice_number == "INV-XYZ"

    async def test_scoped_to_one_tenant(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Sales Report Tenant", slug=f"other-sales-report-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_company = await _make_company(db_session, other_tenant.id)
        await _make_invoice(db_session, other_tenant.id, other_company.id)

        rows, aggregates, total = await repo.get_sales_report(
            tenant_id,
            customer_id=None,
            status=None,
            paid_status=None,
            from_date=None,
            to_date=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 0
        assert rows == []


class TestGetPurchaseReport:
    """Mirrors TestGetSalesReport exactly, on the buy side."""

    async def test_lists_one_row_per_posted_bill_newest_first(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_number="PB-A", bill_date=_D1
        )
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_number="PB-C", bill_date=_D3
        )
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_number="PB-B", bill_date=_D2
        )

        rows, aggregates, total = await repo.get_purchase_report(
            tenant_id,
            supplier_id=None,
            status=None,
            paid_status=None,
            from_date=None,
            to_date=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 3
        assert aggregates.bill_count == 3
        assert [r.bill_number for r in rows] == ["PB-C", "PB-B", "PB-A"]

    async def test_excludes_draft_bills_always(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_purchase_bill(db_session, tenant_id, supplier_id, status=PurchaseStatus.DRAFT)
        await _make_purchase_bill(db_session, tenant_id, supplier_id, status=PurchaseStatus.POSTED)

        rows, aggregates, total = await repo.get_purchase_report(
            tenant_id,
            supplier_id=None,
            status=None,
            paid_status=None,
            from_date=None,
            to_date=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert aggregates.bill_count == 1

    async def test_includes_cancelled_bills_by_default(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, status=PurchaseStatus.CANCELLED
        )

        rows, aggregates, total = await repo.get_purchase_report(
            tenant_id,
            supplier_id=None,
            status=None,
            paid_status=None,
            from_date=None,
            to_date=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1

    async def test_summary_reflects_full_filtered_set_not_just_the_page(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier_id,
            bill_date=_D1,
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("1000.00"),
            balance_amount=Decimal("0"),
        )
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier_id,
            bill_date=_D2,
            total_amount=Decimal("500.00"),
            paid_amount=Decimal("0"),
            balance_amount=Decimal("500.00"),
        )

        rows, aggregates, total = await repo.get_purchase_report(
            tenant_id,
            supplier_id=None,
            status=None,
            paid_status=None,
            from_date=None,
            to_date=None,
            q=None,
            page=1,
            page_size=1,
        )
        assert len(rows) == 1
        assert total == 2
        assert aggregates.total_purchases == Decimal("1500.00")
        assert aggregates.total_paid == Decimal("1000.00")
        assert aggregates.outstanding == Decimal("500.00")
        assert aggregates.largest_bill == Decimal("1000.00")

    async def test_supplier_id_filter_narrows(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier_a = await _make_supplier(db_session, tenant_id)
        supplier_b = await _make_supplier(db_session, tenant_id)
        await _make_purchase_bill(db_session, tenant_id, supplier_a.id, bill_number="PB-A")
        await _make_purchase_bill(db_session, tenant_id, supplier_b.id, bill_number="PB-B")

        rows, aggregates, total = await repo.get_purchase_report(
            tenant_id,
            supplier_id=supplier_a.id,
            status=None,
            paid_status=None,
            from_date=None,
            to_date=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].bill_number == "PB-A"

    async def test_status_filter_narrows(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_purchase_bill(db_session, tenant_id, supplier_id, status=PurchaseStatus.POSTED)
        await _make_purchase_bill(db_session, tenant_id, supplier_id, status=PurchaseStatus.PAID)

        rows, aggregates, total = await repo.get_purchase_report(
            tenant_id,
            supplier_id=None,
            status=PurchaseStatus.PAID,
            paid_status=None,
            from_date=None,
            to_date=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].status == PurchaseStatus.PAID

    async def test_paid_status_filter(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier_id,
            bill_number="UNPAID",
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("0"),
        )
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier_id,
            bill_number="PAID",
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("1000.00"),
        )

        rows, _aggregates, total = await repo.get_purchase_report(
            tenant_id,
            supplier_id=None,
            status=None,
            paid_status=PaidStatus.PAID,
            from_date=None,
            to_date=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].bill_number == "PAID"

    async def test_date_range_narrows(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_number="PB-A", bill_date=_D1
        )
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, bill_number="PB-C", bill_date=_D3
        )

        rows, aggregates, total = await repo.get_purchase_report(
            tenant_id,
            supplier_id=None,
            status=None,
            paid_status=None,
            from_date=_D2,
            to_date=_D4,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].bill_number == "PB-C"

    async def test_q_searches_bill_number_and_supplier_name(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier = await _make_supplier(db_session, tenant_id, name="Coastal Fish Suppliers")
        other_supplier = await _make_supplier(db_session, tenant_id, name="Deep Sea Traders")
        await _make_purchase_bill(db_session, tenant_id, supplier.id, bill_number="PB-XYZ")
        await _make_purchase_bill(db_session, tenant_id, other_supplier.id, bill_number="PB-OTHER")

        by_number = await repo.get_purchase_report(
            tenant_id,
            supplier_id=None,
            status=None,
            paid_status=None,
            from_date=None,
            to_date=None,
            q="XYZ",
            page=1,
            page_size=10,
        )
        assert by_number[2] == 1
        assert by_number[0][0].bill_number == "PB-XYZ"

        by_name = await repo.get_purchase_report(
            tenant_id,
            supplier_id=None,
            status=None,
            paid_status=None,
            from_date=None,
            to_date=None,
            q="Coastal",
            page=1,
            page_size=10,
        )
        assert by_name[2] == 1
        assert by_name[0][0].bill_number == "PB-XYZ"

    async def test_scoped_to_one_tenant(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Purchase Report Tenant",
            slug=f"other-purchase-report-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_supplier = await _make_supplier(db_session, other_tenant.id)
        await _make_purchase_bill(db_session, other_tenant.id, other_supplier.id)

        rows, aggregates, total = await repo.get_purchase_report(
            tenant_id,
            supplier_id=None,
            status=None,
            paid_status=None,
            from_date=None,
            to_date=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 0
        assert rows == []


# A fixed reference date for Outstanding/Aging Report tests - both
# repository methods take `today` as an explicit parameter (mirrors
# DashboardRepository's own today/month_start pattern), so tests never
# depend on the real wall-clock date.
_AGING_TODAY = date(2026, 8, 15)


class TestGetOutstandingSummary:
    """TASKS.md Sprint 11 Session 3 Phase B - always the full, unfiltered
    AR/AP picture, regardless of entity_type or any row filter."""

    async def test_sums_ar_and_ap_across_all_entities(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company_a = await _make_company(db_session, tenant_id)
        company_b = await _make_company(db_session, tenant_id)
        await _make_invoice(
            db_session,
            tenant_id,
            company_a.id,
            total_amount=Decimal("1000.00"),
            balance_amount=Decimal("1000.00"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company_b.id,
            total_amount=Decimal("500.00"),
            balance_amount=Decimal("500.00"),
        )
        supplier = await _make_supplier(db_session, tenant_id)
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            total_amount=Decimal("300.00"),
            balance_amount=Decimal("300.00"),
        )

        summary = await repo.get_outstanding_summary(tenant_id, today=_AGING_TODAY)
        assert summary.accounts_receivable == Decimal("1500.00")
        assert summary.accounts_payable == Decimal("300.00")
        assert summary.customers_with_outstanding == 2
        assert summary.suppliers_with_outstanding == 1

    async def test_overdue_receivable_and_payable(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id)
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            due_date=_AGING_TODAY - timedelta(days=10),
            total_amount=Decimal("1000.00"),
            balance_amount=Decimal("1000.00"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company.id,
            due_date=_AGING_TODAY + timedelta(days=10),
            total_amount=Decimal("500.00"),
            balance_amount=Decimal("500.00"),
        )
        supplier = await _make_supplier(db_session, tenant_id)
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            due_date=_AGING_TODAY - timedelta(days=5),
            total_amount=Decimal("200.00"),
            balance_amount=Decimal("200.00"),
        )

        summary = await repo.get_outstanding_summary(tenant_id, today=_AGING_TODAY)
        assert summary.overdue_receivable == Decimal("1000.00")
        assert summary.overdue_payable == Decimal("200.00")

    async def test_excludes_draft_and_cancelled(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(db_session, tenant_id, company_id, status=InvoiceStatus.DRAFT)
        await _make_invoice(db_session, tenant_id, company_id, status=InvoiceStatus.CANCELLED)

        summary = await repo.get_outstanding_summary(tenant_id, today=_AGING_TODAY)
        assert summary.accounts_receivable == Decimal("0")
        assert summary.customers_with_outstanding == 0

    async def test_scoped_to_one_tenant(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Outstanding Summary Tenant",
            slug=f"other-outstanding-summary-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_company = await _make_company(db_session, other_tenant.id)
        await _make_invoice(db_session, other_tenant.id, other_company.id)

        summary = await repo.get_outstanding_summary(tenant_id, today=_AGING_TODAY)
        assert summary.accounts_receivable == Decimal("0")
        assert summary.customers_with_outstanding == 0


class TestGetOutstandingRowsCustomer:
    async def _seed_three_risk_tiers(
        self, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> tuple[Company, Company, Company]:
        low = await _make_company(db_session, tenant_id, name="Low Risk Co")
        await _make_invoice(
            db_session,
            tenant_id,
            low.id,
            due_date=_AGING_TODAY + timedelta(days=10),
            balance_amount=Decimal("300.00"),
        )
        medium = await _make_company(db_session, tenant_id, name="Medium Risk Co")
        await _make_invoice(
            db_session,
            tenant_id,
            medium.id,
            due_date=_AGING_TODAY - timedelta(days=15),
            balance_amount=Decimal("1000.00"),
        )
        high = await _make_company(db_session, tenant_id, name="High Risk Co")
        await _make_invoice(
            db_session,
            tenant_id,
            high.id,
            due_date=_AGING_TODAY - timedelta(days=75),
            balance_amount=Decimal("500.00"),
        )
        return low, medium, high

    async def test_computes_outstanding_overdue_current_and_risk(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await self._seed_three_risk_tiers(db_session, tenant_id)

        rows, total = await repo.get_outstanding_rows(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            from_date=None,
            to_date=None,
            outstanding_only=False,
            overdue_only=False,
            risk_level=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 3
        by_name = {row.entity_name: row for row in rows}

        assert by_name["Medium Risk Co"].outstanding_amount == Decimal("1000.00")
        assert by_name["Medium Risk Co"].overdue_amount == Decimal("1000.00")
        assert by_name["Medium Risk Co"].current_amount == Decimal("0")
        assert by_name["Medium Risk Co"].risk_level == RiskLevel.MEDIUM

        assert by_name["High Risk Co"].risk_level == RiskLevel.HIGH

        assert by_name["Low Risk Co"].overdue_amount == Decimal("0")
        assert by_name["Low Risk Co"].current_amount == Decimal("300.00")
        assert by_name["Low Risk Co"].risk_level == RiskLevel.LOW

        # Outstanding DESC, then Name ASC - TASKS.md's fixed SORTING order.
        assert [row.entity_name for row in rows] == [
            "Medium Risk Co",
            "High Risk Co",
            "Low Risk Co",
        ]

    async def test_risk_level_filter(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await self._seed_three_risk_tiers(db_session, tenant_id)

        rows, total = await repo.get_outstanding_rows(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            from_date=None,
            to_date=None,
            outstanding_only=False,
            overdue_only=False,
            risk_level=RiskLevel.HIGH,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].entity_name == "High Risk Co"

    async def test_outstanding_only_filter(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        paid_co = await _make_company(db_session, tenant_id, name="Paid Co")
        await _make_invoice(
            db_session,
            tenant_id,
            paid_co.id,
            total_amount=Decimal("100.00"),
            paid_amount=Decimal("100.00"),
            balance_amount=Decimal("0"),
        )
        owing_co = await _make_company(db_session, tenant_id, name="Owing Co")
        await _make_invoice(
            db_session,
            tenant_id,
            owing_co.id,
            total_amount=Decimal("200.00"),
            balance_amount=Decimal("200.00"),
        )

        rows, total = await repo.get_outstanding_rows(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            from_date=None,
            to_date=None,
            outstanding_only=True,
            overdue_only=False,
            risk_level=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].entity_name == "Owing Co"

        _rows_all, total_all = await repo.get_outstanding_rows(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            from_date=None,
            to_date=None,
            outstanding_only=False,
            overdue_only=False,
            risk_level=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total_all == 2

    async def test_overdue_only_filter(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        overdue_co = await _make_company(db_session, tenant_id, name="Overdue Co")
        await _make_invoice(
            db_session,
            tenant_id,
            overdue_co.id,
            due_date=_AGING_TODAY - timedelta(days=5),
            balance_amount=Decimal("1000.00"),
        )
        current_co = await _make_company(db_session, tenant_id, name="Current Co")
        await _make_invoice(
            db_session,
            tenant_id,
            current_co.id,
            due_date=_AGING_TODAY + timedelta(days=5),
            balance_amount=Decimal("500.00"),
        )

        rows, total = await repo.get_outstanding_rows(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            from_date=None,
            to_date=None,
            outstanding_only=False,
            overdue_only=True,
            risk_level=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].entity_name == "Overdue Co"

    async def test_last_transaction_and_payment_dates_and_pending_count(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_date=date(2026, 7, 1),
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("1000.00"),
            balance_amount=Decimal("0"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_date=date(2026, 7, 20),
            total_amount=Decimal("500.00"),
            balance_amount=Decimal("500.00"),
        )
        await _make_payment(db_session, tenant_id, company_id, payment_date=date(2026, 7, 10))
        await _make_payment(db_session, tenant_id, company_id, payment_date=date(2026, 7, 25))

        rows, total = await repo.get_outstanding_rows(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            from_date=None,
            to_date=None,
            outstanding_only=False,
            overdue_only=False,
            risk_level=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        row = rows[0]
        assert row.last_transaction_date == date(2026, 7, 20)
        assert row.last_payment_date == date(2026, 7, 25)
        assert row.pending_count == 1

    async def test_date_range_narrows_which_invoices_count(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_date=date(2026, 7, 1),
            balance_amount=Decimal("1000.00"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_date=date(2026, 7, 20),
            balance_amount=Decimal("500.00"),
        )

        rows, total = await repo.get_outstanding_rows(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            from_date=date(2026, 7, 15),
            to_date=date(2026, 7, 31),
            outstanding_only=False,
            overdue_only=False,
            risk_level=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].outstanding_amount == Decimal("500.00")

    async def test_q_searches_name_and_code(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id, name="Konkan Seafoods", code="KNK-01")
        other = await _make_company(db_session, tenant_id, name="Malabar Traders", code="MAL-01")
        await _make_invoice(db_session, tenant_id, company.id, balance_amount=Decimal("100.00"))
        await _make_invoice(db_session, tenant_id, other.id, balance_amount=Decimal("100.00"))

        rows, total = await repo.get_outstanding_rows(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            from_date=None,
            to_date=None,
            outstanding_only=False,
            overdue_only=False,
            risk_level=None,
            q="Konkan",
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].entity_name == "Konkan Seafoods"

    async def test_excludes_draft_and_cancelled_invoices(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(db_session, tenant_id, company_id, status=InvoiceStatus.DRAFT)
        await _make_invoice(db_session, tenant_id, company_id, status=InvoiceStatus.CANCELLED)

        rows, total = await repo.get_outstanding_rows(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            from_date=None,
            to_date=None,
            outstanding_only=False,
            overdue_only=False,
            risk_level=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 0
        assert rows == []

    async def test_pagination(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        for i in range(3):
            company = await _make_company(db_session, tenant_id, name=f"Company {chr(65 + i)}")
            await _make_invoice(
                db_session, tenant_id, company.id, balance_amount=Decimal(f"{100 * (i + 1)}.00")
            )

        page1, total1 = await repo.get_outstanding_rows(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            from_date=None,
            to_date=None,
            outstanding_only=False,
            overdue_only=False,
            risk_level=None,
            q=None,
            page=1,
            page_size=2,
        )
        page2, total2 = await repo.get_outstanding_rows(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            from_date=None,
            to_date=None,
            outstanding_only=False,
            overdue_only=False,
            risk_level=None,
            q=None,
            page=2,
            page_size=2,
        )
        assert total1 == 3
        assert total2 == 3
        assert len(page1) == 2
        assert len(page2) == 1

    async def test_scoped_to_one_tenant(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Outstanding Rows Tenant",
            slug=f"other-outstanding-rows-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_company = await _make_company(db_session, other_tenant.id)
        await _make_invoice(db_session, other_tenant.id, other_company.id)

        rows, total = await repo.get_outstanding_rows(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            from_date=None,
            to_date=None,
            outstanding_only=False,
            overdue_only=False,
            risk_level=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 0
        assert rows == []


class TestGetOutstandingRowsSupplier:
    """Mirrors TestGetOutstandingRowsCustomer's core behavior, on the buy
    side - a lighter smoke-test since the underlying query shape is
    identical (_finalize_outstanding_rows is fully shared)."""

    async def test_computes_outstanding_overdue_and_last_payment_date(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier = await _make_supplier(db_session, tenant_id, name="Coastal Fish Suppliers")
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier.id,
            bill_date=date(2026, 7, 1),
            due_date=_AGING_TODAY - timedelta(days=10),
            total_amount=Decimal("1000.00"),
            balance_amount=Decimal("1000.00"),
        )
        await _make_supplier_payment(
            db_session, tenant_id, supplier.id, payment_date=date(2026, 7, 15)
        )

        rows, total = await repo.get_outstanding_rows(
            tenant_id,
            entity_type=EntityType.SUPPLIER,
            today=_AGING_TODAY,
            from_date=None,
            to_date=None,
            outstanding_only=False,
            overdue_only=False,
            risk_level=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        row = rows[0]
        assert row.entity_name == "Coastal Fish Suppliers"
        assert row.outstanding_amount == Decimal("1000.00")
        assert row.overdue_amount == Decimal("1000.00")
        assert row.last_payment_date == date(2026, 7, 15)
        assert row.risk_level == RiskLevel.MEDIUM

    async def test_excludes_draft_and_cancelled_bills(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_purchase_bill(db_session, tenant_id, supplier_id, status=PurchaseStatus.DRAFT)
        await _make_purchase_bill(
            db_session, tenant_id, supplier_id, status=PurchaseStatus.CANCELLED
        )

        rows, total = await repo.get_outstanding_rows(
            tenant_id,
            entity_type=EntityType.SUPPLIER,
            today=_AGING_TODAY,
            from_date=None,
            to_date=None,
            outstanding_only=False,
            overdue_only=False,
            risk_level=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 0

    async def test_scoped_to_one_tenant(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Outstanding Supplier Tenant",
            slug=f"other-outstanding-supplier-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_supplier = await _make_supplier(db_session, other_tenant.id)
        await _make_purchase_bill(db_session, other_tenant.id, other_supplier.id)

        rows, total = await repo.get_outstanding_rows(
            tenant_id,
            entity_type=EntityType.SUPPLIER,
            today=_AGING_TODAY,
            from_date=None,
            to_date=None,
            outstanding_only=False,
            overdue_only=False,
            risk_level=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 0


class TestGetAgingReportCustomer:
    async def test_bucket_allocation(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_number="CUR",
            due_date=_AGING_TODAY + timedelta(days=10),
            balance_amount=Decimal("100.00"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_number="B1",
            due_date=_AGING_TODAY - timedelta(days=15),
            balance_amount=Decimal("200.00"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_number="B2",
            due_date=_AGING_TODAY - timedelta(days=45),
            balance_amount=Decimal("300.00"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_number="B3",
            due_date=_AGING_TODAY - timedelta(days=75),
            balance_amount=Decimal("400.00"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_number="B4",
            due_date=_AGING_TODAY - timedelta(days=100),
            balance_amount=Decimal("500.00"),
        )

        rows, summary, total = await repo.get_aging_report(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            outstanding_only=False,
            risk_level=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        row = rows[0]
        assert row.current_amount == Decimal("100.00")
        assert row.days_1_30 == Decimal("200.00")
        assert row.days_31_60 == Decimal("300.00")
        assert row.days_61_90 == Decimal("400.00")
        assert row.days_90_plus == Decimal("500.00")
        assert row.total == Decimal("1500.00")
        assert row.risk_level == RiskLevel.HIGH

        assert summary.current_total == Decimal("100.00")
        assert summary.days_1_30_total == Decimal("200.00")
        assert summary.days_31_60_total == Decimal("300.00")
        assert summary.days_61_90_total == Decimal("400.00")
        assert summary.days_90_plus_total == Decimal("500.00")
        assert summary.grand_total == Decimal("1500.00")

    async def test_bucket_boundaries(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        """Exact boundary days (30/31/60/61/90/91) land in the buckets
        TASKS.md's own labels imply: "1-30"/"31-60"/"61-90" are inclusive
        on both ends, "90+" is exclusive of 90 itself."""
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_number="EXACT30",
            due_date=_AGING_TODAY - timedelta(days=30),
            balance_amount=Decimal("100.00"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_number="EXACT31",
            due_date=_AGING_TODAY - timedelta(days=31),
            balance_amount=Decimal("200.00"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_number="EXACT60",
            due_date=_AGING_TODAY - timedelta(days=60),
            balance_amount=Decimal("300.00"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_number="EXACT61",
            due_date=_AGING_TODAY - timedelta(days=61),
            balance_amount=Decimal("400.00"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_number="EXACT90",
            due_date=_AGING_TODAY - timedelta(days=90),
            balance_amount=Decimal("500.00"),
        )
        await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_number="EXACT91",
            due_date=_AGING_TODAY - timedelta(days=91),
            balance_amount=Decimal("600.00"),
        )

        rows, _summary, total = await repo.get_aging_report(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            outstanding_only=False,
            risk_level=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        row = rows[0]
        assert row.days_1_30 == Decimal("100.00")
        assert row.days_31_60 == Decimal("500.00")
        assert row.days_61_90 == Decimal("900.00")
        assert row.days_90_plus == Decimal("600.00")

    async def test_outstanding_only_filter(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        zero_co = await _make_company(db_session, tenant_id, name="Zero Co")
        await _make_invoice(
            db_session,
            tenant_id,
            zero_co.id,
            total_amount=Decimal("100.00"),
            paid_amount=Decimal("100.00"),
            balance_amount=Decimal("0"),
        )
        owing_co = await _make_company(db_session, tenant_id, name="Owing Co")
        await _make_invoice(db_session, tenant_id, owing_co.id, balance_amount=Decimal("200.00"))

        rows, _summary, total = await repo.get_aging_report(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            outstanding_only=True,
            risk_level=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].entity_name == "Owing Co"

    async def test_risk_level_filter(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        low = await _make_company(db_session, tenant_id, name="Low Co")
        await _make_invoice(
            db_session,
            tenant_id,
            low.id,
            due_date=_AGING_TODAY + timedelta(days=5),
            balance_amount=Decimal("100.00"),
        )
        high = await _make_company(db_session, tenant_id, name="High Co")
        await _make_invoice(
            db_session,
            tenant_id,
            high.id,
            due_date=_AGING_TODAY - timedelta(days=100),
            balance_amount=Decimal("200.00"),
        )

        rows, _summary, total = await repo.get_aging_report(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            outstanding_only=False,
            risk_level=RiskLevel.HIGH,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].entity_name == "High Co"

    async def test_q_filter(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company = await _make_company(db_session, tenant_id, name="Konkan Seafoods")
        other = await _make_company(db_session, tenant_id, name="Malabar Traders")
        await _make_invoice(db_session, tenant_id, company.id, balance_amount=Decimal("100.00"))
        await _make_invoice(db_session, tenant_id, other.id, balance_amount=Decimal("100.00"))

        rows, _summary, total = await repo.get_aging_report(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            outstanding_only=False,
            risk_level=None,
            q="Konkan",
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].entity_name == "Konkan Seafoods"

    async def test_excludes_draft_and_cancelled(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(db_session, tenant_id, company_id, status=InvoiceStatus.DRAFT)
        await _make_invoice(db_session, tenant_id, company_id, status=InvoiceStatus.CANCELLED)

        rows, _summary, total = await repo.get_aging_report(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            outstanding_only=False,
            risk_level=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 0

    async def test_scoped_to_one_tenant(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(name="Other Aging Tenant", slug=f"other-aging-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_company = await _make_company(db_session, other_tenant.id)
        await _make_invoice(db_session, other_tenant.id, other_company.id)

        rows, _summary, total = await repo.get_aging_report(
            tenant_id,
            entity_type=EntityType.CUSTOMER,
            today=_AGING_TODAY,
            outstanding_only=False,
            risk_level=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 0


class TestGetAgingReportSupplier:
    """A lighter smoke-test mirroring TestGetAgingReportCustomer - the
    underlying query shape is identical (_finalize_aging_rows is fully
    shared)."""

    async def test_bucket_allocation(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier_id,
            bill_number="B1",
            due_date=_AGING_TODAY - timedelta(days=15),
            balance_amount=Decimal("200.00"),
        )
        await _make_purchase_bill(
            db_session,
            tenant_id,
            supplier_id,
            bill_number="B2",
            due_date=_AGING_TODAY + timedelta(days=10),
            balance_amount=Decimal("100.00"),
        )

        rows, _summary, total = await repo.get_aging_report(
            tenant_id,
            entity_type=EntityType.SUPPLIER,
            today=_AGING_TODAY,
            outstanding_only=False,
            risk_level=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        row = rows[0]
        assert row.days_1_30 == Decimal("200.00")
        assert row.current_amount == Decimal("100.00")
        assert row.total == Decimal("300.00")

    async def test_scoped_to_one_tenant(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Aging Supplier Tenant",
            slug=f"other-aging-supplier-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_supplier = await _make_supplier(db_session, other_tenant.id)
        await _make_purchase_bill(db_session, other_tenant.id, other_supplier.id)

        rows, _summary, total = await repo.get_aging_report(
            tenant_id,
            entity_type=EntityType.SUPPLIER,
            today=_AGING_TODAY,
            outstanding_only=False,
            risk_level=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 0


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
    invoice_status: InvoiceStatus = InvoiceStatus.ISSUED,
) -> None:
    """One trip catch, one invoice, one invoice item linking them - the
    minimal chain that produces `line_total` of revenue for `trip_id`."""
    catch = await _make_trip_catch(db_session, tenant_id, trip_id, fish_id)
    invoice = await _make_invoice(db_session, tenant_id, company_id, status=invoice_status)
    await _make_trip_invoice_item(
        db_session, tenant_id, invoice.id, fish_id, catch.id, line_total=line_total
    )


@pytest.fixture
async def fish_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    fish = await _make_fish(db_session, tenant_id)
    return fish.id


class TestGetTripProfitability:
    async def test_revenue_and_expense_aggregation(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        boat = await _make_boat(db_session, tenant_id)
        trip = await _make_trip(db_session, tenant_id, boat.id)
        await _seed_trip_revenue(
            db_session, tenant_id, company_id, trip.id, fish_id, line_total=Decimal("10000.00")
        )
        await _seed_trip_revenue(
            db_session, tenant_id, company_id, trip.id, fish_id, line_total=Decimal("5000.00")
        )
        await _make_trip_expense(db_session, tenant_id, trip.id, amount=Decimal("2000.00"))
        await _make_trip_expense(db_session, tenant_id, trip.id, amount=Decimal("1000.00"))

        rows, _summary, total = await repo.get_trip_profitability(
            tenant_id,
            boat_id=None,
            from_date=None,
            to_date=None,
            profitability=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        row = rows[0]
        assert row.revenue == Decimal("15000.00")
        assert row.expenses == Decimal("3000.00")
        assert row.profit == Decimal("12000.00")

    async def test_excludes_draft_and_cancelled_invoice_revenue(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        boat = await _make_boat(db_session, tenant_id)
        trip = await _make_trip(db_session, tenant_id, boat.id)
        await _seed_trip_revenue(
            db_session,
            tenant_id,
            company_id,
            trip.id,
            fish_id,
            line_total=Decimal("10000.00"),
            invoice_status=InvoiceStatus.DRAFT,
        )
        await _seed_trip_revenue(
            db_session,
            tenant_id,
            company_id,
            trip.id,
            fish_id,
            line_total=Decimal("5000.00"),
            invoice_status=InvoiceStatus.CANCELLED,
        )
        await _seed_trip_revenue(
            db_session,
            tenant_id,
            company_id,
            trip.id,
            fish_id,
            line_total=Decimal("7000.00"),
            invoice_status=InvoiceStatus.ISSUED,
        )

        rows, _summary, _total = await repo.get_trip_profitability(
            tenant_id,
            boat_id=None,
            from_date=None,
            to_date=None,
            profitability=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert rows[0].revenue == Decimal("7000.00")

    async def test_only_returned_trips_are_included(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        # PLANNED/DEPARTED are each "the boat's one active trip"
        # (ix_trips_boat_single_active) - each needs its own boat.
        boat = await _make_boat(db_session, tenant_id)
        planned_boat = await _make_boat(db_session, tenant_id)
        departed_boat = await _make_boat(db_session, tenant_id)
        await _make_trip(db_session, tenant_id, planned_boat.id, status=TripStatus.PLANNED)
        await _make_trip(db_session, tenant_id, departed_boat.id, status=TripStatus.DEPARTED)
        await _make_trip(db_session, tenant_id, boat.id, status=TripStatus.CANCELLED)
        returned = await _make_trip(db_session, tenant_id, boat.id, status=TripStatus.RETURNED)

        rows, _summary, total = await repo.get_trip_profitability(
            tenant_id,
            boat_id=None,
            from_date=None,
            to_date=None,
            profitability=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].trip_id == returned.id

    async def test_boat_id_filter(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        boat_a = await _make_boat(db_session, tenant_id)
        boat_b = await _make_boat(db_session, tenant_id)
        await _make_trip(db_session, tenant_id, boat_a.id, trip_number="TRIP-A")
        await _make_trip(db_session, tenant_id, boat_b.id, trip_number="TRIP-B")

        rows, _summary, total = await repo.get_trip_profitability(
            tenant_id,
            boat_id=boat_a.id,
            from_date=None,
            to_date=None,
            profitability=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].trip_number == "TRIP-A"

    async def test_date_range_filters_by_return_date(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        boat = await _make_boat(db_session, tenant_id)
        await _make_trip(
            db_session,
            tenant_id,
            boat.id,
            trip_number="TRIP-EARLY",
            actual_return_datetime=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
        )
        in_range = await _make_trip(
            db_session,
            tenant_id,
            boat.id,
            trip_number="TRIP-IN-RANGE",
            actual_return_datetime=datetime(2026, 7, 5, 12, 0, tzinfo=UTC),
        )

        rows, _summary, total = await repo.get_trip_profitability(
            tenant_id,
            boat_id=None,
            from_date=date(2026, 7, 1),
            to_date=date(2026, 7, 31),
            profitability=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].trip_id == in_range.id

    async def test_profitability_filter(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        boat = await _make_boat(db_session, tenant_id)
        profitable_trip = await _make_trip(
            db_session, tenant_id, boat.id, trip_number="TRIP-PROFIT"
        )
        await _seed_trip_revenue(
            db_session,
            tenant_id,
            company_id,
            profitable_trip.id,
            fish_id,
            line_total=Decimal("10000.00"),
        )
        await _make_trip_expense(
            db_session, tenant_id, profitable_trip.id, amount=Decimal("1000.00")
        )

        loss_trip = await _make_trip(db_session, tenant_id, boat.id, trip_number="TRIP-LOSS")
        await _make_trip_expense(db_session, tenant_id, loss_trip.id, amount=Decimal("500.00"))

        profitable_rows, _summary, _total = await repo.get_trip_profitability(
            tenant_id,
            boat_id=None,
            from_date=None,
            to_date=None,
            profitability=ProfitabilityFilter.PROFITABLE,
            q=None,
            page=1,
            page_size=10,
        )
        assert [row.trip_id for row in profitable_rows] == [profitable_trip.id]

        loss_rows, _summary, _total = await repo.get_trip_profitability(
            tenant_id,
            boat_id=None,
            from_date=None,
            to_date=None,
            profitability=ProfitabilityFilter.LOSS,
            q=None,
            page=1,
            page_size=10,
        )
        assert [row.trip_id for row in loss_rows] == [loss_trip.id]

    async def test_search_matches_trip_number_or_boat_name(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        boat = await _make_boat(db_session, tenant_id, name="Sagar Kanya")
        target = await _make_trip(db_session, tenant_id, boat.id, trip_number="TRIP-XYZ-001")
        await _make_trip(db_session, tenant_id, boat.id, trip_number="TRIP-OTHER-002")

        rows, _summary, total = await repo.get_trip_profitability(
            tenant_id,
            boat_id=None,
            from_date=None,
            to_date=None,
            profitability=None,
            q="XYZ",
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].trip_id == target.id

        by_boat_name, _summary, total = await repo.get_trip_profitability(
            tenant_id,
            boat_id=None,
            from_date=None,
            to_date=None,
            profitability=None,
            q="Sagar",
            page=1,
            page_size=10,
        )
        assert total == 2

    async def test_summary_totals_and_most_profitable_trip(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        boat = await _make_boat(db_session, tenant_id)
        big = await _make_trip(db_session, tenant_id, boat.id, trip_number="TRIP-BIG")
        await _seed_trip_revenue(
            db_session, tenant_id, company_id, big.id, fish_id, line_total=Decimal("20000.00")
        )
        await _make_trip_expense(db_session, tenant_id, big.id, amount=Decimal("5000.00"))

        small = await _make_trip(db_session, tenant_id, boat.id, trip_number="TRIP-SMALL")
        await _make_trip_expense(db_session, tenant_id, small.id, amount=Decimal("500.00"))

        _rows, summary, _total = await repo.get_trip_profitability(
            tenant_id,
            boat_id=None,
            from_date=None,
            to_date=None,
            profitability=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert summary.total_revenue == Decimal("20000.00")
        assert summary.total_expenses == Decimal("5500.00")
        assert summary.total_profit == Decimal("14500.00")
        assert summary.most_profitable_trip_number == "TRIP-BIG"
        assert summary.most_profitable_trip_profit == Decimal("15000.00")
        assert summary.loss_making_trips == 1

    async def test_ordering_is_return_date_desc_then_trip_number_desc(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        boat = await _make_boat(db_session, tenant_id)
        older = await _make_trip(
            db_session,
            tenant_id,
            boat.id,
            trip_number="TRIP-001",
            actual_return_datetime=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        )
        newer = await _make_trip(
            db_session,
            tenant_id,
            boat.id,
            trip_number="TRIP-002",
            actual_return_datetime=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )

        rows, _summary, _total = await repo.get_trip_profitability(
            tenant_id,
            boat_id=None,
            from_date=None,
            to_date=None,
            profitability=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert [row.trip_id for row in rows] == [newer.id, older.id]

    async def test_scoped_to_one_tenant(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Trip Profitability Tenant",
            slug=f"other-trip-profit-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_boat = await _make_boat(db_session, other_tenant.id)
        await _make_trip(db_session, other_tenant.id, other_boat.id)

        _rows, _summary, total = await repo.get_trip_profitability(
            tenant_id,
            boat_id=None,
            from_date=None,
            to_date=None,
            profitability=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 0

    async def test_pagination(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        boat = await _make_boat(db_session, tenant_id)
        for i in range(3):
            await _make_trip(
                db_session,
                tenant_id,
                boat.id,
                actual_return_datetime=datetime(2026, 7, 1 + i, 12, 0, tzinfo=UTC),
            )

        rows, _summary, total = await repo.get_trip_profitability(
            tenant_id,
            boat_id=None,
            from_date=None,
            to_date=None,
            profitability=None,
            q=None,
            page=1,
            page_size=2,
        )
        assert total == 3
        assert len(rows) == 2


class TestGetBoatProfitability:
    async def test_aggregates_across_every_completed_trip(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        boat = await _make_boat(db_session, tenant_id)
        trip1 = await _make_trip(
            db_session,
            tenant_id,
            boat.id,
            trip_number="TRIP-1",
            actual_return_datetime=datetime(2026, 7, 5, 12, 0, tzinfo=UTC),
        )
        await _seed_trip_revenue(
            db_session, tenant_id, company_id, trip1.id, fish_id, line_total=Decimal("10000.00")
        )
        await _make_trip_expense(db_session, tenant_id, trip1.id, amount=Decimal("2000.00"))

        trip2 = await _make_trip(
            db_session,
            tenant_id,
            boat.id,
            trip_number="TRIP-2",
            actual_return_datetime=datetime(2026, 7, 12, 12, 0, tzinfo=UTC),
        )
        await _seed_trip_revenue(
            db_session, tenant_id, company_id, trip2.id, fish_id, line_total=Decimal("5000.00")
        )
        await _make_trip_expense(db_session, tenant_id, trip2.id, amount=Decimal("6000.00"))

        rows, _summary, total = await repo.get_boat_profitability(
            tenant_id,
            boat_id=None,
            from_date=None,
            to_date=None,
            min_trips=None,
            profitability=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        row = rows[0]
        assert row.total_trips == 2
        assert row.revenue == Decimal("15000.00")
        assert row.expenses == Decimal("8000.00")
        assert row.profit == Decimal("7000.00")
        assert row.best_trip_profit == Decimal("8000.00")
        assert row.worst_trip_profit == Decimal("-1000.00")
        assert row.last_trip_date == datetime(2026, 7, 12, 12, 0, tzinfo=UTC)

    async def test_boat_with_no_completed_trips_is_excluded(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        boat = await _make_boat(db_session, tenant_id)
        await _make_trip(db_session, tenant_id, boat.id, status=TripStatus.PLANNED)

        _rows, _summary, total = await repo.get_boat_profitability(
            tenant_id,
            boat_id=None,
            from_date=None,
            to_date=None,
            min_trips=None,
            profitability=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 0

    async def test_boat_id_filter(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        boat_a = await _make_boat(db_session, tenant_id, name="Boat A")
        boat_b = await _make_boat(db_session, tenant_id, name="Boat B")
        await _make_trip(db_session, tenant_id, boat_a.id)
        await _make_trip(db_session, tenant_id, boat_b.id)

        rows, _summary, total = await repo.get_boat_profitability(
            tenant_id,
            boat_id=boat_a.id,
            from_date=None,
            to_date=None,
            min_trips=None,
            profitability=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].boat_id == boat_a.id

    async def test_min_trips_filter(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        boat_a = await _make_boat(db_session, tenant_id)
        await _make_trip(db_session, tenant_id, boat_a.id)

        boat_b = await _make_boat(db_session, tenant_id)
        await _make_trip(db_session, tenant_id, boat_b.id)
        await _make_trip(db_session, tenant_id, boat_b.id)

        rows, _summary, total = await repo.get_boat_profitability(
            tenant_id,
            boat_id=None,
            from_date=None,
            to_date=None,
            min_trips=2,
            profitability=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].boat_id == boat_b.id

    async def test_summary_fleet_totals_and_active_boats(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        active_boat = await _make_boat(db_session, tenant_id, is_active=True)
        await _make_trip(db_session, tenant_id, active_boat.id)

        inactive_boat = await _make_boat(db_session, tenant_id, is_active=False)
        await _make_trip(db_session, tenant_id, inactive_boat.id)

        _rows, summary, _total = await repo.get_boat_profitability(
            tenant_id,
            boat_id=None,
            from_date=None,
            to_date=None,
            min_trips=None,
            profitability=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert summary.total_boats == 2
        assert summary.active_boats == 1

    async def test_most_profitable_boat(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        strong_boat = await _make_boat(db_session, tenant_id, name="Strong Boat")
        strong_trip = await _make_trip(db_session, tenant_id, strong_boat.id)
        await _seed_trip_revenue(
            db_session,
            tenant_id,
            company_id,
            strong_trip.id,
            fish_id,
            line_total=Decimal("20000.00"),
        )

        weak_boat = await _make_boat(db_session, tenant_id, name="Weak Boat")
        weak_trip = await _make_trip(db_session, tenant_id, weak_boat.id)
        await _make_trip_expense(db_session, tenant_id, weak_trip.id, amount=Decimal("500.00"))

        _rows, summary, _total = await repo.get_boat_profitability(
            tenant_id,
            boat_id=None,
            from_date=None,
            to_date=None,
            min_trips=None,
            profitability=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert summary.most_profitable_boat_name == "Strong Boat"
        assert summary.most_profitable_boat_profit == Decimal("20000.00")

    async def test_ordering_is_profit_desc_then_boat_name_asc(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
    ) -> None:
        low_boat = await _make_boat(db_session, tenant_id, name="Low Profit Boat")
        low_trip = await _make_trip(db_session, tenant_id, low_boat.id)
        await _make_trip_expense(db_session, tenant_id, low_trip.id, amount=Decimal("100.00"))

        high_boat = await _make_boat(db_session, tenant_id, name="High Profit Boat")
        high_trip = await _make_trip(db_session, tenant_id, high_boat.id)
        await _seed_trip_revenue(
            db_session, tenant_id, company_id, high_trip.id, fish_id, line_total=Decimal("50000.00")
        )

        rows, _summary, _total = await repo.get_boat_profitability(
            tenant_id,
            boat_id=None,
            from_date=None,
            to_date=None,
            min_trips=None,
            profitability=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert [row.boat_id for row in rows] == [high_boat.id, low_boat.id]

    async def test_scoped_to_one_tenant(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Boat Profitability Tenant",
            slug=f"other-boat-profit-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_boat = await _make_boat(db_session, other_tenant.id)
        await _make_trip(db_session, other_tenant.id, other_boat.id)

        _rows, _summary, total = await repo.get_boat_profitability(
            tenant_id,
            boat_id=None,
            from_date=None,
            to_date=None,
            min_trips=None,
            profitability=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 0


# -- Fish Sales Analytics (TASKS.md Sprint 11 Session 4 Phase B) ---------


async def _make_plain_invoice_item(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
    fish_id: uuid.UUID,
    **overrides: Any,
) -> InvoiceItem:
    """An invoice item with no trip_catch_id - purchased/untracked stock
    (ARCHITECTURE.md's own description of this nullable column) - still
    counts toward revenue/quantity, contributes nothing to trip_count."""
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


class TestGetFishSales:
    async def test_revenue_and_quantity_aggregation(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        fish = await _make_fish(db_session, tenant_id, name="Pomfret")
        invoice1 = await _make_invoice(db_session, tenant_id, company_id)
        invoice2 = await _make_invoice(db_session, tenant_id, company_id)
        await _make_plain_invoice_item(
            db_session,
            tenant_id,
            invoice1.id,
            fish.id,
            quantity=Decimal("100.000"),
            line_total=Decimal("10000.00"),
        )
        await _make_plain_invoice_item(
            db_session,
            tenant_id,
            invoice2.id,
            fish.id,
            quantity=Decimal("50.000"),
            line_total=Decimal("6000.00"),
        )

        rows, _summary, total = await repo.get_fish_sales(
            tenant_id,
            fish_id=None,
            customer_id=None,
            boat_id=None,
            trip_id=None,
            from_date=None,
            to_date=None,
            min_quantity=None,
            min_revenue=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        row = rows[0]
        assert row.fish_id == fish.id
        assert row.quantity_sold == Decimal("150.000")
        assert row.revenue == Decimal("16000.00")
        assert row.invoice_count == 2

    async def test_excludes_draft_and_cancelled_invoices(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        fish = await _make_fish(db_session, tenant_id)
        draft_invoice = await _make_invoice(
            db_session, tenant_id, company_id, status=InvoiceStatus.DRAFT
        )
        cancelled_invoice = await _make_invoice(
            db_session, tenant_id, company_id, status=InvoiceStatus.CANCELLED
        )
        real_invoice = await _make_invoice(
            db_session, tenant_id, company_id, status=InvoiceStatus.ISSUED
        )
        await _make_plain_invoice_item(
            db_session, tenant_id, draft_invoice.id, fish.id, line_total=Decimal("9999.00")
        )
        await _make_plain_invoice_item(
            db_session, tenant_id, cancelled_invoice.id, fish.id, line_total=Decimal("9999.00")
        )
        await _make_plain_invoice_item(
            db_session, tenant_id, real_invoice.id, fish.id, line_total=Decimal("1000.00")
        )

        rows, _summary, _total = await repo.get_fish_sales(
            tenant_id,
            fish_id=None,
            customer_id=None,
            boat_id=None,
            trip_id=None,
            from_date=None,
            to_date=None,
            min_quantity=None,
            min_revenue=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert rows[0].revenue == Decimal("1000.00")

    async def test_invoice_count_counts_distinct_invoices_not_lines(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        fish = await _make_fish(db_session, tenant_id)
        invoice = await _make_invoice(db_session, tenant_id, company_id)
        await _make_plain_invoice_item(db_session, tenant_id, invoice.id, fish.id, line_number=1)
        await _make_plain_invoice_item(db_session, tenant_id, invoice.id, fish.id, line_number=2)

        rows, _summary, _total = await repo.get_fish_sales(
            tenant_id,
            fish_id=None,
            customer_id=None,
            boat_id=None,
            trip_id=None,
            from_date=None,
            to_date=None,
            min_quantity=None,
            min_revenue=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert rows[0].invoice_count == 1

    async def test_trip_count_via_trip_catch_and_untracked_lines_still_count_revenue(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        fish = await _make_fish(db_session, tenant_id)
        boat = await _make_boat(db_session, tenant_id)
        trip_a = await _make_trip(db_session, tenant_id, boat.id)
        trip_b = await _make_trip(db_session, tenant_id, boat.id)
        catch_a = await _make_trip_catch(db_session, tenant_id, trip_a.id, fish.id)
        catch_b = await _make_trip_catch(db_session, tenant_id, trip_b.id, fish.id)

        invoice = await _make_invoice(db_session, tenant_id, company_id)
        await _make_trip_invoice_item(
            db_session, tenant_id, invoice.id, fish.id, catch_a.id, line_number=1
        )
        await _make_trip_invoice_item(
            db_session, tenant_id, invoice.id, fish.id, catch_b.id, line_number=2
        )
        # Untracked stock - no trip_catch_id - still counts toward revenue/quantity.
        await _make_plain_invoice_item(
            db_session, tenant_id, invoice.id, fish.id, line_number=3, line_total=Decimal("500.00")
        )

        rows, _summary, _total = await repo.get_fish_sales(
            tenant_id,
            fish_id=None,
            customer_id=None,
            boat_id=None,
            trip_id=None,
            from_date=None,
            to_date=None,
            min_quantity=None,
            min_revenue=None,
            q=None,
            page=1,
            page_size=10,
        )
        row = rows[0]
        assert row.trip_count == 2
        assert row.revenue == Decimal("20500.00")

    async def test_customer_count_counts_distinct_customers(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        fish = await _make_fish(db_session, tenant_id)
        company_a = await _make_company(db_session, tenant_id)
        company_b = await _make_company(db_session, tenant_id)
        invoice_a = await _make_invoice(db_session, tenant_id, company_a.id)
        invoice_b = await _make_invoice(db_session, tenant_id, company_b.id)
        await _make_plain_invoice_item(db_session, tenant_id, invoice_a.id, fish.id)
        await _make_plain_invoice_item(db_session, tenant_id, invoice_b.id, fish.id)

        rows, _summary, _total = await repo.get_fish_sales(
            tenant_id,
            fish_id=None,
            customer_id=None,
            boat_id=None,
            trip_id=None,
            from_date=None,
            to_date=None,
            min_quantity=None,
            min_revenue=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert rows[0].customer_count == 2

    async def test_fish_id_filter(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        fish_a = await _make_fish(db_session, tenant_id, name="Fish A")
        fish_b = await _make_fish(db_session, tenant_id, name="Fish B")
        invoice = await _make_invoice(db_session, tenant_id, company_id)
        await _make_plain_invoice_item(db_session, tenant_id, invoice.id, fish_a.id)
        await _make_plain_invoice_item(db_session, tenant_id, invoice.id, fish_b.id, line_number=2)

        rows, _summary, total = await repo.get_fish_sales(
            tenant_id,
            fish_id=fish_a.id,
            customer_id=None,
            boat_id=None,
            trip_id=None,
            from_date=None,
            to_date=None,
            min_quantity=None,
            min_revenue=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 1
        assert rows[0].fish_id == fish_a.id

    async def test_customer_id_filter(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        fish = await _make_fish(db_session, tenant_id)
        company_a = await _make_company(db_session, tenant_id)
        company_b = await _make_company(db_session, tenant_id)
        invoice_a = await _make_invoice(db_session, tenant_id, company_a.id)
        invoice_b = await _make_invoice(db_session, tenant_id, company_b.id)
        await _make_plain_invoice_item(
            db_session, tenant_id, invoice_a.id, fish.id, line_total=Decimal("100.00")
        )
        await _make_plain_invoice_item(
            db_session, tenant_id, invoice_b.id, fish.id, line_total=Decimal("200.00")
        )

        rows, _summary, _total = await repo.get_fish_sales(
            tenant_id,
            fish_id=None,
            customer_id=company_a.id,
            boat_id=None,
            trip_id=None,
            from_date=None,
            to_date=None,
            min_quantity=None,
            min_revenue=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert rows[0].revenue == Decimal("100.00")

    async def test_boat_id_filter(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        fish = await _make_fish(db_session, tenant_id)
        boat_a = await _make_boat(db_session, tenant_id)
        boat_b = await _make_boat(db_session, tenant_id)
        trip_a = await _make_trip(db_session, tenant_id, boat_a.id)
        trip_b = await _make_trip(db_session, tenant_id, boat_b.id)
        catch_a = await _make_trip_catch(db_session, tenant_id, trip_a.id, fish.id)
        catch_b = await _make_trip_catch(db_session, tenant_id, trip_b.id, fish.id)
        invoice = await _make_invoice(db_session, tenant_id, company_id)
        await _make_trip_invoice_item(
            db_session,
            tenant_id,
            invoice.id,
            fish.id,
            catch_a.id,
            line_number=1,
            line_total=Decimal("111.00"),
        )
        await _make_trip_invoice_item(
            db_session,
            tenant_id,
            invoice.id,
            fish.id,
            catch_b.id,
            line_number=2,
            line_total=Decimal("222.00"),
        )

        rows, _summary, _total = await repo.get_fish_sales(
            tenant_id,
            fish_id=None,
            customer_id=None,
            boat_id=boat_a.id,
            trip_id=None,
            from_date=None,
            to_date=None,
            min_quantity=None,
            min_revenue=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert rows[0].revenue == Decimal("111.00")

    async def test_trip_id_filter(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        fish = await _make_fish(db_session, tenant_id)
        boat = await _make_boat(db_session, tenant_id)
        trip_a = await _make_trip(db_session, tenant_id, boat.id)
        trip_b = await _make_trip(db_session, tenant_id, boat.id)
        catch_a = await _make_trip_catch(db_session, tenant_id, trip_a.id, fish.id)
        catch_b = await _make_trip_catch(db_session, tenant_id, trip_b.id, fish.id)
        invoice = await _make_invoice(db_session, tenant_id, company_id)
        await _make_trip_invoice_item(
            db_session,
            tenant_id,
            invoice.id,
            fish.id,
            catch_a.id,
            line_number=1,
            line_total=Decimal("333.00"),
        )
        await _make_trip_invoice_item(
            db_session,
            tenant_id,
            invoice.id,
            fish.id,
            catch_b.id,
            line_number=2,
            line_total=Decimal("444.00"),
        )

        rows, _summary, _total = await repo.get_fish_sales(
            tenant_id,
            fish_id=None,
            customer_id=None,
            boat_id=None,
            trip_id=trip_a.id,
            from_date=None,
            to_date=None,
            min_quantity=None,
            min_revenue=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert rows[0].revenue == Decimal("333.00")

    async def test_date_range_filters_by_invoice_date(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        fish = await _make_fish(db_session, tenant_id)
        early_invoice = await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=date(2026, 6, 1)
        )
        in_range_invoice = await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=date(2026, 7, 10)
        )
        await _make_plain_invoice_item(
            db_session, tenant_id, early_invoice.id, fish.id, line_total=Decimal("999.00")
        )
        await _make_plain_invoice_item(
            db_session, tenant_id, in_range_invoice.id, fish.id, line_total=Decimal("555.00")
        )

        rows, _summary, _total = await repo.get_fish_sales(
            tenant_id,
            fish_id=None,
            customer_id=None,
            boat_id=None,
            trip_id=None,
            from_date=date(2026, 7, 1),
            to_date=date(2026, 7, 31),
            min_quantity=None,
            min_revenue=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert rows[0].revenue == Decimal("555.00")

    async def test_min_quantity_and_min_revenue_filters(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        small_fish = await _make_fish(db_session, tenant_id, name="Small Fish")
        big_fish = await _make_fish(db_session, tenant_id, name="Big Fish")
        invoice = await _make_invoice(db_session, tenant_id, company_id)
        await _make_plain_invoice_item(
            db_session,
            tenant_id,
            invoice.id,
            small_fish.id,
            line_number=1,
            quantity=Decimal("5.000"),
            line_total=Decimal("50.00"),
        )
        await _make_plain_invoice_item(
            db_session,
            tenant_id,
            invoice.id,
            big_fish.id,
            line_number=2,
            quantity=Decimal("500.000"),
            line_total=Decimal("50000.00"),
        )

        by_quantity, _summary, _total = await repo.get_fish_sales(
            tenant_id,
            fish_id=None,
            customer_id=None,
            boat_id=None,
            trip_id=None,
            from_date=None,
            to_date=None,
            min_quantity=Decimal("100"),
            min_revenue=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert [row.fish_id for row in by_quantity] == [big_fish.id]

        by_revenue, _summary, _total = await repo.get_fish_sales(
            tenant_id,
            fish_id=None,
            customer_id=None,
            boat_id=None,
            trip_id=None,
            from_date=None,
            to_date=None,
            min_quantity=None,
            min_revenue=Decimal("1000"),
            q=None,
            page=1,
            page_size=10,
        )
        assert [row.fish_id for row in by_revenue] == [big_fish.id]

    async def test_search_matches_fish_name_code_or_scientific_name(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        target = await _make_fish(
            db_session, tenant_id, name="Pomfret", scientific_name="Pampus argenteus"
        )
        other = await _make_fish(db_session, tenant_id, name="Mackerel")
        invoice = await _make_invoice(db_session, tenant_id, company_id)
        await _make_plain_invoice_item(db_session, tenant_id, invoice.id, target.id, line_number=1)
        await _make_plain_invoice_item(db_session, tenant_id, invoice.id, other.id, line_number=2)

        by_name, _summary, total = await repo.get_fish_sales(
            tenant_id,
            fish_id=None,
            customer_id=None,
            boat_id=None,
            trip_id=None,
            from_date=None,
            to_date=None,
            min_quantity=None,
            min_revenue=None,
            q="Pomfret",
            page=1,
            page_size=10,
        )
        assert total == 1
        assert by_name[0].fish_id == target.id

        by_scientific_name, _summary, total = await repo.get_fish_sales(
            tenant_id,
            fish_id=None,
            customer_id=None,
            boat_id=None,
            trip_id=None,
            from_date=None,
            to_date=None,
            min_quantity=None,
            min_revenue=None,
            q="argenteus",
            page=1,
            page_size=10,
        )
        assert total == 1
        assert by_scientific_name[0].fish_id == target.id

    async def test_summary_totals_best_selling_and_highest_revenue_fish(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        high_volume_fish = await _make_fish(db_session, tenant_id, name="High Volume Fish")
        high_revenue_fish = await _make_fish(db_session, tenant_id, name="High Revenue Fish")
        invoice = await _make_invoice(db_session, tenant_id, company_id)
        await _make_plain_invoice_item(
            db_session,
            tenant_id,
            invoice.id,
            high_volume_fish.id,
            line_number=1,
            quantity=Decimal("1000.000"),
            line_total=Decimal("2000.00"),
        )
        await _make_plain_invoice_item(
            db_session,
            tenant_id,
            invoice.id,
            high_revenue_fish.id,
            line_number=2,
            quantity=Decimal("10.000"),
            line_total=Decimal("50000.00"),
        )

        _rows, summary, _total = await repo.get_fish_sales(
            tenant_id,
            fish_id=None,
            customer_id=None,
            boat_id=None,
            trip_id=None,
            from_date=None,
            to_date=None,
            min_quantity=None,
            min_revenue=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert summary.total_fish_sold == Decimal("1010.000")
        assert summary.total_revenue == Decimal("52000.00")
        assert summary.best_selling_fish_name == "High Volume Fish"
        assert summary.best_selling_fish_quantity == Decimal("1000.000")
        assert summary.highest_revenue_fish_name == "High Revenue Fish"
        assert summary.highest_revenue_fish_revenue == Decimal("50000.00")
        assert summary.total_fish_types_sold == 2

    async def test_ordering_is_revenue_desc_then_fish_name_asc(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        low = await _make_fish(db_session, tenant_id, name="A Low Revenue Fish")
        high = await _make_fish(db_session, tenant_id, name="Z High Revenue Fish")
        invoice = await _make_invoice(db_session, tenant_id, company_id)
        await _make_plain_invoice_item(
            db_session, tenant_id, invoice.id, low.id, line_number=1, line_total=Decimal("10.00")
        )
        await _make_plain_invoice_item(
            db_session, tenant_id, invoice.id, high.id, line_number=2, line_total=Decimal("999.00")
        )

        rows, _summary, _total = await repo.get_fish_sales(
            tenant_id,
            fish_id=None,
            customer_id=None,
            boat_id=None,
            trip_id=None,
            from_date=None,
            to_date=None,
            min_quantity=None,
            min_revenue=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert [row.fish_id for row in rows] == [high.id, low.id]

    async def test_last_sold_date_is_max_invoice_date(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        fish = await _make_fish(db_session, tenant_id)
        older_invoice = await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=date(2026, 6, 1)
        )
        newer_invoice = await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=date(2026, 7, 20)
        )
        await _make_plain_invoice_item(
            db_session, tenant_id, older_invoice.id, fish.id, line_number=1
        )
        await _make_plain_invoice_item(
            db_session, tenant_id, newer_invoice.id, fish.id, line_number=1
        )

        rows, _summary, _total = await repo.get_fish_sales(
            tenant_id,
            fish_id=None,
            customer_id=None,
            boat_id=None,
            trip_id=None,
            from_date=None,
            to_date=None,
            min_quantity=None,
            min_revenue=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert rows[0].last_sold_date == date(2026, 7, 20)

    async def test_pagination(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        invoice = await _make_invoice(db_session, tenant_id, company_id)
        for i in range(3):
            fish = await _make_fish(db_session, tenant_id, name=f"Pagination Fish {i}")
            await _make_plain_invoice_item(
                db_session,
                tenant_id,
                invoice.id,
                fish.id,
                line_number=i + 1,
                line_total=Decimal(f"{100 * (i + 1)}.00"),
            )

        rows, _summary, total = await repo.get_fish_sales(
            tenant_id,
            fish_id=None,
            customer_id=None,
            boat_id=None,
            trip_id=None,
            from_date=None,
            to_date=None,
            min_quantity=None,
            min_revenue=None,
            q=None,
            page=1,
            page_size=2,
        )
        assert total == 3
        assert len(rows) == 2

    async def test_scoped_to_one_tenant(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Fish Sales Tenant", slug=f"other-fish-sales-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_company = await _make_company(db_session, other_tenant.id)
        other_fish = await _make_fish(db_session, other_tenant.id)
        other_invoice = await _make_invoice(db_session, other_tenant.id, other_company.id)
        await _make_plain_invoice_item(db_session, other_tenant.id, other_invoice.id, other_fish.id)

        _rows, _summary, total = await repo.get_fish_sales(
            tenant_id,
            fish_id=None,
            customer_id=None,
            boat_id=None,
            trip_id=None,
            from_date=None,
            to_date=None,
            min_quantity=None,
            min_revenue=None,
            q=None,
            page=1,
            page_size=10,
        )
        assert total == 0


class TestGetFishSalesHistory:
    async def test_one_row_per_invoice_item(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        fish = await _make_fish(db_session, tenant_id, name="History Fish")
        invoice = await _make_invoice(
            db_session,
            tenant_id,
            company_id,
            invoice_number="INV-HIST-01",
            invoice_date=date(2026, 7, 10),
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
        await _make_plain_invoice_item(
            db_session,
            tenant_id,
            invoice.id,
            fish.id,
            line_number=2,
            quantity=Decimal("10.000"),
            rate=Decimal("260.0000"),
            line_total=Decimal("2600.00"),
        )

        rows, total = await repo.get_fish_sales_history(
            tenant_id, fish_id=fish.id, page=1, page_size=10
        )
        assert total == 2
        assert {row.quantity for row in rows} == {Decimal("20.000"), Decimal("10.000")}
        row = next(r for r in rows if r.quantity == Decimal("20.000"))
        assert row.invoice_number == "INV-HIST-01"
        assert row.unit_price == Decimal("250.0000")
        assert row.revenue == Decimal("5000.00")

    async def test_includes_customer_boat_and_trip_names(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        fish = await _make_fish(db_session, tenant_id)
        company = await _make_company(db_session, tenant_id, name="History Customer Co")
        boat = await _make_boat(db_session, tenant_id, name="History Boat")
        trip = await _make_trip(db_session, tenant_id, boat.id, trip_number="HIST-TRIP-01")
        catch = await _make_trip_catch(db_session, tenant_id, trip.id, fish.id)
        invoice = await _make_invoice(db_session, tenant_id, company.id)
        await _make_trip_invoice_item(db_session, tenant_id, invoice.id, fish.id, catch.id)

        rows, _total = await repo.get_fish_sales_history(
            tenant_id, fish_id=fish.id, page=1, page_size=10
        )
        assert rows[0].customer_name == "History Customer Co"
        assert rows[0].boat_name == "History Boat"
        assert rows[0].trip_number == "HIST-TRIP-01"

    async def test_untracked_stock_has_null_boat_and_trip(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        fish = await _make_fish(db_session, tenant_id)
        invoice = await _make_invoice(db_session, tenant_id, company_id)
        await _make_plain_invoice_item(db_session, tenant_id, invoice.id, fish.id)

        rows, _total = await repo.get_fish_sales_history(
            tenant_id, fish_id=fish.id, page=1, page_size=10
        )
        assert rows[0].boat_name is None
        assert rows[0].trip_number is None

    async def test_excludes_draft_and_cancelled_invoices(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        fish = await _make_fish(db_session, tenant_id)
        draft_invoice = await _make_invoice(
            db_session, tenant_id, company_id, status=InvoiceStatus.DRAFT
        )
        await _make_plain_invoice_item(db_session, tenant_id, draft_invoice.id, fish.id)

        _rows, total = await repo.get_fish_sales_history(
            tenant_id, fish_id=fish.id, page=1, page_size=10
        )
        assert total == 0

    async def test_scoped_to_the_requested_fish(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        target_fish = await _make_fish(db_session, tenant_id, name="Target Fish")
        other_fish = await _make_fish(db_session, tenant_id, name="Other Fish")
        invoice = await _make_invoice(db_session, tenant_id, company_id)
        await _make_plain_invoice_item(
            db_session, tenant_id, invoice.id, target_fish.id, line_number=1
        )
        await _make_plain_invoice_item(
            db_session, tenant_id, invoice.id, other_fish.id, line_number=2
        )

        rows, total = await repo.get_fish_sales_history(
            tenant_id, fish_id=target_fish.id, page=1, page_size=10
        )
        assert total == 1
        assert rows[0].quantity is not None

    async def test_ordering_is_invoice_date_desc(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        fish = await _make_fish(db_session, tenant_id)
        older_invoice = await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=date(2026, 6, 1)
        )
        newer_invoice = await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=date(2026, 7, 20)
        )
        await _make_plain_invoice_item(db_session, tenant_id, older_invoice.id, fish.id)
        await _make_plain_invoice_item(db_session, tenant_id, newer_invoice.id, fish.id)

        rows, _total = await repo.get_fish_sales_history(
            tenant_id, fish_id=fish.id, page=1, page_size=10
        )
        assert rows[0].invoice_date == date(2026, 7, 20)
        assert rows[1].invoice_date == date(2026, 6, 1)

    async def test_pagination(
        self,
        repo: ReportsRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        fish = await _make_fish(db_session, tenant_id)
        for i in range(3):
            invoice = await _make_invoice(
                db_session, tenant_id, company_id, invoice_date=date(2026, 7, 1 + i)
            )
            await _make_plain_invoice_item(db_session, tenant_id, invoice.id, fish.id)

        rows, total = await repo.get_fish_sales_history(
            tenant_id, fish_id=fish.id, page=1, page_size=2
        )
        assert total == 3
        assert len(rows) == 2

    async def test_scoped_to_one_tenant(
        self, repo: ReportsRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Fish Sales History Tenant", slug=f"other-fish-hist-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_company = await _make_company(db_session, other_tenant.id)
        other_fish = await _make_fish(db_session, other_tenant.id)
        other_invoice = await _make_invoice(db_session, other_tenant.id, other_company.id)
        await _make_plain_invoice_item(db_session, other_tenant.id, other_invoice.id, other_fish.id)

        _rows, total = await repo.get_fish_sales_history(
            tenant_id, fish_id=other_fish.id, page=1, page_size=10
        )
        assert total == 0
