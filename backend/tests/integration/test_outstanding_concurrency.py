"""Sprint 13 Session 3 - genuine PostgreSQL concurrency tests for the
outstanding-cache lost-update race (ARCHITECTURE.md §14.2/§14.3).

`Company.outstanding_amount`/`Supplier.outstanding_amount` are denormalized
caches recomputed via a SUM-then-SET pattern
(InvoiceService.recalculate_payment_totals -> CompanyService.
recalculate_outstanding, and the mirrored PurchaseService ->
SupplierService chain): each caller independently sums its party's open
document balances, then blindly overwrites outstanding_amount with that
sum. Two concurrent recomputes for the *same* party (each triggered by a
different document - e.g. two payments allocated to two different invoices
of the same company at the same time) can each compute their own SUM
before either commits, then whichever's blind SET commits last wins,
silently discarding the other's contribution. This file proves that race
(pre-fix, the final cached value diverges from the authoritative SUM) and
then serves as the permanent regression suite (post-fix, the party row is
locked FOR UPDATE - after the existing Payment/SupplierPayment -> Invoice/
PurchaseBill locks, per the deterministic lock order this session
establishes - before the SUM is read, so the second recompute always
re-reads post-commit state instead of a stale snapshot).

Mirrors test_allocation_concurrency.py's approach exactly: real sessions
from `app.db.session.async_session_factory` (not the rollback-only
`db_session` fixture - see that file's module docstring for why), real
committed rows, `asyncio.Barrier` to force simultaneous entry.
"""

import asyncio
import uuid
from datetime import date
from decimal import Decimal
from typing import NamedTuple

from sqlalchemy import delete

from app.db.session import async_session_factory
from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.companies.constants import CompanyStatus, CompanyType
from app.modules.companies.models import Company
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.models import Invoice
from app.modules.payments.constants import PaymentMethod
from app.modules.payments.constants import PaymentStatus as CustomerPaymentStatus
from app.modules.payments.models import Payment, PaymentAllocation
from app.modules.payments.schemas import PaymentAllocationCreateRequest
from app.modules.payments.service import PaymentService
from app.modules.purchase.constants import PurchaseStatus
from app.modules.purchase.models import PurchaseBill
from app.modules.supplier_payments.constants import PaymentMethod as SupplierPaymentMethod
from app.modules.supplier_payments.constants import SupplierPaymentStatus
from app.modules.supplier_payments.models import SupplierPayment, SupplierPaymentAllocation
from app.modules.supplier_payments.schemas import SupplierPaymentAllocationCreateRequest
from app.modules.supplier_payments.service import SupplierPaymentService
from app.modules.suppliers.constants import SupplierStatus
from app.modules.suppliers.models import Supplier

_BILL_DATE = date(2026, 8, 1)


class _CustomerScenario(NamedTuple):
    tenant_id: uuid.UUID
    actor_id: uuid.UUID
    company_id: uuid.UUID
    invoice_a_id: uuid.UUID
    invoice_b_id: uuid.UUID
    payment_a_id: uuid.UUID
    payment_b_id: uuid.UUID


class _SupplierScenario(NamedTuple):
    tenant_id: uuid.UUID
    actor_id: uuid.UUID
    supplier_id: uuid.UUID
    bill_a_id: uuid.UUID
    bill_b_id: uuid.UUID
    payment_a_id: uuid.UUID
    payment_b_id: uuid.UUID


