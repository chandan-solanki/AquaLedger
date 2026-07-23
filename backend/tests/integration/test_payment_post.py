import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import hash_password
from app.modules.boats.models import Boat
from app.modules.companies.models import Company
from app.modules.fish.models import Fish
from app.modules.invoices.schemas import InvoiceCreateRequest, InvoiceItemCreateRequest
from app.modules.invoices.service import InvoiceService
from app.modules.payments.constants import PaymentStatus
from app.modules.payments.exceptions import (
    PaymentAllocationPaymentNotDraftError,
    PaymentNoAllocationsError,
    PaymentNotDraftError,
    PaymentNotFoundError,
)
from app.modules.payments.models import Payment
from app.modules.payments.schemas import (
    PaymentAllocationCreateRequest,
    PaymentAllocationUpdateRequest,
    PaymentCreateRequest,
    PaymentUpdateRequest,
)
from app.modules.payments.service import PaymentService
from app.modules.trip_catches.models import TripCatch
from app.modules.trips.constants import TripType
from app.modules.trips.models import Trip

_INVOICE_DATE = date(2026, 7, 22)
_PAYMENT_DATE = date(2026, 7, 23)
_LANDING_DATE = date(2026, 6, 20)


@pytest.fixture
def payment_service(db_session: AsyncSession) -> PaymentService:
    return PaymentService(db_session)


