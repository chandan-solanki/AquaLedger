"""Sprint 13 Session 4 - final financial-integrity validation & concurrency
stress pass over Sessions 1-3 (ARCHITECTURE.md §14.2).

This file does NOT change any invariant Sessions 1-3 established - it exists
to stress them harder than the existing regression suites
(test_allocation_concurrency.py, test_outstanding_concurrency.py) do:

- three-way concurrency (three invoices/purchase bills of one company/
  supplier, not just two) for Phases 3/4/5/7 of the Session 4 brief
- tenant isolation under concurrent load (Phase 8)
- decimal precision under concurrent, non-conflicting allocations that sum
  exactly to a fractional total (Phase 12)

Mirrors test_allocation_concurrency.py's approach exactly: real, independent
sessions from `app.db.session.async_session_factory` (not the rollback-only
`db_session` fixture - see that file's module docstring for why real
concurrency requires two genuinely separate connections/transactions), real
committed rows, `asyncio.Barrier` to force simultaneous entry, cleaned up in
a `finally` block.
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
from app.modules.payments.exceptions import PaymentAllocationInvoiceNotFoundError
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
    invoice_ids: list[uuid.UUID]
    payment_ids: list[uuid.UUID]


class _SupplierScenario(NamedTuple):
    tenant_id: uuid.UUID
    actor_id: uuid.UUID
    supplier_id: uuid.UUID
    bill_ids: list[uuid.UUID]
    payment_ids: list[uuid.UUID]


async def _setup_customer_scenario(
    *, invoice_totals: list[Decimal], payment_amounts: list[Decimal]
) -> _CustomerScenario:
    """A company with one ISSUED invoice per `invoice_totals` entry and one
    DRAFT payment per `payment_amounts` entry - the Session 4 brief's
    "Customer A / Invoice 1,2,3 / multiple payments" scenario, generalized to
    any count so the same helper covers both the 3-invoice stress tests and
    the 2-invoice decimal test."""
    async with async_session_factory() as session:
        tenant = Tenant(name="Session4 Co", slug=f"s4-{uuid.uuid4().hex[:8]}")
        session.add(tenant)
        await session.flush()

        user = User(
            tenant_id=tenant.id,
            email=f"s4-{uuid.uuid4().hex[:8]}@fisherp.local",
            username=f"s4-{uuid.uuid4().hex[:8]}",
            password_hash="not-a-real-hash",
            full_name="Session4 Tester",
            status=AccountStatus.ACTIVE,
        )
        session.add(user)
        await session.flush()

        company = Company(
            tenant_id=tenant.id,
            code=f"S4-{uuid.uuid4().hex[:8]}",
            name=f"Session4 Customer {uuid.uuid4().hex[:8]}",
            company_type=CompanyType.CUSTOMER,
            status=CompanyStatus.ACTIVE,
            outstanding_amount=sum(invoice_totals, Decimal("0")),
            created_by=user.id,
            updated_by=user.id,
        )
        session.add(company)
        await session.flush()

        invoice_ids: list[uuid.UUID] = []
        for total in invoice_totals:
            invoice = Invoice(
                tenant_id=tenant.id,
                company_id=company.id,
                invoice_number=f"INV-S4-{uuid.uuid4().hex[:8]}",
                invoice_date=_BILL_DATE,
                status=InvoiceStatus.ISSUED,
                total_amount=total,
                paid_amount=Decimal("0"),
                balance_amount=total,
                created_by=user.id,
                updated_by=user.id,
            )
            session.add(invoice)
            await session.flush()
            invoice_ids.append(invoice.id)

        payment_ids: list[uuid.UUID] = []
        for amount in payment_amounts:
            payment = Payment(
                tenant_id=tenant.id,
                company_id=company.id,
                payment_number=None,
                payment_date=_BILL_DATE,
                payment_method=PaymentMethod.CHEQUE,
                amount=amount,
                allocated_amount=Decimal("0"),
                unallocated_amount=amount,
                status=CustomerPaymentStatus.DRAFT,
                created_by=user.id,
                updated_by=user.id,
            )
            session.add(payment)
            await session.flush()
            payment_ids.append(payment.id)

        await session.commit()
        return _CustomerScenario(
            tenant_id=tenant.id,
            actor_id=user.id,
            company_id=company.id,
            invoice_ids=invoice_ids,
            payment_ids=payment_ids,
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


async def _setup_supplier_scenario(
    *, bill_totals: list[Decimal], payment_amounts: list[Decimal]
) -> _SupplierScenario:
    async with async_session_factory() as session:
        tenant = Tenant(name="Session4 Supplier Co", slug=f"s4-sup-{uuid.uuid4().hex[:8]}")
        session.add(tenant)
        await session.flush()

        user = User(
            tenant_id=tenant.id,
            email=f"s4-{uuid.uuid4().hex[:8]}@fisherp.local",
            username=f"s4-{uuid.uuid4().hex[:8]}",
            password_hash="not-a-real-hash",
            full_name="Session4 Tester",
            status=AccountStatus.ACTIVE,
        )
        session.add(user)
        await session.flush()

        supplier = Supplier(
            tenant_id=tenant.id,
            code=f"S4-{uuid.uuid4().hex[:8]}",
            name=f"Session4 Supplier {uuid.uuid4().hex[:8]}",
            status=SupplierStatus.ACTIVE,
            outstanding_amount=sum(bill_totals, Decimal("0")),
            created_by=user.id,
            updated_by=user.id,
        )
        session.add(supplier)
        await session.flush()

        bill_ids: list[uuid.UUID] = []
        for total in bill_totals:
            bill = PurchaseBill(
                tenant_id=tenant.id,
                supplier_id=supplier.id,
                bill_number=f"PUR-S4-{uuid.uuid4().hex[:8]}",
                bill_date=_BILL_DATE,
                status=PurchaseStatus.POSTED,
                total_amount=total,
                paid_amount=Decimal("0"),
                balance_amount=total,
                posted_at=None,
                created_by=user.id,
                updated_by=user.id,
            )
            session.add(bill)
            await session.flush()
            bill_ids.append(bill.id)

        payment_ids: list[uuid.UUID] = []
        for amount in payment_amounts:
            supplier_payment = SupplierPayment(
                tenant_id=tenant.id,
                supplier_id=supplier.id,
                payment_number=None,
                payment_date=_BILL_DATE,
                payment_method=SupplierPaymentMethod.CHEQUE,
                amount=amount,
                allocated_amount=Decimal("0"),
                unallocated_amount=amount,
                status=SupplierPaymentStatus.DRAFT,
                posted_at=None,
                created_by=user.id,
                updated_by=user.id,
            )
            session.add(supplier_payment)
            await session.flush()
            payment_ids.append(supplier_payment.id)

        await session.commit()
        return _SupplierScenario(
            tenant_id=tenant.id,
            actor_id=user.id,
            supplier_id=supplier.id,
            bill_ids=bill_ids,
            payment_ids=payment_ids,
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
) -> Exception | None:
    """Runs one create_allocation on its own independent connection,
    returning the exception (if any) instead of propagating it, so
    asyncio.gather can run every racer to completion regardless of which
    ones are expected to fail."""
    async with async_session_factory() as session:
        await start_barrier.wait()
        service = PaymentService(session)
        try:
            await service.create_allocation(
                payment_id,
                PaymentAllocationCreateRequest(invoice_id=invoice_id, allocated_amount=amount),
                tenant_id=tenant_id,
                actor_id=actor_id,
            )
        except Exception as exc:  # noqa: BLE001 - the race's outcome is the point
            return exc
        return None


async def _create_supplier_allocation(
    *,
    supplier_payment_id: uuid.UUID,
    purchase_bill_id: uuid.UUID,
    amount: Decimal,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    start_barrier: asyncio.Barrier,
) -> Exception | None:
    async with async_session_factory() as session:
        await start_barrier.wait()
        service = SupplierPaymentService(session)
        try:
            await service.create_allocation(
                supplier_payment_id,
                SupplierPaymentAllocationCreateRequest(
                    purchase_bill_id=purchase_bill_id, allocated_amount=amount
                ),
                tenant_id=tenant_id,
                actor_id=actor_id,
            )
        except Exception as exc:  # noqa: BLE001 - the race's outcome is the point
            return exc
        return None


class TestCustomerThreeWayAllocationStress:
    """Phase 3/5/7 of the Session 4 brief: three concurrent allocations
    against three different invoices of the SAME company - one order of
    magnitude more lock contention on Company.outstanding_amount than the
    2-way tests in test_outstanding_concurrency.py, run under a bounded
    timeout to prove the Payment -> Invoice -> Company lock order still
    can't deadlock with three participants instead of two."""

    async def test_three_concurrent_full_allocations_settle_every_invoice_and_the_company(
        self,
    ) -> None:
        # Customer A: Invoice 1 = 10,000, Invoice 2 = 8,000, Invoice 3 = 5,000
        # (exactly the Session 4 brief's example), one payment per invoice
        # for its exact remaining balance, all three allocated concurrently.
        amounts = [Decimal("10000.00"), Decimal("8000.00"), Decimal("5000.00")]
        scenario = await _setup_customer_scenario(invoice_totals=amounts, payment_amounts=amounts)
        start_barrier = asyncio.Barrier(3)
        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    *(
                        _create_customer_allocation(
                            payment_id=scenario.payment_ids[i],
                            invoice_id=scenario.invoice_ids[i],
                            amount=amounts[i],
                            tenant_id=scenario.tenant_id,
                            actor_id=scenario.actor_id,
                            start_barrier=start_barrier,
                        )
                        for i in range(3)
                    )
                ),
                timeout=15,
            )

            assert results == [None, None, None], (
                "three concurrent allocations against three DIFFERENT invoices of the same "
                f"company must all succeed - no real contention exists between them: {results}"
            )

            async with async_session_factory() as verify_session:
                service = PaymentService(verify_session)
                invoices = [
                    await service._invoice_service.get(inv_id, tenant_id=scenario.tenant_id)
                    for inv_id in scenario.invoice_ids
                ]
                for invoice, total in zip(invoices, amounts, strict=True):
                    assert invoice.balance_amount == Decimal("0.00")
                    assert invoice.paid_amount == total
                    assert invoice.status == InvoiceStatus.PAID

                true_sum = sum((inv.balance_amount for inv in invoices), Decimal("0.00"))
                assert true_sum == Decimal("0.00")

                company = await service._company_service.get(
                    scenario.company_id, tenant_id=scenario.tenant_id
                )
                assert company.outstanding_amount == true_sum, (
                    "Company.outstanding_amount must equal the authoritative SUM of open "
                    f"invoice balances (0.00) after three concurrent allocations - "
                    f"got {company.outstanding_amount}"
                )

                payments = [
                    await service.get(pay_id, tenant_id=scenario.tenant_id)
                    for pay_id in scenario.payment_ids
                ]
                for payment, total in zip(payments, amounts, strict=True):
                    assert payment.allocated_amount == total
                    assert payment.unallocated_amount == Decimal("0.00")
        finally:
            await _cleanup_customer_scenario(scenario.tenant_id)

    async def test_three_concurrent_partial_allocations_do_not_deadlock_and_outstanding_matches_sum(
        self,
    ) -> None:
        # Same three invoices, but each payment only partially settles its
        # invoice - proves the invariant holds (and no deadlock occurs) even
        # when every invoice ends up PARTIALLY_PAID rather than PAID, and
        # every payment retains unallocated_amount > 0.
        invoice_totals = [Decimal("10000.00"), Decimal("8000.00"), Decimal("5000.00")]
        partials = [Decimal("4000.00"), Decimal("3000.00"), Decimal("2000.00")]
        scenario = await _setup_customer_scenario(
            invoice_totals=invoice_totals, payment_amounts=partials
        )
        start_barrier = asyncio.Barrier(3)
        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    *(
                        _create_customer_allocation(
                            payment_id=scenario.payment_ids[i],
                            invoice_id=scenario.invoice_ids[i],
                            amount=partials[i],
                            tenant_id=scenario.tenant_id,
                            actor_id=scenario.actor_id,
                            start_barrier=start_barrier,
                        )
                        for i in range(3)
                    )
                ),
                timeout=15,
            )
            assert results == [None, None, None]

            async with async_session_factory() as verify_session:
                service = PaymentService(verify_session)
                invoices = [
                    await service._invoice_service.get(inv_id, tenant_id=scenario.tenant_id)
                    for inv_id in scenario.invoice_ids
                ]
                expected_balances = [
                    total - partial for total, partial in zip(invoice_totals, partials, strict=True)
                ]
                for invoice, expected in zip(invoices, expected_balances, strict=True):
                    assert invoice.balance_amount == expected
                    assert invoice.status == InvoiceStatus.PARTIALLY_PAID
                    assert invoice.paid_amount >= Decimal("0")
                    assert invoice.balance_amount >= Decimal("0")

                true_sum = sum((inv.balance_amount for inv in invoices), Decimal("0.00"))
                company = await service._company_service.get(
                    scenario.company_id, tenant_id=scenario.tenant_id
                )
                assert company.outstanding_amount == true_sum, (
                    "Company.outstanding_amount must equal the authoritative SUM of open "
                    f"invoice balances ({true_sum}) after three concurrent partial "
                    f"allocations - got {company.outstanding_amount}"
                )
        finally:
            await _cleanup_customer_scenario(scenario.tenant_id)


