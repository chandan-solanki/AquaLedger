"""Sprint 13 Session 2 - genuine PostgreSQL concurrency tests for the
payment-allocation TOCTOU race fixed this session (ARCHITECTURE.md §14.2).

These tests deliberately do NOT use the `db_session`/`client` fixtures from
conftest.py: that fixture wraps an entire test in one connection-level
transaction that is always rolled back via a SAVEPOINT, so a second,
genuinely independent connection would never see the rows it creates (see
test_trip_catch_repository.py::TestGetByIdForUpdate's docstring, which
documents this exact limitation for the same reason). A real concurrency
test needs two separate connections/transactions that Postgres can actually
serialize against each other - so this file opens its own sessions directly
from `app.db.session.async_session_factory` (the same factory production
code uses, with the same autoflush=False the payments/supplier_payments
services depend on), commits real rows, and cleans them up afterward.
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
from app.modules.payments.constants import PaymentMethod, PaymentStatus
from app.modules.payments.exceptions import (
    PaymentAllocationAmountExceededError,
    PaymentAllocationInvoiceInvalidStatusError,
)
from app.modules.payments.models import Payment, PaymentAllocation
from app.modules.payments.schemas import PaymentAllocationCreateRequest
from app.modules.payments.service import PaymentService
from app.modules.purchase.constants import PurchaseStatus
from app.modules.purchase.models import PurchaseBill
from app.modules.supplier_payments.constants import PaymentMethod as SupplierPaymentMethod
from app.modules.supplier_payments.constants import SupplierPaymentStatus
from app.modules.supplier_payments.exceptions import (
    SupplierPaymentAllocationAmountExceededError,
    SupplierPaymentPurchaseBillNotAllocatableError,
)
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
    invoice_id: uuid.UUID
    payment_ids: list[uuid.UUID]


class _SupplierScenario(NamedTuple):
    tenant_id: uuid.UUID
    actor_id: uuid.UUID
    supplier_id: uuid.UUID
    purchase_bill_id: uuid.UUID
    payment_ids: list[uuid.UUID]


async def _setup_customer_scenario(
    *, invoice_total: Decimal, payment_amounts: list[Decimal]
) -> _CustomerScenario:
    """Commits a real tenant/user/company/ISSUED invoice, plus one DRAFT
    payment per amount in `payment_amounts` - all for real, on their own
    connection, so a second independent session can see them."""
    async with async_session_factory() as session:
        tenant = Tenant(name="Concurrency Co", slug=f"concurrency-{uuid.uuid4().hex[:8]}")
        session.add(tenant)
        await session.flush()

        user = User(
            tenant_id=tenant.id,
            email=f"racer-{uuid.uuid4().hex[:8]}@fisherp.local",
            username=f"racer-{uuid.uuid4().hex[:8]}",
            password_hash="not-a-real-hash",
            full_name="Concurrency Tester",
            status=AccountStatus.ACTIVE,
        )
        session.add(user)
        await session.flush()

        company = Company(
            tenant_id=tenant.id,
            code=f"CONC-{uuid.uuid4().hex[:8]}",
            name=f"Concurrency Customer {uuid.uuid4().hex[:8]}",
            company_type=CompanyType.CUSTOMER,
            status=CompanyStatus.ACTIVE,
            created_by=user.id,
            updated_by=user.id,
        )
        session.add(company)
        await session.flush()

        invoice = Invoice(
            tenant_id=tenant.id,
            company_id=company.id,
            invoice_number=f"INV-CONC-{uuid.uuid4().hex[:8]}",
            invoice_date=_BILL_DATE,
            status=InvoiceStatus.ISSUED,
            total_amount=invoice_total,
            paid_amount=Decimal("0"),
            balance_amount=invoice_total,
            issued_at=None,
            created_by=user.id,
            updated_by=user.id,
        )
        session.add(invoice)
        await session.flush()

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
                status=PaymentStatus.DRAFT,
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
            invoice_id=invoice.id,
            payment_ids=payment_ids,
        )


async def _add_invoice(
    tenant_id: uuid.UUID, company_id: uuid.UUID, actor_id: uuid.UUID, total: Decimal
) -> uuid.UUID:
    """A second ISSUED invoice under the same tenant/company - used by the
    "one payment can't be split beyond its own amount" test."""
    async with async_session_factory() as session:
        invoice = Invoice(
            tenant_id=tenant_id,
            company_id=company_id,
            invoice_number=f"INV-CONC-{uuid.uuid4().hex[:8]}",
            invoice_date=_BILL_DATE,
            status=InvoiceStatus.ISSUED,
            total_amount=total,
            paid_amount=Decimal("0"),
            balance_amount=total,
            created_by=actor_id,
            updated_by=actor_id,
        )
        session.add(invoice)
        await session.commit()
        return invoice.id


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
    *, bill_total: Decimal, payment_amounts: list[Decimal]
) -> _SupplierScenario:
    async with async_session_factory() as session:
        tenant = Tenant(name="Concurrency Supplier Co", slug=f"conc-sup-{uuid.uuid4().hex[:8]}")
        session.add(tenant)
        await session.flush()

        user = User(
            tenant_id=tenant.id,
            email=f"racer-{uuid.uuid4().hex[:8]}@fisherp.local",
            username=f"racer-{uuid.uuid4().hex[:8]}",
            password_hash="not-a-real-hash",
            full_name="Concurrency Tester",
            status=AccountStatus.ACTIVE,
        )
        session.add(user)
        await session.flush()

        supplier = Supplier(
            tenant_id=tenant.id,
            code=f"CONC-{uuid.uuid4().hex[:8]}",
            name=f"Concurrency Supplier {uuid.uuid4().hex[:8]}",
            status=SupplierStatus.ACTIVE,
            created_by=user.id,
            updated_by=user.id,
        )
        session.add(supplier)
        await session.flush()

        purchase_bill = PurchaseBill(
            tenant_id=tenant.id,
            supplier_id=supplier.id,
            bill_number=f"PUR-CONC-{uuid.uuid4().hex[:8]}",
            bill_date=_BILL_DATE,
            status=PurchaseStatus.POSTED,
            total_amount=bill_total,
            paid_amount=Decimal("0"),
            balance_amount=bill_total,
            posted_at=None,
            created_by=user.id,
            updated_by=user.id,
        )
        session.add(purchase_bill)
        await session.flush()

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
            purchase_bill_id=purchase_bill.id,
            payment_ids=payment_ids,
        )


async def _add_purchase_bill(
    tenant_id: uuid.UUID, supplier_id: uuid.UUID, actor_id: uuid.UUID, total: Decimal
) -> uuid.UUID:
    async with async_session_factory() as session:
        purchase_bill = PurchaseBill(
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            bill_number=f"PUR-CONC-{uuid.uuid4().hex[:8]}",
            bill_date=_BILL_DATE,
            status=PurchaseStatus.POSTED,
            total_amount=total,
            paid_amount=Decimal("0"),
            balance_amount=total,
            created_by=actor_id,
            updated_by=actor_id,
        )
        session.add(purchase_bill)
        await session.commit()
        return purchase_bill.id


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


async def _try_create_customer_allocation(
    *,
    payment_id: uuid.UUID,
    invoice_id: uuid.UUID,
    amount: Decimal,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    start_barrier: asyncio.Barrier,
) -> Exception | None:
    """Runs one create_allocation call on its own, independent session/
    connection/transaction - returns the exception raised (if any) instead
    of letting it propagate, so asyncio.gather can run both racers to
    completion and let the test assert on both outcomes.

    `start_barrier` (shared by both racers, size 2) is awaited right after
    opening the connection, so both coroutines enter create_allocation at
    the same instant instead of merely being scheduled "concurrently" by
    asyncio.gather - without it, one request can occasionally finish (and
    commit) before the other's first query even reaches Postgres, which
    would let the second correctly observe post-commit state without ever
    exercising the row lock this test exists to prove out.
    """
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
        except Exception as exc:  # noqa: BLE001 - the race's outcome is the point of this helper
            return exc
        return None


async def _try_create_supplier_allocation(
    *,
    supplier_payment_id: uuid.UUID,
    purchase_bill_id: uuid.UUID,
    amount: Decimal,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    start_barrier: asyncio.Barrier,
) -> Exception | None:
    """Mirrors _try_create_customer_allocation exactly, including the
    shared start_barrier - see its docstring for why."""
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
        except Exception as exc:  # noqa: BLE001 - the race's outcome is the point of this helper
            return exc
        return None


class TestCustomerPaymentAllocationConcurrency:
    """Reproduces the exact race Sprint 13 Session 1's audit confirmed and
    Session 2 fixed: two concurrent create_allocation calls validating
    against the same invoice/payment's stale balance. Before the fix
    (PaymentService locking payment/invoice FOR UPDATE before validating),
    both of these could succeed, over-allocating past the invoice's total or
    the payment's own amount."""

    async def test_two_full_payments_cannot_both_consume_one_invoice(self) -> None:
        # Invoice = 10,000; Payment A = 10,000; Payment B = 10,000 - the
        # exact scenario from the Session 2 brief. Both try to allocate
        # their full amount to the same invoice at the same time.
        scenario = await _setup_customer_scenario(
            invoice_total=Decimal("10000.00"),
            payment_amounts=[Decimal("10000.00"), Decimal("10000.00")],
        )
        payment_a_id, payment_b_id = scenario.payment_ids
        start_barrier = asyncio.Barrier(2)
        try:
            results = await asyncio.gather(
                _try_create_customer_allocation(
                    payment_id=payment_a_id,
                    invoice_id=scenario.invoice_id,
                    amount=Decimal("10000.00"),
                    tenant_id=scenario.tenant_id,
                    actor_id=scenario.actor_id,
                    start_barrier=start_barrier,
                ),
                _try_create_customer_allocation(
                    payment_id=payment_b_id,
                    invoice_id=scenario.invoice_id,
                    amount=Decimal("10000.00"),
                    tenant_id=scenario.tenant_id,
                    actor_id=scenario.actor_id,
                    start_barrier=start_barrier,
                ),
            )

            successes = [r for r in results if r is None]
            failures = [r for r in results if r is not None]
            assert len(successes) == 1, (
                "exactly one concurrent allocation must consume the invoice's balance - "
                f"got {len(successes)} successes"
            )
            assert len(failures) == 1
            # Whichever commits second sees the invoice already fully
            # allocated once its own lock unblocks - either because it's now
            # PAID (excluded from _ALLOCATABLE_INVOICE_STATUSES) or because
            # its balance is 0 (AllocationExceedsInvoiceBalanceError) -
            # both are pre-existing, typed business exceptions, never a raw
            # IntegrityError/DB exception leaking out.
            failure = failures[0]
            assert isinstance(
                failure,
                (PaymentAllocationInvoiceInvalidStatusError, PaymentAllocationAmountExceededError),
            ), f"expected a typed business exception, got {type(failure)}: {failure}"

            async with async_session_factory() as verify_session:
                service = PaymentService(verify_session)
                invoice = await service._invoice_service.get(
                    scenario.invoice_id, tenant_id=scenario.tenant_id
                )
                assert invoice.paid_amount == Decimal("10000.00")
                assert invoice.balance_amount == Decimal("0.00")
                assert invoice.status == InvoiceStatus.PAID

                total_allocated = await service._repo.sum_allocated_amount_by_invoice(
                    scenario.invoice_id, scenario.tenant_id
                )
                assert total_allocated == Decimal("10000.00"), (
                    "sum of allocations must never exceed the invoice total - "
                    f"got {total_allocated}"
                )

                paid_payment_id = payment_a_id if results[0] is None else payment_b_id
                unpaid_payment_id = (
                    payment_b_id if paid_payment_id == payment_a_id else payment_a_id
                )
                paid_payment = await service.get(paid_payment_id, tenant_id=scenario.tenant_id)
                unpaid_payment = await service.get(unpaid_payment_id, tenant_id=scenario.tenant_id)
                assert paid_payment.allocated_amount == Decimal("10000.00")
                assert paid_payment.unallocated_amount == Decimal("0.00")
                assert unpaid_payment.allocated_amount == Decimal("0.00")
                assert unpaid_payment.unallocated_amount == Decimal("10000.00")
        finally:
            await _cleanup_customer_scenario(scenario.tenant_id)

    async def test_one_payment_cannot_be_split_beyond_its_own_amount(self) -> None:
        # Payment = 10,000, split concurrently across two DIFFERENT
        # invoices (8,000 each, 7,000 requested from each) - each request
        # alone is within its own invoice's balance, but 7,000 + 7,000 =
        # 14,000 exceeds the payment's own 10,000. This isolates the
        # *payment*-side ceiling from the *invoice*-side ceiling exercised
        # by the test above.
        scenario = await _setup_customer_scenario(
            invoice_total=Decimal("8000.00"), payment_amounts=[Decimal("10000.00")]
        )
        (payment_id,) = scenario.payment_ids
        invoice_y_id = await _add_invoice(
            scenario.tenant_id, scenario.company_id, scenario.actor_id, Decimal("8000.00")
        )
        start_barrier = asyncio.Barrier(2)
        try:
            results = await asyncio.gather(
                _try_create_customer_allocation(
                    payment_id=payment_id,
                    invoice_id=scenario.invoice_id,
                    amount=Decimal("7000.00"),
                    tenant_id=scenario.tenant_id,
                    actor_id=scenario.actor_id,
                    start_barrier=start_barrier,
                ),
                _try_create_customer_allocation(
                    payment_id=payment_id,
                    invoice_id=invoice_y_id,
                    amount=Decimal("7000.00"),
                    tenant_id=scenario.tenant_id,
                    actor_id=scenario.actor_id,
                    start_barrier=start_barrier,
                ),
            )

            successes = [r for r in results if r is None]
            failures = [r for r in results if r is not None]
            assert len(successes) == 1
            assert len(failures) == 1
            failure = failures[0]
            assert isinstance(failure, PaymentAllocationAmountExceededError), (
                "expected the payment's own unallocated-amount ceiling to reject the second "
                f"request, got {type(failure)}: {failure}"
            )

            async with async_session_factory() as verify_session:
                service = PaymentService(verify_session)
                payment = await service.get(payment_id, tenant_id=scenario.tenant_id)
                assert payment.allocated_amount == Decimal("7000.00"), (
                    "a payment's allocated_amount must never exceed its own amount, even under "
                    f"concurrent requests - got {payment.allocated_amount}"
                )
                assert payment.unallocated_amount == Decimal("3000.00")
        finally:
            await _cleanup_customer_scenario(scenario.tenant_id)


