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
from app.modules.companies.constants import CompanyStatus
from app.modules.companies.models import Company
from app.modules.fish.models import Fish
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.exceptions import (
    InvoiceCompanyInactiveError,
    InvoiceEmptyError,
    InvoiceInsufficientInventoryError,
    InvoiceNotDraftError,
)
from app.modules.invoices.models import Invoice, InvoiceItem
from app.modules.invoices.schemas import (
    InvoiceCreateRequest,
    InvoiceItemCreateRequest,
    InvoiceItemUpdateRequest,
    InvoiceUpdateRequest,
)
from app.modules.invoices.service import InvoiceService
from app.modules.trip_catches.models import TripCatch
from app.modules.trips.constants import TripType
from app.modules.trips.models import Trip

_INVOICE_DATE = date(2026, 7, 22)
_LANDING_DATE = date(2026, 6, 20)


@pytest.fixture
def service(db_session: AsyncSession) -> InvoiceService:
    return InvoiceService(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - keeps every assertion independent of
    whatever else exists in the seeded default tenant."""
    tenant = Tenant(
        name="Invoice Issue Test Tenant", slug=f"invoice-issue-test-{uuid.uuid4().hex[:8]}"
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant.id


@pytest.fixture
async def actor_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    """created_by/updated_by are real FKs to users.id, so InvoiceService
    calls (unlike HTTP-level tests) need an actual user row."""
    user = User(
        tenant_id=tenant_id,
        email=f"issue-{uuid.uuid4().hex[:8]}@fisherp.local",
        username=f"issue-{uuid.uuid4().hex[:8]}",
        password_hash=hash_password("Whatever@123"),
        full_name="Issue Test User",
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


@pytest.fixture
async def company_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    company = await _make_company(db_session, tenant_id)
    return company.id


@pytest.fixture
async def boat_id(
    db_session: AsyncSession, tenant_id: uuid.UUID, company_id: uuid.UUID
) -> uuid.UUID:
    boat = await _make_boat(db_session, tenant_id, company_id)
    return boat.id


@pytest.fixture
async def trip_id(db_session: AsyncSession, tenant_id: uuid.UUID, boat_id: uuid.UUID) -> uuid.UUID:
    trip = await _make_trip(db_session, tenant_id, boat_id)
    return trip.id


@pytest.fixture
async def fish_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    fish = await _make_fish(db_session, tenant_id)
    return fish.id


@pytest.fixture
async def trip_catch_id(
    db_session: AsyncSession, tenant_id: uuid.UUID, trip_id: uuid.UUID, fish_id: uuid.UUID
) -> uuid.UUID:
    trip_catch = await _make_trip_catch(db_session, tenant_id, trip_id, fish_id)
    return trip_catch.id


async def _draft_invoice_with_item(
    service: InvoiceService,
    *,
    tenant_id: uuid.UUID,
    company_id: uuid.UUID,
    fish_id: uuid.UUID,
    trip_catch_id: uuid.UUID,
    actor_id: uuid.UUID,
    quantity: Decimal = Decimal("50.000"),
    rate: Decimal = Decimal("450.0000"),
    tax_rate: Decimal = Decimal("5.00"),
    transport_charge: Decimal = Decimal("0"),
) -> Any:
    invoice = await service.create(
        InvoiceCreateRequest(
            company_id=company_id, invoice_date=_INVOICE_DATE, transport_charge=transport_charge
        ),
        tenant_id=tenant_id,
        actor_id=actor_id,
    )
    await service.add_item(
        invoice.id,
        InvoiceItemCreateRequest(
            trip_catch_id=trip_catch_id,
            fish_id=fish_id,
            quantity=quantity,
            unit="kg",
            rate=rate,
            tax_rate=tax_rate,
        ),
        tenant_id=tenant_id,
        actor_id=actor_id,
    )
    return invoice


class TestSuccessfulIssue:
    async def test_transitions_draft_to_issued(
        self,
        service: InvoiceService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_id,
            trip_catch_id=trip_catch_id,
            actor_id=actor_id,
        )

        issued = await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)

        assert issued.status == InvoiceStatus.ISSUED
        assert issued.invoice_number == "INV/2026-27/00001"

    async def test_issued_at_is_populated(
        self,
        service: InvoiceService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_id,
            trip_catch_id=trip_catch_id,
            actor_id=actor_id,
        )
        assert invoice.issued_at is None

        before = datetime.now(UTC)
        issued = await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)
        after = datetime.now(UTC)

        assert issued.issued_at is not None
        assert before <= issued.issued_at <= after

    async def test_second_invoice_in_the_same_fiscal_year_gets_the_next_number(
        self,
        service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        trip_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        fish_a = await _make_fish(db_session, tenant_id)
        catch_a = await _make_trip_catch(db_session, tenant_id, trip_id, fish_a.id)
        invoice_a = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_a.id,
            trip_catch_id=catch_a.id,
            actor_id=actor_id,
        )
        issued_a = await service.issue(invoice_a.id, tenant_id=tenant_id, actor_id=actor_id)
        assert issued_a.invoice_number == "INV/2026-27/00001"

        fish_b = await _make_fish(db_session, tenant_id)
        catch_b = await _make_trip_catch(db_session, tenant_id, trip_id, fish_b.id)
        invoice_b = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_b.id,
            trip_catch_id=catch_b.id,
            actor_id=actor_id,
        )
        issued_b = await service.issue(invoice_b.id, tenant_id=tenant_id, actor_id=actor_id)
        assert issued_b.invoice_number == "INV/2026-27/00002"

    async def test_recalculates_totals_immediately_before_issue(
        self,
        service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        """Even if a line's stored total were somehow stale, issue() must
        never trust it - it always recomputes from quantity/rate/discount/
        tax immediately before issuing (ARCHITECTURE.md §13.3)."""
        invoice = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_id,
            trip_catch_id=trip_catch_id,
            actor_id=actor_id,
            quantity=Decimal("50.000"),
            rate=Decimal("450.0000"),
            tax_rate=Decimal("5.00"),
        )
        # Correct line_total is 23625.00 - corrupt it directly via the ORM,
        # bypassing the service entirely, to prove issue() doesn't trust it.
        result = await db_session.execute(
            select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
        )
        item = result.scalar_one()
        item.line_total = Decimal("1.00")
        await db_session.commit()

        issued = await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)

        assert issued.total_amount == Decimal("23625.00")
        assert issued.balance_amount == Decimal("23625.00")


class TestDoubleIssue:
    async def test_issuing_an_already_issued_invoice_raises_not_draft(
        self,
        service: InvoiceService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_id,
            trip_catch_id=trip_catch_id,
            actor_id=actor_id,
        )
        await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(InvoiceNotDraftError):
            await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)

    async def test_double_issue_does_not_double_deduct_inventory_or_double_credit_outstanding(
        self,
        service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_id,
            trip_catch_id=trip_catch_id,
            actor_id=actor_id,
            quantity=Decimal("50.000"),
        )
        issued = await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(InvoiceNotDraftError):
            await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)

        trip_catch_row = (
            await db_session.execute(select(TripCatch).where(TripCatch.id == trip_catch_id))
        ).scalar_one()
        assert trip_catch_row.available_quantity == Decimal("50.000")
        assert trip_catch_row.sold_quantity == Decimal("50.000")

        company_row = (
            await db_session.execute(select(Company).where(Company.id == company_id))
        ).scalar_one()
        assert company_row.outstanding_amount == issued.total_amount

    async def test_cannot_issue_a_cancelled_invoice(
        self,
        service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_id,
            trip_catch_id=trip_catch_id,
            actor_id=actor_id,
        )
        row = (
            await db_session.execute(select(Invoice).where(Invoice.id == invoice.id))
        ).scalar_one()
        row.status = InvoiceStatus.CANCELLED
        await db_session.commit()

        with pytest.raises(InvoiceNotDraftError):
            await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)


class TestEmptyInvoice:
    async def test_raises_empty_for_a_draft_with_no_items(
        self,
        service: InvoiceService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await service.create(
            InvoiceCreateRequest(company_id=company_id, invoice_date=_INVOICE_DATE),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

        with pytest.raises(InvoiceEmptyError):
            await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)

    async def test_raises_empty_when_the_only_item_was_deleted(
        self,
        service: InvoiceService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_id,
            trip_catch_id=trip_catch_id,
            actor_id=actor_id,
        )
        items = await service.list_items(invoice.id, tenant_id=tenant_id, q=None)
        await service.delete_item(invoice.id, items[0].id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(InvoiceEmptyError):
            await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)

    async def test_empty_invoice_is_not_left_mutated_after_the_failed_attempt(
        self,
        service: InvoiceService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await service.create(
            InvoiceCreateRequest(company_id=company_id, invoice_date=_INVOICE_DATE),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

        with pytest.raises(InvoiceEmptyError):
            await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)

        refetched = await service.get(invoice.id, tenant_id=tenant_id)
        assert refetched.status == InvoiceStatus.DRAFT
        assert refetched.invoice_number is None


class TestCompanyMustBeActive:
    async def test_raises_inactive_if_the_company_was_deactivated_after_the_invoice_was_drafted(
        self,
        service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_id,
            trip_catch_id=trip_catch_id,
            actor_id=actor_id,
        )
        company_row = (
            await db_session.execute(select(Company).where(Company.id == company_id))
        ).scalar_one()
        company_row.status = CompanyStatus.INACTIVE
        await db_session.commit()

        with pytest.raises(InvoiceCompanyInactiveError):
            await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)


class TestInsufficientInventory:
    async def test_raises_when_available_quantity_dropped_below_the_items_quantity_since_add(
        self,
        service: InvoiceService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        """A trip catch starts with 100.000 available. Two draft invoices
        each take a 60.000 item against it - both additions are individually
        valid (each is <= 100 available at add time). Issuing the first
        succeeds and drops availability to 40.000; issuing the second must
        then fail the revalidation under lock, even though it passed
        validation when the item was originally added."""
        invoice_a = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_id,
            trip_catch_id=trip_catch_id,
            actor_id=actor_id,
            quantity=Decimal("60.000"),
        )
        invoice_b = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_id,
            trip_catch_id=trip_catch_id,
            actor_id=actor_id,
            quantity=Decimal("60.000"),
        )

        await service.issue(invoice_a.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(InvoiceInsufficientInventoryError):
            await service.issue(invoice_b.id, tenant_id=tenant_id, actor_id=actor_id)

    async def test_failed_issue_leaves_the_invoice_as_draft_and_inventory_untouched(
        self,
        service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice_a = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_id,
            trip_catch_id=trip_catch_id,
            actor_id=actor_id,
            quantity=Decimal("60.000"),
        )
        invoice_b = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_id,
            trip_catch_id=trip_catch_id,
            actor_id=actor_id,
            quantity=Decimal("60.000"),
        )
        await service.issue(invoice_a.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(InvoiceInsufficientInventoryError):
            await service.issue(invoice_b.id, tenant_id=tenant_id, actor_id=actor_id)

        refetched_b = await service.get(invoice_b.id, tenant_id=tenant_id)
        assert refetched_b.status == InvoiceStatus.DRAFT
        assert refetched_b.invoice_number is None

        trip_catch_row = (
            await db_session.execute(select(TripCatch).where(TripCatch.id == trip_catch_id))
        ).scalar_one()
        # Only invoice_a's 60.000 deduction should be reflected - invoice_b's
        # failed attempt must not have deducted anything.
        assert trip_catch_row.available_quantity == Decimal("40.000")
        assert trip_catch_row.sold_quantity == Decimal("60.000")


class TestRollbackBehaviour:
    async def test_a_second_items_failure_rolls_back_the_first_items_already_applied_deduction(
        self,
        service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        trip_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        """One invoice with two items on two different trip catches: the
        first item's trip catch has plenty of inventory, the second's does
        not. Regardless of which item the deduction loop processes first
        (it's ordered by trip_catch_id for deadlock avoidance, not item
        order), the whole transaction must roll back together - the
        sufficient trip catch must not end up partially deducted."""
        plentiful_fish = await _make_fish(db_session, tenant_id)
        plentiful_catch = await _make_trip_catch(
            db_session, tenant_id, trip_id, plentiful_fish.id, available_quantity=Decimal("100.000")
        )
        plentiful_catch_id = plentiful_catch.id
        scarce_fish = await _make_fish(db_session, tenant_id)
        scarce_catch = await _make_trip_catch(
            db_session,
            tenant_id,
            trip_id,
            scarce_fish.id,
            quantity_caught=Decimal("5.000"),
            available_quantity=Decimal("5.000"),
        )
        scarce_catch_id = scarce_catch.id

        invoice = await service.create(
            InvoiceCreateRequest(company_id=company_id, invoice_date=_INVOICE_DATE),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        await service.add_item(
            invoice.id,
            InvoiceItemCreateRequest(
                trip_catch_id=plentiful_catch_id,
                fish_id=plentiful_fish.id,
                quantity=Decimal("10.000"),
                unit="kg",
                rate=Decimal("100.0000"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        await service.add_item(
            invoice.id,
            InvoiceItemCreateRequest(
                trip_catch_id=scarce_catch_id,
                fish_id=scarce_fish.id,
                quantity=Decimal("5.000"),
                unit="kg",
                rate=Decimal("100.0000"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        # Someone else consumes the scarce catch's inventory after the item
        # was added but before this invoice is issued.
        scarce_row = (
            await db_session.execute(select(TripCatch).where(TripCatch.id == scarce_catch_id))
        ).scalar_one()
        scarce_row.available_quantity = Decimal("0.000")
        scarce_row.sold_quantity = Decimal("5.000")
        await db_session.commit()

        with pytest.raises(InvoiceInsufficientInventoryError):
            await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)

        # issue()'s explicit rollback on failure expires every object in
        # this shared session's identity map (including plentiful_catch/
        # scarce_catch above) - re-query by the ids captured earlier rather
        # than touching those expired objects' attributes.
        plentiful_row = (
            await db_session.execute(select(TripCatch).where(TripCatch.id == plentiful_catch_id))
        ).scalar_one()
        assert plentiful_row.available_quantity == Decimal("100.000")
        assert plentiful_row.sold_quantity == Decimal("0.000")

        company_row = (
            await db_session.execute(select(Company).where(Company.id == company_id))
        ).scalar_one()
        assert company_row.outstanding_amount == Decimal("0.00")

        refetched = await service.get(invoice.id, tenant_id=tenant_id)
        assert refetched.status == InvoiceStatus.DRAFT
        assert refetched.invoice_number is None


class TestCompanyOutstandingUpdated:
    async def test_increases_outstanding_by_the_issued_total(
        self,
        service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_id,
            trip_catch_id=trip_catch_id,
            actor_id=actor_id,
            transport_charge=Decimal("250.00"),
        )

        issued = await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)

        company_row = (
            await db_session.execute(select(Company).where(Company.id == company_id))
        ).scalar_one()
        assert company_row.outstanding_amount == issued.total_amount
        assert issued.total_amount == Decimal("23875.00")

    async def test_accumulates_across_multiple_issued_invoices_for_the_same_company(
        self,
        service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        trip_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        fish_a = await _make_fish(db_session, tenant_id)
        catch_a = await _make_trip_catch(db_session, tenant_id, trip_id, fish_a.id)
        invoice_a = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_a.id,
            trip_catch_id=catch_a.id,
            actor_id=actor_id,
            quantity=Decimal("10.000"),
            rate=Decimal("100.0000"),
            tax_rate=Decimal("0"),
        )
        issued_a = await service.issue(invoice_a.id, tenant_id=tenant_id, actor_id=actor_id)

        fish_b = await _make_fish(db_session, tenant_id)
        catch_b = await _make_trip_catch(db_session, tenant_id, trip_id, fish_b.id)
        invoice_b = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_b.id,
            trip_catch_id=catch_b.id,
            actor_id=actor_id,
            quantity=Decimal("20.000"),
            rate=Decimal("100.0000"),
            tax_rate=Decimal("0"),
        )
        issued_b = await service.issue(invoice_b.id, tenant_id=tenant_id, actor_id=actor_id)

        company_row = (
            await db_session.execute(select(Company).where(Company.id == company_id))
        ).scalar_one()
        assert company_row.outstanding_amount == issued_a.total_amount + issued_b.total_amount
        assert company_row.outstanding_amount == Decimal("3000.00")


class TestInventoryUpdated:
    async def test_deducts_available_and_credits_sold_for_every_item(
        self,
        service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        trip_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        fish_a = await _make_fish(db_session, tenant_id)
        catch_a = await _make_trip_catch(
            db_session, tenant_id, trip_id, fish_a.id, available_quantity=Decimal("100.000")
        )
        fish_b = await _make_fish(db_session, tenant_id)
        catch_b = await _make_trip_catch(
            db_session,
            tenant_id,
            trip_id,
            fish_b.id,
            quantity_caught=Decimal("50.000"),
            available_quantity=Decimal("50.000"),
        )

        invoice = await service.create(
            InvoiceCreateRequest(company_id=company_id, invoice_date=_INVOICE_DATE),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        await service.add_item(
            invoice.id,
            InvoiceItemCreateRequest(
                trip_catch_id=catch_a.id,
                fish_id=fish_a.id,
                quantity=Decimal("30.000"),
                unit="kg",
                rate=Decimal("100.0000"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        await service.add_item(
            invoice.id,
            InvoiceItemCreateRequest(
                trip_catch_id=catch_b.id,
                fish_id=fish_b.id,
                quantity=Decimal("15.000"),
                unit="kg",
                rate=Decimal("100.0000"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

        await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)

        row_a = (
            await db_session.execute(select(TripCatch).where(TripCatch.id == catch_a.id))
        ).scalar_one()
        assert row_a.available_quantity == Decimal("70.000")
        assert row_a.sold_quantity == Decimal("30.000")

        row_b = (
            await db_session.execute(select(TripCatch).where(TripCatch.id == catch_b.id))
        ).scalar_one()
        assert row_b.available_quantity == Decimal("35.000")
        assert row_b.sold_quantity == Decimal("15.000")

    async def test_deducting_exactly_all_available_quantity_succeeds(
        self,
        service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_id,
            trip_catch_id=trip_catch_id,
            actor_id=actor_id,
            quantity=Decimal("100.000"),
        )

        await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)

        row = (
            await db_session.execute(select(TripCatch).where(TripCatch.id == trip_catch_id))
        ).scalar_one()
        assert row.available_quantity == Decimal("0.000")
        assert row.sold_quantity == Decimal("100.000")


class TestImmutabilityAfterIssue:
    async def test_issued_invoice_cannot_be_updated(
        self,
        service: InvoiceService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_id,
            trip_catch_id=trip_catch_id,
            actor_id=actor_id,
        )
        await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(InvoiceNotDraftError):
            await service.update(
                invoice.id,
                InvoiceUpdateRequest(remarks="Trying to edit"),
                tenant_id=tenant_id,
                actor_id=actor_id,
            )

    async def test_issued_invoice_cannot_be_deleted(
        self,
        service: InvoiceService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_id,
            trip_catch_id=trip_catch_id,
            actor_id=actor_id,
        )
        await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(InvoiceNotDraftError):
            await service.delete(invoice.id, tenant_id=tenant_id, actor_id=actor_id)

    async def test_issued_invoice_items_cannot_be_added_updated_or_deleted(
        self,
        service: InvoiceService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await _draft_invoice_with_item(
            service,
            tenant_id=tenant_id,
            company_id=company_id,
            fish_id=fish_id,
            trip_catch_id=trip_catch_id,
            actor_id=actor_id,
        )
        items = await service.list_items(invoice.id, tenant_id=tenant_id, q=None)
        item_id = items[0].id
        await service.issue(invoice.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(InvoiceNotDraftError):
            await service.add_item(
                invoice.id,
                InvoiceItemCreateRequest(
                    trip_catch_id=trip_catch_id,
                    fish_id=fish_id,
                    quantity=Decimal("1.000"),
                    unit="kg",
                    rate=Decimal("1.0000"),
                ),
                tenant_id=tenant_id,
                actor_id=actor_id,
            )

        with pytest.raises(InvoiceNotDraftError):
            await service.update_item(
                invoice.id,
                item_id,
                InvoiceItemUpdateRequest(quantity=Decimal("1.000")),
                tenant_id=tenant_id,
                actor_id=actor_id,
            )

        with pytest.raises(InvoiceNotDraftError):
            await service.delete_item(invoice.id, item_id, tenant_id=tenant_id, actor_id=actor_id)