class TestSupplierThreeWayAllocationStress:
    """Mirrors TestCustomerThreeWayAllocationStress exactly for the payable
    side (SupplierPayment -> SupplierPaymentAllocation -> PurchaseBill ->
    Supplier)."""

    async def test_three_concurrent_full_allocations_settle_every_bill_and_the_supplier(
        self,
    ) -> None:
        amounts = [Decimal("10000.00"), Decimal("8000.00"), Decimal("5000.00")]
        scenario = await _setup_supplier_scenario(bill_totals=amounts, payment_amounts=amounts)
        start_barrier = asyncio.Barrier(3)
        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    *(
                        _create_supplier_allocation(
                            supplier_payment_id=scenario.payment_ids[i],
                            purchase_bill_id=scenario.bill_ids[i],
                            amount=amounts[i],
                            tenant_id=scenario.tenant_id,
                            actor_id=scenario.actor_id,
                            start_barrier=start_barrier,
                        )
                        for i in range(3)
                    )
                ),
                timeout=15,
            )
            assert results == [None, None, None], (
                "three concurrent allocations against three DIFFERENT purchase bills of the "
                f"same supplier must all succeed: {results}"
            )

            async with async_session_factory() as verify_session:
                service = SupplierPaymentService(verify_session)
                bills = [
                    await service._purchase_service.get(bill_id, tenant_id=scenario.tenant_id)
                    for bill_id in scenario.bill_ids
                ]
                for bill, total in zip(bills, amounts, strict=True):
                    assert bill.balance_amount == Decimal("0.00")
                    assert bill.paid_amount == total
                    assert bill.status == PurchaseStatus.PAID

                true_sum = sum((bill.balance_amount for bill in bills), Decimal("0.00"))
                supplier = await service._supplier_service.get(
                    scenario.supplier_id, tenant_id=scenario.tenant_id
                )
                assert supplier.outstanding_amount == true_sum, (
                    "Supplier.outstanding_amount must equal the authoritative SUM of open "
                    f"purchase bill balances (0.00) after three concurrent allocations - "
                    f"got {supplier.outstanding_amount}"
                )

                payments = [
                    await service.get(pay_id, tenant_id=scenario.tenant_id)
                    for pay_id in scenario.payment_ids
                ]
                for payment, total in zip(payments, amounts, strict=True):
                    assert payment.allocated_amount == total
                    assert payment.unallocated_amount == Decimal("0.00")
        finally:
            await _cleanup_supplier_scenario(scenario.tenant_id)

    async def test_three_concurrent_partial_allocations_do_not_deadlock_and_outstanding_matches_sum(
        self,
    ) -> None:
        bill_totals = [Decimal("10000.00"), Decimal("8000.00"), Decimal("5000.00")]
        partials = [Decimal("4000.00"), Decimal("3000.00"), Decimal("2000.00")]
        scenario = await _setup_supplier_scenario(bill_totals=bill_totals, payment_amounts=partials)
        start_barrier = asyncio.Barrier(3)
        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    *(
                        _create_supplier_allocation(
                            supplier_payment_id=scenario.payment_ids[i],
                            purchase_bill_id=scenario.bill_ids[i],
                            amount=partials[i],
                            tenant_id=scenario.tenant_id,
                            actor_id=scenario.actor_id,
                            start_barrier=start_barrier,
                        )
                        for i in range(3)
                    )
                ),
                timeout=15,
            )
            assert results == [None, None, None]

            async with async_session_factory() as verify_session:
                service = SupplierPaymentService(verify_session)
                bills = [
                    await service._purchase_service.get(bill_id, tenant_id=scenario.tenant_id)
                    for bill_id in scenario.bill_ids
                ]
                expected_balances = [
                    total - partial for total, partial in zip(bill_totals, partials, strict=True)
                ]
                for bill, expected in zip(bills, expected_balances, strict=True):
                    assert bill.balance_amount == expected
                    assert bill.status == PurchaseStatus.PARTIALLY_PAID
                    assert bill.paid_amount >= Decimal("0")
                    assert bill.balance_amount >= Decimal("0")

                true_sum = sum((bill.balance_amount for bill in bills), Decimal("0.00"))
                supplier = await service._supplier_service.get(
                    scenario.supplier_id, tenant_id=scenario.tenant_id
                )
                assert supplier.outstanding_amount == true_sum, (
                    "Supplier.outstanding_amount must equal the authoritative SUM of open "
                    f"purchase bill balances ({true_sum}) after three concurrent partial "
                    f"allocations - got {supplier.outstanding_amount}"
                )
        finally:
            await _cleanup_supplier_scenario(scenario.tenant_id)