@pytest.fixture
def invoice_service(db_session: AsyncSession) -> InvoiceService:
    return InvoiceService(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - keeps every assertion independent of
    whatever else exists in the seeded default tenant."""
    tenant = Tenant(
        name="Payment Post Test Tenant", slug=f"payment-post-test-{uuid.uuid4().hex[:8]}"
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant.id


@pytest.fixture
async def actor_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    """created_by/updated_by are real FKs to users.id, so service calls
    (unlike HTTP-level tests) need an actual user row."""
    user = User(
        tenant_id=tenant_id,
        email=f"post-{uuid.uuid4().hex[:8]}@fisherp.local",
        username=f"post-{uuid.uuid4().hex[:8]}",
        password_hash=hash_password("Whatever@123"),
        full_name="Post Test User",
        status=AccountStatus.ACTIVE,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user.id


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


async def _make_boat(
    db_session: AsyncSession, tenant_id: uuid.UUID, company_id: uuid.UUID, **overrides: Any
) -> Boat:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "company_id": company_id,
        "code": f"B-{uuid.uuid4().hex[:8]}",
        "name": f"Boat {uuid.uuid4().hex[:8]}",
        "registration_number": f"REG-{uuid.uuid4().hex[:8]}",
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
        "departure_datetime": datetime(2026, 6, 1, 4, 0, tzinfo=UTC),
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
        "available_quantity": Decimal("100.000"),
        "sold_quantity": Decimal("0.000"),
        "waste_quantity": Decimal("0.000"),
        "landing_date": _LANDING_DATE,
    }
    defaults.update(overrides)
    trip_catch = TripCatch(**defaults)
    db_session.add(trip_catch)
    await db_session.commit()
    return trip_catch


async def _issued_invoice(
    invoice_service: InvoiceService,
    db_session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    company_id: uuid.UUID,
    actor_id: uuid.UUID,
    quantity: Decimal = Decimal("10.000"),
    rate: Decimal = Decimal("100.0000"),
) -> Any:
    """A fully issued invoice with a known balance_amount (quantity x rate,
    no tax/discount) - the default 10 x 100 = 1000.00, provisioning its own
    boat/trip/fish/trip-catch chain."""
    boat = await _make_boat(db_session, tenant_id, company_id)
    trip = await _make_trip(db_session, tenant_id, boat.id)
    fish = await _make_fish(db_session, tenant_id)
    trip_catch = await _make_trip_catch(db_session, tenant_id, trip.id, fish.id)

    invoice = await invoice_service.create(
        InvoiceCreateRequest(company_id=company_id, invoice_date=_INVOICE_DATE),
        tenant_id=tenant_id,
        actor_id=actor_id,
    )
    await invoice_service.add_item(
        invoice.id,
        InvoiceItemCreateRequest(
            trip_catch_id=trip_catch.id,
            fish_id=fish.id,
            quantity=quantity,
            unit="kg",
            rate=rate,
        ),
        tenant_id=tenant_id,
        actor_id=actor_id,
    )
    return await invoice_service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)


async def _draft_payment_with_allocation(
    payment_service: PaymentService,
    *,
    tenant_id: uuid.UUID,
    company_id: uuid.UUID,
    invoice_id: uuid.UUID,
    actor_id: uuid.UUID,
    amount: Decimal = Decimal("1000.00"),
    allocated_amount: Decimal = Decimal("1000.00"),
) -> Any:
    payment = await payment_service.create(
        PaymentCreateRequest(
            company_id=company_id,
            payment_date=_PAYMENT_DATE,
            payment_method="cheque",
            amount=amount,
        ),
        tenant_id=tenant_id,
        actor_id=actor_id,
    )
    await payment_service.create_allocation(
        payment.id,
        PaymentAllocationCreateRequest(invoice_id=invoice_id, allocated_amount=allocated_amount),
        tenant_id=tenant_id,
        actor_id=actor_id,
    )
    return payment


class TestSuccessfulPost:
    async def test_transitions_draft_to_posted(
        self,
        payment_service: PaymentService,
        invoice_service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _issued_invoice(
            invoice_service,
            db_session,
            tenant_id=tenant_id,
            company_id=company_id,
            actor_id=actor_id,
        )
        payment = await _draft_payment_with_allocation(
            payment_service,
            tenant_id=tenant_id,
            company_id=company_id,
            invoice_id=invoice.id,
            actor_id=actor_id,
        )

        posted = await payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        assert posted.status == PaymentStatus.POSTED
        assert posted.payment_number == "PAY/2026-27/00001"
        assert posted.allocated_amount == Decimal("1000.00")
        assert posted.unallocated_amount == Decimal("0.00")

    async def test_second_payment_in_the_same_fiscal_year_gets_the_next_number(
        self,
        payment_service: PaymentService,
        invoice_service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice_a = await _issued_invoice(
            invoice_service,
            db_session,
            tenant_id=tenant_id,
            company_id=company_id,
            actor_id=actor_id,
        )
        payment_a = await _draft_payment_with_allocation(
            payment_service,
            tenant_id=tenant_id,
            company_id=company_id,
            invoice_id=invoice_a.id,
            actor_id=actor_id,
        )
        posted_a = await payment_service.post(payment_a.id, tenant_id=tenant_id, actor_id=actor_id)
        assert posted_a.payment_number == "PAY/2026-27/00001"

        invoice_b = await _issued_invoice(
            invoice_service,
            db_session,
            tenant_id=tenant_id,
            company_id=company_id,
            actor_id=actor_id,
        )
        payment_b = await _draft_payment_with_allocation(
            payment_service,
            tenant_id=tenant_id,
            company_id=company_id,
            invoice_id=invoice_b.id,
            actor_id=actor_id,
        )
        posted_b = await payment_service.post(payment_b.id, tenant_id=tenant_id, actor_id=actor_id)
        assert posted_b.payment_number == "PAY/2026-27/00002"

    async def test_partial_allocation_still_posts_with_the_correct_totals(
        self,
        payment_service: PaymentService,
        invoice_service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _issued_invoice(
            invoice_service,
            db_session,
            tenant_id=tenant_id,
            company_id=company_id,
            actor_id=actor_id,
        )
        payment = await _draft_payment_with_allocation(
            payment_service,
            tenant_id=tenant_id,
            company_id=company_id,
            invoice_id=invoice.id,
            actor_id=actor_id,
            amount=Decimal("1000.00"),
            allocated_amount=Decimal("400.00"),
        )

        posted = await payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        assert posted.allocated_amount == Decimal("400.00")
        assert posted.unallocated_amount == Decimal("600.00")

    async def test_does_not_touch_invoice_or_company_financials(
        self,
        payment_service: PaymentService,
        invoice_service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        """Session 4's outstanding engine already keeps Invoice.paid_amount/
        balance_amount/status and Company.outstanding_amount correct as of
        every allocation change made while the payment was draft - post()
        must leave them exactly as they were."""
        invoice = await _issued_invoice(
            invoice_service,
            db_session,
            tenant_id=tenant_id,
            company_id=company_id,
            actor_id=actor_id,
        )
        payment = await _draft_payment_with_allocation(
            payment_service,
            tenant_id=tenant_id,
            company_id=company_id,
            invoice_id=invoice.id,
            actor_id=actor_id,
        )
        before_invoice = await invoice_service.get(invoice.id, tenant_id=tenant_id)
        before_company_row = (
            await db_session.execute(select(Company).where(Company.id == company_id))
        ).scalar_one()
        before_outstanding = before_company_row.outstanding_amount

        await payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        after_invoice = await invoice_service.get(invoice.id, tenant_id=tenant_id)
        after_company_row = (
            await db_session.execute(select(Company).where(Company.id == company_id))
        ).scalar_one()
        assert after_invoice.status == before_invoice.status
        assert after_invoice.paid_amount == before_invoice.paid_amount
        assert after_invoice.balance_amount == before_invoice.balance_amount
        assert after_company_row.outstanding_amount == before_outstanding


class TestDoublePost:
    async def test_posting_an_already_posted_payment_raises_not_draft(
        self,
        payment_service: PaymentService,
        invoice_service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _issued_invoice(
            invoice_service,
            db_session,
            tenant_id=tenant_id,
            company_id=company_id,
            actor_id=actor_id,
        )
        payment = await _draft_payment_with_allocation(
            payment_service,
            tenant_id=tenant_id,
            company_id=company_id,
            invoice_id=invoice.id,
            actor_id=actor_id,
        )
        await payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(PaymentNotDraftError):
            await payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

    async def test_double_post_does_not_assign_a_second_number(
        self,
        payment_service: PaymentService,
        invoice_service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _issued_invoice(
            invoice_service,
            db_session,
            tenant_id=tenant_id,
            company_id=company_id,
            actor_id=actor_id,
        )
        payment = await _draft_payment_with_allocation(
            payment_service,
            tenant_id=tenant_id,
            company_id=company_id,
            invoice_id=invoice.id,
            actor_id=actor_id,
        )
        posted = await payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(PaymentNotDraftError):
            await payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        refetched = await payment_service.get(payment.id, tenant_id=tenant_id)
        assert refetched.payment_number == posted.payment_number

    async def test_cannot_post_a_cancelled_payment(
        self,
        payment_service: PaymentService,
        invoice_service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _issued_invoice(
            invoice_service,
            db_session,
            tenant_id=tenant_id,
            company_id=company_id,
            actor_id=actor_id,
        )
        payment = await _draft_payment_with_allocation(
            payment_service,
            tenant_id=tenant_id,
            company_id=company_id,
            invoice_id=invoice.id,
            actor_id=actor_id,
        )
        row = (
            await db_session.execute(select(Payment).where(Payment.id == payment.id))
        ).scalar_one()
        row.status = PaymentStatus.CANCELLED
        await db_session.commit()

        with pytest.raises(PaymentNotDraftError):
            await payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)


class TestEmptyAllocation:
    async def test_raises_no_allocations_for_a_draft_with_none(
        self,
        payment_service: PaymentService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        payment = await payment_service.create(
            PaymentCreateRequest(
                company_id=company_id,
                payment_date=_PAYMENT_DATE,
                payment_method="cheque",
                amount=Decimal("1000.00"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

        with pytest.raises(PaymentNoAllocationsError):
            await payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

    async def test_raises_no_allocations_when_the_only_allocation_was_removed(
        self,
        payment_service: PaymentService,
        invoice_service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _issued_invoice(
            invoice_service,
            db_session,
            tenant_id=tenant_id,
            company_id=company_id,
            actor_id=actor_id,
        )
        payment = await _draft_payment_with_allocation(
            payment_service,
            tenant_id=tenant_id,
            company_id=company_id,
            invoice_id=invoice.id,
            actor_id=actor_id,
        )
        allocations = await payment_service.list_allocations(payment.id, tenant_id=tenant_id)
        await payment_service.delete_allocation(payment.id, allocations[0].id, tenant_id=tenant_id)

        with pytest.raises(PaymentNoAllocationsError):
            await payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

    async def test_failed_post_leaves_the_payment_as_draft_without_a_number(
        self,
        payment_service: PaymentService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        payment = await payment_service.create(
            PaymentCreateRequest(
                company_id=company_id,
                payment_date=_PAYMENT_DATE,
                payment_method="cheque",
                amount=Decimal("1000.00"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

        with pytest.raises(PaymentNoAllocationsError):
            await payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        refetched = await payment_service.get(payment.id, tenant_id=tenant_id)
        assert refetched.status == PaymentStatus.DRAFT
        assert refetched.payment_number is None


class TestRollbackBehaviour:
    async def test_a_failed_post_does_not_leak_a_sequence_number(
        self,
        payment_service: PaymentService,
        invoice_service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        """A payment number is only ever generated after every validation
        passes (post()'s step 8 comes after steps 4/5/7) - a failed attempt
        must never punch a hole in the sequence."""
        payment = await payment_service.create(
            PaymentCreateRequest(
                company_id=company_id,
                payment_date=_PAYMENT_DATE,
                payment_method="cheque",
                amount=Decimal("1000.00"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        with pytest.raises(PaymentNoAllocationsError):
            await payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        invoice = await _issued_invoice(
            invoice_service,
            db_session,
            tenant_id=tenant_id,
            company_id=company_id,
            actor_id=actor_id,
        )
        good_payment = await _draft_payment_with_allocation(
            payment_service,
            tenant_id=tenant_id,
            company_id=company_id,
            invoice_id=invoice.id,
            actor_id=actor_id,
        )
        posted = await payment_service.post(good_payment.id, tenant_id=tenant_id, actor_id=actor_id)

        # The failed attempt above must not have consumed sequence number 1.
        assert posted.payment_number == "PAY/2026-27/00001"

    async def test_failed_post_rolls_back_and_the_payment_remains_editable(
        self,
        payment_service: PaymentService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        payment = await payment_service.create(
            PaymentCreateRequest(
                company_id=company_id,
                payment_date=_PAYMENT_DATE,
                payment_method="cheque",
                amount=Decimal("1000.00"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        with pytest.raises(PaymentNoAllocationsError):
            await payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        # A draft payment is still editable after a failed post attempt -
        # proof the explicit rollback didn't leave the session/transaction
        # in a broken state.
        updated = await payment_service.update(
            payment.id,
            PaymentUpdateRequest(remarks="Still editable"),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        assert updated.remarks == "Still editable"


class TestImmutabilityAfterPost:
    async def test_posted_payment_cannot_be_updated(
        self,
        payment_service: PaymentService,
        invoice_service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _issued_invoice(
            invoice_service,
            db_session,
            tenant_id=tenant_id,
            company_id=company_id,
            actor_id=actor_id,
        )
        payment = await _draft_payment_with_allocation(
            payment_service,
            tenant_id=tenant_id,
            company_id=company_id,
            invoice_id=invoice.id,
            actor_id=actor_id,
        )
        await payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(PaymentNotDraftError):
            await payment_service.update(
                payment.id,
                PaymentUpdateRequest(remarks="Trying to edit"),
                tenant_id=tenant_id,
                actor_id=actor_id,
            )

    async def test_posted_payment_cannot_be_deleted(
        self,
        payment_service: PaymentService,
        invoice_service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _issued_invoice(
            invoice_service,
            db_session,
            tenant_id=tenant_id,
            company_id=company_id,
            actor_id=actor_id,
        )
        payment = await _draft_payment_with_allocation(
            payment_service,
            tenant_id=tenant_id,
            company_id=company_id,
            invoice_id=invoice.id,
            actor_id=actor_id,
        )
        await payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(PaymentNotDraftError):
            await payment_service.delete(payment.id, tenant_id=tenant_id, actor_id=actor_id)

    async def test_posted_payment_allocations_cannot_be_created_updated_or_deleted(
        self,
        payment_service: PaymentService,
        invoice_service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _issued_invoice(
            invoice_service,
            db_session,
            tenant_id=tenant_id,
            company_id=company_id,
            actor_id=actor_id,
        )
        other_invoice = await _issued_invoice(
            invoice_service,
            db_session,
            tenant_id=tenant_id,
            company_id=company_id,
            actor_id=actor_id,
        )
        payment = await _draft_payment_with_allocation(
            payment_service,
            tenant_id=tenant_id,
            company_id=company_id,
            invoice_id=invoice.id,
            actor_id=actor_id,
        )
        allocations = await payment_service.list_allocations(payment.id, tenant_id=tenant_id)
        allocation_id = allocations[0].id
        await payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(PaymentAllocationPaymentNotDraftError):
            await payment_service.create_allocation(
                payment.id,
                PaymentAllocationCreateRequest(
                    invoice_id=other_invoice.id, allocated_amount=Decimal("1.00")
                ),
                tenant_id=tenant_id,
                actor_id=actor_id,
            )

        with pytest.raises(PaymentAllocationPaymentNotDraftError):
            await payment_service.update_allocation(
                payment.id,
                allocation_id,
                PaymentAllocationUpdateRequest(allocated_amount=Decimal("1.00")),
                tenant_id=tenant_id,
            )

        with pytest.raises(PaymentAllocationPaymentNotDraftError):
            await payment_service.delete_allocation(payment.id, allocation_id, tenant_id=tenant_id)

    async def test_posting_belonging_to_another_tenant_is_not_found(
        self,
        payment_service: PaymentService,
        tenant_id: uuid.UUID,
    ) -> None:
        with pytest.raises(PaymentNotFoundError):
            await payment_service.post(uuid.uuid4(), tenant_id=tenant_id, actor_id=uuid.uuid4())