async def _setup_customer_scenario() -> _CustomerScenario:
    """A company with two open invoices - A=10,000, B=5,000 - whose
    outstanding_amount is already correctly 15,000 (as InvoiceService.issue's
    atomic increase_outstanding would have left it), plus one DRAFT payment
    per invoice (4,000 against A, 2,000 against B) ready to allocate."""
    async with async_session_factory() as session:
        tenant = Tenant(name="Outstanding Race Co", slug=f"outrace-{uuid.uuid4().hex[:8]}")
        session.add(tenant)
        await session.flush()

        user = User(
            tenant_id=tenant.id,
            email=f"racer-{uuid.uuid4().hex[:8]}@fisherp.local",
            username=f"racer-{uuid.uuid4().hex[:8]}",
            password_hash="not-a-real-hash",
            full_name="Outstanding Race Tester",
            status=AccountStatus.ACTIVE,
        )
        session.add(user)
        await session.flush()

        company = Company(
            tenant_id=tenant.id,
            code=f"ORACE-{uuid.uuid4().hex[:8]}",
            name=f"Outstanding Race Customer {uuid.uuid4().hex[:8]}",
            company_type=CompanyType.CUSTOMER,
            status=CompanyStatus.ACTIVE,
            outstanding_amount=Decimal("15000.00"),
            created_by=user.id,
            updated_by=user.id,
        )
        session.add(company)
        await session.flush()

        invoice_a = Invoice(
            tenant_id=tenant.id,
            company_id=company.id,
            invoice_number=f"INV-ORACE-{uuid.uuid4().hex[:8]}",
            invoice_date=_BILL_DATE,
            status=InvoiceStatus.ISSUED,
            total_amount=Decimal("10000.00"),
            paid_amount=Decimal("0"),
            balance_amount=Decimal("10000.00"),
            created_by=user.id,
            updated_by=user.id,
        )
        invoice_b = Invoice(
            tenant_id=tenant.id,
            company_id=company.id,
            invoice_number=f"INV-ORACE-{uuid.uuid4().hex[:8]}",
            invoice_date=_BILL_DATE,
            status=InvoiceStatus.ISSUED,
            total_amount=Decimal("5000.00"),
            paid_amount=Decimal("0"),
            balance_amount=Decimal("5000.00"),
            created_by=user.id,
            updated_by=user.id,
        )
        session.add_all([invoice_a, invoice_b])
        await session.flush()

        payment_a = Payment(
            tenant_id=tenant.id,
            company_id=company.id,
            payment_number=None,
            payment_date=_BILL_DATE,
            payment_method=PaymentMethod.CHEQUE,
            amount=Decimal("4000.00"),
            allocated_amount=Decimal("0"),
            unallocated_amount=Decimal("4000.00"),
            status=CustomerPaymentStatus.DRAFT,
            created_by=user.id,
            updated_by=user.id,
        )
        payment_b = Payment(
            tenant_id=tenant.id,
            company_id=company.id,
            payment_number=None,
            payment_date=_BILL_DATE,
            payment_method=PaymentMethod.CHEQUE,
            amount=Decimal("2000.00"),
            allocated_amount=Decimal("0"),
            unallocated_amount=Decimal("2000.00"),
            status=CustomerPaymentStatus.DRAFT,
            created_by=user.id,
            updated_by=user.id,
        )
        session.add_all([payment_a, payment_b])
        await session.flush()

        await session.commit()
        return _CustomerScenario(
            tenant_id=tenant.id,
            actor_id=user.id,
            company_id=company.id,
            invoice_a_id=invoice_a.id,
            invoice_b_id=invoice_b.id,
            payment_a_id=payment_a.id,
            payment_b_id=payment_b.id,
        )


async def _cleanup_customer_scenario(tenant_id: uuid.UUID) -> None:
    async with async_session_factory() as session:
        await session.execute(
            delete(PaymentAllocation).where(PaymentAllocation.tenant_id == tenant_id)
        )
        await session.execute(delete(Payment).where(Payment.tenant_id == tenant_id))
        await session.execute(delete(Invoice).where(Invoice.tenant_id == tenant_id))
        await session.execute(delete(Company).where(Company.tenant_id == tenant_id))
        await session.execute(delete(User).where(User.tenant_id == tenant_id))
        await session.execute(delete(Tenant).where(Tenant.id == tenant_id))
        await session.commit()