class TestSupplierPaymentAllocationConcurrency:
    """Mirrors TestCustomerPaymentAllocationConcurrency exactly for the
    payable side (SupplierPayment -> SupplierPaymentAllocation ->
    PurchaseBill), which the Session 1 audit flagged as the more urgent
    half of this race: the supplier-payment allocation-totals recompute has
    no downstream negative-unallocated guard at all, unlike the invoice
    side's reconciliation module."""

    async def test_two_full_payments_cannot_both_consume_one_bill(self) -> None:
        scenario = await _setup_supplier_scenario(
            bill_total=Decimal("10000.00"),
            payment_amounts=[Decimal("10000.00"), Decimal("10000.00")],
        )
        payment_a_id, payment_b_id = scenario.payment_ids
        start_barrier = asyncio.Barrier(2)
        try:
            results = await asyncio.gather(
                _try_create_supplier_allocation(
                    supplier_payment_id=payment_a_id,
                    purchase_bill_id=scenario.purchase_bill_id,
                    amount=Decimal("10000.00"),
                    tenant_id=scenario.tenant_id,
                    actor_id=scenario.actor_id,
                    start_barrier=start_barrier,
                ),
                _try_create_supplier_allocation(
                    supplier_payment_id=payment_b_id,
                    purchase_bill_id=scenario.purchase_bill_id,
                    amount=Decimal("10000.00"),
                    tenant_id=scenario.tenant_id,
                    actor_id=scenario.actor_id,
                    start_barrier=start_barrier,
                ),
            )

            successes = [r for r in results if r is None]
            failures = [r for r in results if r is not None]
            assert len(successes) == 1, (
                "exactly one concurrent allocation must consume the purchase bill's balance - "
                f"got {len(successes)} successes"
            )
            assert len(failures) == 1
            failure = failures[0]
            assert isinstance(
                failure,
                (
                    SupplierPaymentPurchaseBillNotAllocatableError,
                    SupplierPaymentAllocationAmountExceededError,
                ),
            ), f"expected a typed business exception, got {type(failure)}: {failure}"

            async with async_session_factory() as verify_session:
                service = SupplierPaymentService(verify_session)
                purchase_bill = await service._purchase_service.get(
                    scenario.purchase_bill_id, tenant_id=scenario.tenant_id
                )
                assert purchase_bill.paid_amount == Decimal("10000.00")
                assert purchase_bill.balance_amount == Decimal("0.00")
                assert purchase_bill.status == PurchaseStatus.PAID

                total_allocated = await service._repo.sum_allocated_amount_by_purchase_bill(
                    scenario.purchase_bill_id, scenario.tenant_id
                )
                assert total_allocated == Decimal("10000.00"), (
                    "sum of allocations must never exceed the purchase bill total - "
                    f"got {total_allocated}"
                )
        finally:
            await _cleanup_supplier_scenario(scenario.tenant_id)

    async def test_one_supplier_payment_cannot_be_split_beyond_its_own_amount(self) -> None:
        scenario = await _setup_supplier_scenario(
            bill_total=Decimal("8000.00"), payment_amounts=[Decimal("10000.00")]
        )
        (supplier_payment_id,) = scenario.payment_ids
        bill_y_id = await _add_purchase_bill(
            scenario.tenant_id, scenario.supplier_id, scenario.actor_id, Decimal("8000.00")
        )
        start_barrier = asyncio.Barrier(2)
        try:
            results = await asyncio.gather(
                _try_create_supplier_allocation(
                    supplier_payment_id=supplier_payment_id,
                    purchase_bill_id=scenario.purchase_bill_id,
                    amount=Decimal("7000.00"),
                    tenant_id=scenario.tenant_id,
                    actor_id=scenario.actor_id,
                    start_barrier=start_barrier,
                ),
                _try_create_supplier_allocation(
                    supplier_payment_id=supplier_payment_id,
                    purchase_bill_id=bill_y_id,
                    amount=Decimal("7000.00"),
                    tenant_id=scenario.tenant_id,
                    actor_id=scenario.actor_id,
                    start_barrier=start_barrier,
                ),
            )

            successes = [r for r in results if r is None]
            failures = [r for r in results if r is not None]
            assert len(successes) == 1
            assert len(failures) == 1
            failure = failures[0]
            assert isinstance(failure, SupplierPaymentAllocationAmountExceededError), (
                "expected the payment's own unallocated-amount ceiling to reject the second "
                f"request, got {type(failure)}: {failure}"
            )

            async with async_session_factory() as verify_session:
                service = SupplierPaymentService(verify_session)
                supplier_payment = await service.get(
                    supplier_payment_id, tenant_id=scenario.tenant_id
                )
                assert supplier_payment.allocated_amount == Decimal("7000.00"), (
                    "a supplier payment's allocated_amount must never exceed its own amount, "
                    f"even under concurrent requests - got {supplier_payment.allocated_amount}"
                )
                assert supplier_payment.unallocated_amount == Decimal("3000.00")
        finally:
            await _cleanup_supplier_scenario(scenario.tenant_id)