class TestTenantIsolationUnderConcurrency:
    """Phase 8 of the Session 4 brief: concurrent operations from two
    different tenants must never cross-contaminate, and an attempt to
    allocate against another tenant's invoice/purchase bill must fail with
    the existing typed not-found error - never a raw DB exception, never a
    silent cross-tenant mutation. Uses the existing repository/tenant_id
    scoping already in place (no new isolation mechanism)."""

    async def test_concurrent_allocations_across_two_tenants_do_not_cross_contaminate(
        self,
    ) -> None:
        scenario_a = await _setup_customer_scenario(
            invoice_totals=[Decimal("10000.00")], payment_amounts=[Decimal("6000.00")]
        )
        scenario_b = await _setup_customer_scenario(
            invoice_totals=[Decimal("7000.00")], payment_amounts=[Decimal("3000.00")]
        )
        start_barrier = asyncio.Barrier(2)
        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    _create_customer_allocation(
                        payment_id=scenario_a.payment_ids[0],
                        invoice_id=scenario_a.invoice_ids[0],
                        amount=Decimal("6000.00"),
                        tenant_id=scenario_a.tenant_id,
                        actor_id=scenario_a.actor_id,
                        start_barrier=start_barrier,
                    ),
                    _create_customer_allocation(
                        payment_id=scenario_b.payment_ids[0],
                        invoice_id=scenario_b.invoice_ids[0],
                        amount=Decimal("3000.00"),
                        tenant_id=scenario_b.tenant_id,
                        actor_id=scenario_b.actor_id,
                        start_barrier=start_barrier,
                    ),
                ),
                timeout=15,
            )
            assert list(results) == [None, None]

            async with async_session_factory() as verify_session:
                service = PaymentService(verify_session)
                invoice_a = await service._invoice_service.get(
                    scenario_a.invoice_ids[0], tenant_id=scenario_a.tenant_id
                )
                invoice_b = await service._invoice_service.get(
                    scenario_b.invoice_ids[0], tenant_id=scenario_b.tenant_id
                )
                assert invoice_a.balance_amount == Decimal("4000.00")
                assert invoice_b.balance_amount == Decimal("4000.00")

                company_a = await service._company_service.get(
                    scenario_a.company_id, tenant_id=scenario_a.tenant_id
                )
                company_b = await service._company_service.get(
                    scenario_b.company_id, tenant_id=scenario_b.tenant_id
                )
                assert company_a.outstanding_amount == Decimal("4000.00")
                assert company_b.outstanding_amount == Decimal("4000.00")
        finally:
            await _cleanup_customer_scenario(scenario_a.tenant_id)
            await _cleanup_customer_scenario(scenario_b.tenant_id)

    async def test_allocation_against_foreign_tenant_invoice_is_rejected_without_mutation(
        self,
    ) -> None:
        scenario_a = await _setup_customer_scenario(
            invoice_totals=[Decimal("10000.00")], payment_amounts=[Decimal("5000.00")]
        )
        scenario_b = await _setup_customer_scenario(
            invoice_totals=[Decimal("7000.00")], payment_amounts=[]
        )
        try:
            async with async_session_factory() as session:
                service = PaymentService(session)
                raised: Exception | None = None
                try:
                    await service.create_allocation(
                        scenario_a.payment_ids[0],
                        PaymentAllocationCreateRequest(
                            invoice_id=scenario_b.invoice_ids[0],
                            allocated_amount=Decimal("5000.00"),
                        ),
                        # Tenant A's actor, using Tenant A's own tenant_id (as any
                        # authenticated request would), targeting Tenant B's
                        # invoice id - the cross-tenant reference must be rejected
                        # purely because the invoice doesn't resolve under
                        # Tenant A's scope, exactly like a typo'd/unknown id would.
                        tenant_id=scenario_a.tenant_id,
                        actor_id=scenario_a.actor_id,
                    )
                except PaymentAllocationInvoiceNotFoundError as exc:
                    raised = exc
                assert raised is not None, (
                    "allocating against another tenant's invoice id must raise the same "
                    "typed not-found error as an unknown id - it must never succeed nor leak "
                    "a distinguishing raw DB error"
                )

            async with async_session_factory() as verify_session:
                service = PaymentService(verify_session)
                invoice_b = await service._invoice_service.get(
                    scenario_b.invoice_ids[0], tenant_id=scenario_b.tenant_id
                )
                assert invoice_b.balance_amount == Decimal("7000.00"), (
                    "the foreign invoice must be completely untouched by the rejected "
                    f"cross-tenant attempt - got balance {invoice_b.balance_amount}"
                )
                payment_a = await service.get(
                    scenario_a.payment_ids[0], tenant_id=scenario_a.tenant_id
                )
                assert payment_a.allocated_amount == Decimal("0.00"), (
                    "the rejecting payment must also be untouched - got allocated_amount "
                    f"{payment_a.allocated_amount}"
                )
        finally:
            await _cleanup_customer_scenario(scenario_a.tenant_id)
            await _cleanup_customer_scenario(scenario_b.tenant_id)