async def _setup_supplier_scenario() -> _SupplierScenario:
    """Mirrors _setup_customer_scenario exactly for the payable side: a
    supplier with two open (POSTED) purchase bills - A=10,000, B=5,000 -
    outstanding_amount already correctly 15,000, plus one DRAFT supplier
    payment per bill."""
    async with async_session_factory() as session:
        tenant = Tenant(
            name="Outstanding Race Supplier Co", slug=f"outrace-sup-{uuid.uuid4().hex[:8]}"
        )
        session.add(tenant)
        await session.flush()

        user = User(
            tenant_id=tenant.id,
            email=f"racer-{uuid.uuid4().hex[:8]}@fisherp.local",
            username=f"racer-{uuid.uuid4().hex[:8]}",
            password_hash="not-a-real-hash",
            full_name="Outstanding Race Tester",
            status=AccountStatus.ACTIVE,
        )
        session.add(user)
        await session.flush()

        supplier = Supplier(
            tenant_id=tenant.id,
            code=f"ORACE-{uuid.uuid4().hex[:8]}",
            name=f"Outstanding Race Supplier {uuid.uuid4().hex[:8]}",
            status=SupplierStatus.ACTIVE,
            outstanding_amount=Decimal("15000.00"),
            created_by=user.id,
            updated_by=user.id,
        )
        session.add(supplier)
        await session.flush()

        bill_a = PurchaseBill(
            tenant_id=tenant.id,
            supplier_id=supplier.id,
            bill_number=f"PUR-ORACE-{uuid.uuid4().hex[:8]}",
            bill_date=_BILL_DATE,
            status=PurchaseStatus.POSTED,
            total_amount=Decimal("10000.00"),
            paid_amount=Decimal("0"),
            balance_amount=Decimal("10000.00"),
            posted_at=None,
            created_by=user.id,
            updated_by=user.id,
        )
        bill_b = PurchaseBill(
            tenant_id=tenant.id,
            supplier_id=supplier.id,
            bill_number=f"PUR-ORACE-{uuid.uuid4().hex[:8]}",
            bill_date=_BILL_DATE,
            status=PurchaseStatus.POSTED,
            total_amount=Decimal("5000.00"),
            paid_amount=Decimal("0"),
            balance_amount=Decimal("5000.00"),
            posted_at=None,
            created_by=user.id,
            updated_by=user.id,
        )
        session.add_all([bill_a, bill_b])
        await session.flush()

        payment_a = SupplierPayment(
            tenant_id=tenant.id,
            supplier_id=supplier.id,
            payment_number=None,
            payment_date=_BILL_DATE,
            payment_method=SupplierPaymentMethod.CHEQUE,
            amount=Decimal("4000.00"),
            allocated_amount=Decimal("0"),
            unallocated_amount=Decimal("4000.00"),
            status=SupplierPaymentStatus.DRAFT,
            posted_at=None,
            created_by=user.id,
            updated_by=user.id,
        )
        payment_b = SupplierPayment(
            tenant_id=tenant.id,
            supplier_id=supplier.id,
            payment_number=None,
            payment_date=_BILL_DATE,
            payment_method=SupplierPaymentMethod.CHEQUE,
            amount=Decimal("2000.00"),
            allocated_amount=Decimal("0"),
            unallocated_amount=Decimal("2000.00"),
            status=SupplierPaymentStatus.DRAFT,
            posted_at=None,
            created_by=user.id,
            updated_by=user.id,
        )
        session.add_all([payment_a, payment_b])
        await session.flush()

        await session.commit()
        return _SupplierScenario(
            tenant_id=tenant.id,
            actor_id=user.id,
            supplier_id=supplier.id,
            bill_a_id=bill_a.id,
            bill_b_id=bill_b.id,
            payment_a_id=payment_a.id,
            payment_b_id=payment_b.id,
        )


async def _cleanup_supplier_scenario(tenant_id: uuid.UUID) -> None:
    async with async_session_factory() as session:
        await session.execute(
            delete(SupplierPaymentAllocation).where(
                SupplierPaymentAllocation.tenant_id == tenant_id
            )
        )
        await session.execute(delete(SupplierPayment).where(SupplierPayment.tenant_id == tenant_id))
        await session.execute(delete(PurchaseBill).where(PurchaseBill.tenant_id == tenant_id))
        await session.execute(delete(Supplier).where(Supplier.tenant_id == tenant_id))
        await session.execute(delete(User).where(User.tenant_id == tenant_id))
        await session.execute(delete(Tenant).where(Tenant.id == tenant_id))
        await session.commit()


async def _create_customer_allocation(
    *,
    payment_id: uuid.UUID,
    invoice_id: uuid.UUID,
    amount: Decimal,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    start_barrier: asyncio.Barrier,
) -> None:
    async with async_session_factory() as session:
        await start_barrier.wait()
        service = PaymentService(session)
        await service.create_allocation(
            payment_id,
            PaymentAllocationCreateRequest(invoice_id=invoice_id, allocated_amount=amount),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )


