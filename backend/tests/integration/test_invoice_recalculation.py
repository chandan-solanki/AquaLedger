import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import hash_password
from app.modules.boats.models import Boat
from app.modules.companies.models import Company
from app.modules.fish.models import Fish
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
        name="Invoice Recalc Test Tenant", slug=f"invoice-recalc-test-{uuid.uuid4().hex[:8]}"
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant.id


@pytest.fixture
async def actor_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    """created_by/updated_by are real FKs to users.id, so InvoiceService
    calls (unlike the repository-only tests) need an actual user row."""
    user = User(
        tenant_id=tenant_id,
        email=f"recalc-{uuid.uuid4().hex[:8]}@fisherp.local",
        username=f"recalc-{uuid.uuid4().hex[:8]}",
        password_hash=hash_password("Whatever@123"),
        full_name="Recalc Test User",
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


async def _second_trip_catch(
    db_session: AsyncSession, tenant_id: uuid.UUID, trip_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID]:
    """A distinct fish + trip catch pair, for tests with more than one item."""
    fish = await _make_fish(db_session, tenant_id)
    trip_catch = await _make_trip_catch(db_session, tenant_id, trip_id, fish.id)
    return fish.id, trip_catch.id


class TestRecalculateAfterAddItem:
    async def test_creating_invoice_with_charges_totals_immediately(
        self,
        service: InvoiceService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await service.create(
            InvoiceCreateRequest(
                company_id=company_id,
                invoice_date=_INVOICE_DATE,
                transport_charge=Decimal("250.00"),
                other_charge=Decimal("10.00"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        assert invoice.subtotal == Decimal("0.00")
        assert invoice.total_amount == Decimal("260.00")
        assert invoice.balance_amount == Decimal("260.00")

    async def test_adding_first_item_sets_line_and_invoice_totals(
        self,
        service: InvoiceService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await service.create(
            InvoiceCreateRequest(company_id=company_id, invoice_date=_INVOICE_DATE),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

        item = await service.add_item(
            invoice.id,
            InvoiceItemCreateRequest(
                trip_catch_id=trip_catch_id,
                fish_id=fish_id,
                quantity=Decimal("50.000"),
                unit="kg",
                rate=Decimal("450.0000"),
                tax_rate=Decimal("5.00"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        assert item.taxable_amount == Decimal("22500.00")
        assert item.tax_amount == Decimal("1125.00")
        assert item.line_total == Decimal("23625.00")

        refetched = await service.get(invoice.id, tenant_id=tenant_id)
        assert refetched.subtotal == Decimal("23625.00")
        assert refetched.taxable_amount == Decimal("22500.00")
        assert refetched.tax_amount == Decimal("1125.00")
        assert refetched.total_amount == Decimal("23625.00")
        assert refetched.balance_amount == Decimal("23625.00")

    async def test_adding_second_item_sums_both_into_invoice_totals(
        self,
        service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        trip_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await service.create(
            InvoiceCreateRequest(company_id=company_id, invoice_date=_INVOICE_DATE),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        await service.add_item(
            invoice.id,
            InvoiceItemCreateRequest(
                trip_catch_id=trip_catch_id,
                fish_id=fish_id,
                quantity=Decimal("10"),
                unit="kg",
                rate=Decimal("100"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

        other_fish_id, other_trip_catch_id = await _second_trip_catch(
            db_session, tenant_id, trip_id
        )
        await service.add_item(
            invoice.id,
            InvoiceItemCreateRequest(
                trip_catch_id=other_trip_catch_id,
                fish_id=other_fish_id,
                quantity=Decimal("5"),
                unit="kg",
                rate=Decimal("50"),
                discount_percent=Decimal("10"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

        # item 1: 10*100=1000, item 2: 5*50=250 - 10% (25) = 225
        refetched = await service.get(invoice.id, tenant_id=tenant_id)
        assert refetched.subtotal == Decimal("1225.00")
        assert refetched.discount_amount == Decimal("25.00")
        assert refetched.total_amount == Decimal("1225.00")


class TestRecalculateAfterUpdateItem:
    async def test_updating_quantity_recalculates_item_and_invoice(
        self,
        service: InvoiceService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await service.create(
            InvoiceCreateRequest(company_id=company_id, invoice_date=_INVOICE_DATE),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        item = await service.add_item(
            invoice.id,
            InvoiceItemCreateRequest(
                trip_catch_id=trip_catch_id,
                fish_id=fish_id,
                quantity=Decimal("10"),
                unit="kg",
                rate=Decimal("100"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        assert item.line_total == Decimal("1000.00")

        updated = await service.update_item(
            invoice.id,
            item.id,
            InvoiceItemUpdateRequest(quantity=Decimal("20")),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        assert updated.line_total == Decimal("2000.00")

        refetched = await service.get(invoice.id, tenant_id=tenant_id)
        assert refetched.subtotal == Decimal("2000.00")
        assert refetched.total_amount == Decimal("2000.00")

    async def test_updating_rate_only_still_recalculates_invoice(
        self,
        service: InvoiceService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await service.create(
            InvoiceCreateRequest(company_id=company_id, invoice_date=_INVOICE_DATE),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        item = await service.add_item(
            invoice.id,
            InvoiceItemCreateRequest(
                trip_catch_id=trip_catch_id,
                fish_id=fish_id,
                quantity=Decimal("10"),
                unit="kg",
                rate=Decimal("100"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

        await service.update_item(
            invoice.id,
            item.id,
            InvoiceItemUpdateRequest(rate=Decimal("150")),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

        refetched = await service.get(invoice.id, tenant_id=tenant_id)
        assert refetched.total_amount == Decimal("1500.00")


class TestRecalculateAfterDeleteItem:
    async def test_deleting_one_of_two_items_recalculates_down(
        self,
        service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        trip_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await service.create(
            InvoiceCreateRequest(company_id=company_id, invoice_date=_INVOICE_DATE),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        item_a = await service.add_item(
            invoice.id,
            InvoiceItemCreateRequest(
                trip_catch_id=trip_catch_id,
                fish_id=fish_id,
                quantity=Decimal("10"),
                unit="kg",
                rate=Decimal("100"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        other_fish_id, other_trip_catch_id = await _second_trip_catch(
            db_session, tenant_id, trip_id
        )
        await service.add_item(
            invoice.id,
            InvoiceItemCreateRequest(
                trip_catch_id=other_trip_catch_id,
                fish_id=other_fish_id,
                quantity=Decimal("5"),
                unit="kg",
                rate=Decimal("50"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

        before = await service.get(invoice.id, tenant_id=tenant_id)
        assert before.subtotal == Decimal("1250.00")

        await service.delete_item(invoice.id, item_a.id, tenant_id=tenant_id, actor_id=actor_id)

        after = await service.get(invoice.id, tenant_id=tenant_id)
        assert after.subtotal == Decimal("250.00")
        assert after.total_amount == Decimal("250.00")

    async def test_deleting_the_only_item_zeroes_the_invoice_totals(
        self,
        service: InvoiceService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await service.create(
            InvoiceCreateRequest(
                company_id=company_id,
                invoice_date=_INVOICE_DATE,
                transport_charge=Decimal("50.00"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        item = await service.add_item(
            invoice.id,
            InvoiceItemCreateRequest(
                trip_catch_id=trip_catch_id,
                fish_id=fish_id,
                quantity=Decimal("10"),
                unit="kg",
                rate=Decimal("100"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

        await service.delete_item(invoice.id, item.id, tenant_id=tenant_id, actor_id=actor_id)

        after = await service.get(invoice.id, tenant_id=tenant_id)
        assert after.subtotal == Decimal("0.00")
        # transport_charge still contributes even with zero items.
        assert after.total_amount == Decimal("50.00")


class TestRecalculateAfterInvoiceChargeUpdate:
    async def test_updating_transport_charge_recalculates_total_only(
        self,
        service: InvoiceService,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await service.create(
            InvoiceCreateRequest(company_id=company_id, invoice_date=_INVOICE_DATE),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        item = await service.add_item(
            invoice.id,
            InvoiceItemCreateRequest(
                trip_catch_id=trip_catch_id,
                fish_id=fish_id,
                quantity=Decimal("10"),
                unit="kg",
                rate=Decimal("100"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

        updated = await service.update(
            invoice.id,
            InvoiceUpdateRequest(transport_charge=Decimal("75.00")),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        assert updated.subtotal == Decimal("1000.00")  # item totals untouched
        assert updated.total_amount == Decimal("1075.00")

        item_after = await service.list_items(invoice.id, tenant_id=tenant_id, q=None)
        assert item_after[0].id == item.id
        assert item_after[0].line_total == Decimal("1000.00")  # unchanged by the charge update


class TestSequentialMutationsStayCorrect:
    async def test_add_update_add_delete_sequence_keeps_totals_correct(
        self,
        service: InvoiceService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
        trip_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await service.create(
            InvoiceCreateRequest(
                company_id=company_id,
                invoice_date=_INVOICE_DATE,
                transport_charge=Decimal("20.00"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

        item_a = await service.add_item(
            invoice.id,
            InvoiceItemCreateRequest(
                trip_catch_id=trip_catch_id,
                fish_id=fish_id,
                quantity=Decimal("10"),
                unit="kg",
                rate=Decimal("100"),
                tax_rate=Decimal("10"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        # subtotal = 1000 + 100 tax = 1100; total = 1100 + 20 = 1120
        step1 = await service.get(invoice.id, tenant_id=tenant_id)
        assert step1.total_amount == Decimal("1120.00")

        await service.update_item(
            invoice.id,
            item_a.id,
            InvoiceItemUpdateRequest(quantity=Decimal("5")),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        # subtotal = 500 + 50 tax = 550; total = 550 + 20 = 570
        step2 = await service.get(invoice.id, tenant_id=tenant_id)
        assert step2.total_amount == Decimal("570.00")

        other_fish_id, other_trip_catch_id = await _second_trip_catch(
            db_session, tenant_id, trip_id
        )
        item_b = await service.add_item(
            invoice.id,
            InvoiceItemCreateRequest(
                trip_catch_id=other_trip_catch_id,
                fish_id=other_fish_id,
                quantity=Decimal("2"),
                unit="kg",
                rate=Decimal("50"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        # + 100 -> subtotal 650; total 670
        step3 = await service.get(invoice.id, tenant_id=tenant_id)
        assert step3.total_amount == Decimal("670.00")

        await service.delete_item(invoice.id, item_a.id, tenant_id=tenant_id, actor_id=actor_id)
        # only item_b remains: subtotal 100; total 120
        step4 = await service.get(invoice.id, tenant_id=tenant_id)
        assert step4.subtotal == Decimal("100.00")
        assert step4.total_amount == Decimal("120.00")

        remaining_items = await service.list_items(invoice.id, tenant_id=tenant_id, q=None)
        assert [i.id for i in remaining_items] == [item_b.id]