class TestDecimalPrecisionUnderConcurrency:
    """Phase 12 of the Session 4 brief: two concurrent, non-conflicting
    allocations whose amounts sum EXACTLY to a fractional invoice total
    (100.01 = 33.33 + 66.68) must leave the invoice at exactly 0.00 - not
    0.01 or -0.01 - proving the SUM-then-SET recompute (Decimal throughout,
    never float) introduces no rounding residue even when both allocations
    commit through the same lock in quick succession."""

    async def test_two_concurrent_fractional_allocations_summing_exactly_leave_zero_residue(
        self,
    ) -> None:
        scenario = await _setup_customer_scenario(
            invoice_totals=[Decimal("100.01")],
            payment_amounts=[Decimal("33.33"), Decimal("66.68")],
        )
        payment_x_id, payment_y_id = scenario.payment_ids
        (invoice_id,) = scenario.invoice_ids
        start_barrier = asyncio.Barrier(2)
        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    _create_customer_allocation(
                        payment_id=payment_x_id,
                        invoice_id=invoice_id,
                        amount=Decimal("33.33"),
                        tenant_id=scenario.tenant_id,
                        actor_id=scenario.actor_id,
                        start_barrier=start_barrier,
                    ),
                    _create_customer_allocation(
                        payment_id=payment_y_id,
                        invoice_id=invoice_id,
                        amount=Decimal("66.68"),
                        tenant_id=scenario.tenant_id,
                        actor_id=scenario.actor_id,
                        start_barrier=start_barrier,
                    ),
                ),
                timeout=15,
            )
            assert list(results) == [None, None], (
                "33.33 + 66.68 == 100.01 exactly - both allocations fit within the invoice's "
                f"balance regardless of commit order and must both succeed: {results}"
            )

            async with async_session_factory() as verify_session:
                service = PaymentService(verify_session)
                invoice = await service._invoice_service.get(
                    invoice_id, tenant_id=scenario.tenant_id
                )
                assert invoice.paid_amount == Decimal("100.01")
                assert invoice.balance_amount == Decimal("0.00"), (
                    "no rounding residue may survive two concurrent Decimal allocations that "
                    f"sum exactly to the total - got balance_amount {invoice.balance_amount}"
                )
                assert invoice.status == InvoiceStatus.PAID

                company = await service._company_service.get(
                    scenario.company_id, tenant_id=scenario.tenant_id
                )
                assert company.outstanding_amount == Decimal("0.00")
        finally:
            await _cleanup_customer_scenario(scenario.tenant_id)