async def _delete_customer_allocation(
    *,
    payment_id: uuid.UUID,
    allocation_id: uuid.UUID,
    tenant_id: uuid.UUID,
    start_barrier: asyncio.Barrier,
) -> None:
    async with async_session_factory() as session:
        await start_barrier.wait()
        service = PaymentService(session)
        await service.delete_allocation(payment_id, allocation_id, tenant_id=tenant_id)


async def _create_supplier_allocation(
    *,
    supplier_payment_id: uuid.UUID,
    purchase_bill_id: uuid.UUID,
    amount: Decimal,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    start_barrier: asyncio.Barrier,
) -> None:
    async with async_session_factory() as session:
        await start_barrier.wait()
        service = SupplierPaymentService(session)
        await service.create_allocation(
            supplier_payment_id,
            SupplierPaymentAllocationCreateRequest(
                purchase_bill_id=purchase_bill_id, allocated_amount=amount
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )


async def _delete_supplier_allocation(
    *,
    supplier_payment_id: uuid.UUID,
    allocation_id: uuid.UUID,
    tenant_id: uuid.UUID,
    start_barrier: asyncio.Barrier,
) -> None:
    async with async_session_factory() as session:
        await start_barrier.wait()
        service = SupplierPaymentService(session)
        await service.delete_allocation(supplier_payment_id, allocation_id, tenant_id=tenant_id)


class TestCompanyOutstandingConcurrency:
    """Two concurrent operations that each recompute the SAME company's
    outstanding_amount, triggered by changes to two DIFFERENT invoices -
    the exact scenario Sprint 13 Session 3's brief specifies. Before the
    fix (locking the company row FOR UPDATE before the SUM), both
    recomputes read a stale snapshot of the other's not-yet-committed
    invoice change, and whichever's blind SET commits last silently drops
    the other's contribution."""

    async def test_two_concurrent_allocations_against_different_invoices(self) -> None:
        scenario = await _setup_customer_scenario()
        start_barrier = asyncio.Barrier(2)
        try:
            await asyncio.gather(
                _create_customer_allocation(
                    payment_id=scenario.payment_a_id,
                    invoice_id=scenario.invoice_a_id,
                    amount=Decimal("4000.00"),
                    tenant_id=scenario.tenant_id,
                    actor_id=scenario.actor_id,
                    start_barrier=start_barrier,
                ),
                _create_customer_allocation(
                    payment_id=scenario.payment_b_id,
                    invoice_id=scenario.invoice_b_id,
                    amount=Decimal("2000.00"),
                    tenant_id=scenario.tenant_id,
                    actor_id=scenario.actor_id,
                    start_barrier=start_barrier,
                ),
            )

            async with async_session_factory() as verify_session:
                service = PaymentService(verify_session)
                invoice_a = await service._invoice_service.get(
                    scenario.invoice_a_id, tenant_id=scenario.tenant_id
                )
                invoice_b = await service._invoice_service.get(
                    scenario.invoice_b_id, tenant_id=scenario.tenant_id
                )
                assert invoice_a.balance_amount == Decimal("6000.00")
                assert invoice_b.balance_amount == Decimal("3000.00")
                true_sum = invoice_a.balance_amount + invoice_b.balance_amount

                company = await service._company_service.get(
                    scenario.company_id, tenant_id=scenario.tenant_id
                )
                assert company.outstanding_amount == true_sum, (
                    "Company.outstanding_amount must equal the authoritative SUM of open "
                    f"invoice balances ({true_sum}) even under concurrent recomputation - "
                    f"got {company.outstanding_amount} (a lost-update race)"
                )
        finally:
            await _cleanup_customer_scenario(scenario.tenant_id)

    async def test_allocation_create_concurrent_with_allocation_delete(self) -> None:
        """Invoice B already has an existing allocation being freed
        (delete_allocation) at the same moment invoice A receives a new one
        (create_allocation) - both cascade into the same company's
        outstanding recompute concurrently."""
        scenario = await _setup_customer_scenario()
        async with async_session_factory() as setup_session:
            service = PaymentService(setup_session)
            existing = await service.create_allocation(
                scenario.payment_b_id,
                PaymentAllocationCreateRequest(
                    invoice_id=scenario.invoice_b_id, allocated_amount=Decimal("2000.00")
                ),
                tenant_id=scenario.tenant_id,
                actor_id=scenario.actor_id,
            )
        start_barrier = asyncio.Barrier(2)
        try:
            await asyncio.gather(
                _create_customer_allocation(
                    payment_id=scenario.payment_a_id,
                    invoice_id=scenario.invoice_a_id,
                    amount=Decimal("4000.00"),
                    tenant_id=scenario.tenant_id,
                    actor_id=scenario.actor_id,
                    start_barrier=start_barrier,
                ),
                _delete_customer_allocation(
                    payment_id=scenario.payment_b_id,
                    allocation_id=existing.id,
                    tenant_id=scenario.tenant_id,
                    start_barrier=start_barrier,
                ),
            )

            async with async_session_factory() as verify_session:
                service = PaymentService(verify_session)
                invoice_a = await service._invoice_service.get(
                    scenario.invoice_a_id, tenant_id=scenario.tenant_id
                )
                invoice_b = await service._invoice_service.get(
                    scenario.invoice_b_id, tenant_id=scenario.tenant_id
                )
                assert invoice_a.balance_amount == Decimal("6000.00")
                assert invoice_b.balance_amount == Decimal("5000.00")
                true_sum = invoice_a.balance_amount + invoice_b.balance_amount

                company = await service._company_service.get(
                    scenario.company_id, tenant_id=scenario.tenant_id
                )
                assert company.outstanding_amount == true_sum, (
                    "Company.outstanding_amount must equal the authoritative SUM even when a "
                    f"create and a delete race each other - got {company.outstanding_amount}, "
                    f"expected {true_sum}"
                )
        finally:
            await _cleanup_customer_scenario(scenario.tenant_id)


class TestSupplierOutstandingConcurrency:
    """Mirrors TestCompanyOutstandingConcurrency exactly for the payable
    side (SupplierPayment -> SupplierPaymentAllocation -> PurchaseBill ->
    Supplier)."""

    async def test_two_concurrent_allocations_against_different_bills(self) -> None:
        scenario = await _setup_supplier_scenario()
        start_barrier = asyncio.Barrier(2)
        try:
            await asyncio.gather(
                _create_supplier_allocation(
                    supplier_payment_id=scenario.payment_a_id,
                    purchase_bill_id=scenario.bill_a_id,
                    amount=Decimal("4000.00"),
                    tenant_id=scenario.tenant_id,
                    actor_id=scenario.actor_id,
                    start_barrier=start_barrier,
                ),
                _create_supplier_allocation(
                    supplier_payment_id=scenario.payment_b_id,
                    purchase_bill_id=scenario.bill_b_id,
                    amount=Decimal("2000.00"),
                    tenant_id=scenario.tenant_id,
                    actor_id=scenario.actor_id,
                    start_barrier=start_barrier,
                ),
            )

            async with async_session_factory() as verify_session:
                service = SupplierPaymentService(verify_session)
                bill_a = await service._purchase_service.get(
                    scenario.bill_a_id, tenant_id=scenario.tenant_id
                )
                bill_b = await service._purchase_service.get(
                    scenario.bill_b_id, tenant_id=scenario.tenant_id
                )
                assert bill_a.balance_amount == Decimal("6000.00")
                assert bill_b.balance_amount == Decimal("3000.00")
                true_sum = bill_a.balance_amount + bill_b.balance_amount

                supplier = await service._supplier_service.get(
                    scenario.supplier_id, tenant_id=scenario.tenant_id
                )
                assert supplier.outstanding_amount == true_sum, (
                    "Supplier.outstanding_amount must equal the authoritative SUM of open "
                    f"purchase bill balances ({true_sum}) even under concurrent recomputation - "
                    f"got {supplier.outstanding_amount} (a lost-update race)"
                )
        finally:
            await _cleanup_supplier_scenario(scenario.tenant_id)

    async def test_allocation_create_concurrent_with_allocation_delete(self) -> None:
        scenario = await _setup_supplier_scenario()
        async with async_session_factory() as setup_session:
            service = SupplierPaymentService(setup_session)
            existing = await service.create_allocation(
                scenario.payment_b_id,
                SupplierPaymentAllocationCreateRequest(
                    purchase_bill_id=scenario.bill_b_id, allocated_amount=Decimal("2000.00")
                ),
                tenant_id=scenario.tenant_id,
                actor_id=scenario.actor_id,
            )
        start_barrier = asyncio.Barrier(2)
        try:
            await asyncio.gather(
                _create_supplier_allocation(
                    supplier_payment_id=scenario.payment_a_id,
                    purchase_bill_id=scenario.bill_a_id,
                    amount=Decimal("4000.00"),
                    tenant_id=scenario.tenant_id,
                    actor_id=scenario.actor_id,
                    start_barrier=start_barrier,
                ),
                _delete_supplier_allocation(
                    supplier_payment_id=scenario.payment_b_id,
                    allocation_id=existing.id,
                    tenant_id=scenario.tenant_id,
                    start_barrier=start_barrier,
                ),
            )

            async with async_session_factory() as verify_session:
                service = SupplierPaymentService(verify_session)
                bill_a = await service._purchase_service.get(
                    scenario.bill_a_id, tenant_id=scenario.tenant_id
                )
                bill_b = await service._purchase_service.get(
                    scenario.bill_b_id, tenant_id=scenario.tenant_id
                )
                assert bill_a.balance_amount == Decimal("6000.00")
                assert bill_b.balance_amount == Decimal("5000.00")
                true_sum = bill_a.balance_amount + bill_b.balance_amount

                supplier = await service._supplier_service.get(
                    scenario.supplier_id, tenant_id=scenario.tenant_id
                )
                assert supplier.outstanding_amount == true_sum, (
                    "Supplier.outstanding_amount must equal the authoritative SUM even when a "
                    f"create and a delete race each other - got {supplier.outstanding_amount}, "
                    f"expected {true_sum}"
                )
        finally:
            await _cleanup_supplier_scenario(scenario.tenant_id)


class TestOutstandingRecomputeDeadlockSafety:
    """Sprint 13 Session 3 adds a Company/Supplier row lock, acquired only
    after the existing Payment/SupplierPayment -> Invoice/PurchaseBill locks
    (Session 2) - always last, never reversed. This runs several legitimate
    concurrent allocations against a shared company/supplier (more lock
    contention than either test above) and asserts they all complete
    without deadlock or timeout."""

    async def test_many_concurrent_customer_allocations_do_not_deadlock(self) -> None:
        scenario = await _setup_customer_scenario()
        start_barrier = asyncio.Barrier(2)
        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    _create_customer_allocation(
                        payment_id=scenario.payment_a_id,
                        invoice_id=scenario.invoice_a_id,
                        amount=Decimal("4000.00"),
                        tenant_id=scenario.tenant_id,
                        actor_id=scenario.actor_id,
                        start_barrier=start_barrier,
                    ),
                    _create_customer_allocation(
                        payment_id=scenario.payment_b_id,
                        invoice_id=scenario.invoice_b_id,
                        amount=Decimal("2000.00"),
                        tenant_id=scenario.tenant_id,
                        actor_id=scenario.actor_id,
                        start_barrier=start_barrier,
                    ),
                    return_exceptions=True,
                ),
                timeout=15,
            )
            for result in results:
                if isinstance(result, BaseException):
                    raise result
        finally:
            await _cleanup_customer_scenario(scenario.tenant_id)

    async def test_many_concurrent_supplier_allocations_do_not_deadlock(self) -> None:
        scenario = await _setup_supplier_scenario()
        start_barrier = asyncio.Barrier(2)
        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    _create_supplier_allocation(
                        supplier_payment_id=scenario.payment_a_id,
                        purchase_bill_id=scenario.bill_a_id,
                        amount=Decimal("4000.00"),
                        tenant_id=scenario.tenant_id,
                        actor_id=scenario.actor_id,
                        start_barrier=start_barrier,
                    ),
                    _create_supplier_allocation(
                        supplier_payment_id=scenario.payment_b_id,
                        purchase_bill_id=scenario.bill_b_id,
                        amount=Decimal("2000.00"),
                        tenant_id=scenario.tenant_id,
                        actor_id=scenario.actor_id,
                        start_barrier=start_barrier,
                    ),
                    return_exceptions=True,
                ),
                timeout=15,
            )
            for result in results:
                if isinstance(result, BaseException):
                    raise result
        finally:
            await _cleanup_supplier_scenario(scenario.tenant_id)
