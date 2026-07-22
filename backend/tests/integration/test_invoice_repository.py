import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Tenant
from app.modules.boats.models import Boat
from app.modules.companies.models import Company
from app.modules.fish.models import Fish
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.models import Invoice, InvoiceItem, InvoiceSequence
from app.modules.invoices.repository import InvoiceRepository
from app.modules.trip_catches.models import TripCatch
from app.modules.trips.constants import TripType
from app.modules.trips.models import Trip

_INVOICE_DATE = date(2026, 7, 1)
_LANDING_DATE = date(2026, 6, 20)


@pytest.fixture
async def repo(db_session: AsyncSession) -> InvoiceRepository:
    return InvoiceRepository(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - the seeded default tenant may already carry
    invoices from manual/exploratory testing, which would silently pollute
    any count-based assertion here."""
    tenant = Tenant(
        name="Invoice Repo Test Tenant",
        slug=f"invoice-repo-test-{uuid.uuid4().hex[:8]}",
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
        "invoice_date": _INVOICE_DATE,
        "status": InvoiceStatus.DRAFT,
        "subtotal": Decimal("0"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("0"),
        "tax_amount": Decimal("0"),
        "transport_charge": Decimal("0"),
        "other_charge": Decimal("0"),
        "round_off": Decimal("0"),
        "total_amount": Decimal("0"),
        "paid_amount": Decimal("0"),
        "balance_amount": Decimal("0"),
    }
    defaults.update(overrides)
    invoice = Invoice(**defaults)
    db_session.add(invoice)
    await db_session.commit()
    return invoice


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


@pytest.fixture
async def invoice_id(
    db_session: AsyncSession, tenant_id: uuid.UUID, company_id: uuid.UUID
) -> uuid.UUID:
    invoice = await _make_invoice(db_session, tenant_id, company_id)
    return invoice.id


async def _make_invoice_item(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
    fish_id: uuid.UUID,
    trip_catch_id: uuid.UUID,
    *,
    line_number: int = 1,
    **overrides: Any,
) -> InvoiceItem:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "line_number": line_number,
        "fish_id": fish_id,
        "trip_catch_id": trip_catch_id,
        "quantity": Decimal("10.000"),
        "unit": "kg",
        "rate": Decimal("100.0000"),
        "discount_percent": Decimal("0"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("0"),
        "tax_rate": Decimal("0"),
        "tax_amount": Decimal("0"),
        "line_total": Decimal("0"),
    }
    defaults.update(overrides)
    item = InvoiceItem(**defaults)
    db_session.add(item)
    await db_session.commit()
    return item


class TestGetByIdForUpdate:
    """The Session 5 issue workflow's locked lookup - same scoping rules as
    get_by_id, plus a row lock. Functional correctness (does it find/scope
    the same way) is what's testable here; the actual lock's effect on a
    concurrent transaction isn't exercised by this single-session suite."""

    async def test_finds_invoice_in_own_tenant(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        invoice = await _make_invoice(db_session, tenant_id, company_id, remarks="Lockable")
        found = await repo.get_by_id_for_update(invoice.id, tenant_id)
        assert found is not None
        assert found.remarks == "Lockable"

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        invoice = await _make_invoice(db_session, tenant_id, company_id)
        assert await repo.get_by_id_for_update(invoice.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: InvoiceRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id_for_update(uuid.uuid4(), tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        invoice = await _make_invoice(
            db_session, tenant_id, company_id, deleted_at=datetime.now(UTC)
        )
        assert await repo.get_by_id_for_update(invoice.id, tenant_id) is None

    async def test_mutations_on_the_locked_row_persist_after_commit(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        invoice = await _make_invoice(db_session, tenant_id, company_id)
        locked = await repo.get_by_id_for_update(invoice.id, tenant_id)
        assert locked is not None
        locked.invoice_number = "INV/2026-27/00001"
        locked.status = InvoiceStatus.ISSUED
        await db_session.commit()

        refetched = await repo.get_by_id(invoice.id, tenant_id)
        assert refetched is not None
        assert refetched.invoice_number == "INV/2026-27/00001"
        assert refetched.status == InvoiceStatus.ISSUED


class TestSequenceRow:
    """The Session 5 issue workflow's invoice numbering counter
    (ARCHITECTURE.md §13.1) - ensure_sequence_row (`INSERT ... ON CONFLICT
    DO NOTHING`) followed by get_sequence_for_update (`SELECT ... FOR
    UPDATE`)."""

    async def test_ensure_creates_a_row_starting_at_zero(
        self, repo: InvoiceRepository, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "INV", "2026-27")
        sequence = await repo.get_sequence_for_update(tenant_id, "INV", "2026-27")
        assert sequence.last_number == 0

    async def test_ensure_is_idempotent_and_does_not_reset_an_existing_counter(
        self, repo: InvoiceRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "INV", "2026-27")
        sequence = await repo.get_sequence_for_update(tenant_id, "INV", "2026-27")
        sequence.last_number += 1
        await db_session.commit()

        # A second ensure_sequence_row call (as issue() makes on every
        # invoice, not just the first per fiscal year) must not clobber the
        # counter back to zero.
        await repo.ensure_sequence_row(tenant_id, "INV", "2026-27")
        relocked = await repo.get_sequence_for_update(tenant_id, "INV", "2026-27")
        assert relocked.last_number == 1

    async def test_increment_persists_after_commit(
        self, repo: InvoiceRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "INV", "2026-27")
        sequence = await repo.get_sequence_for_update(tenant_id, "INV", "2026-27")
        sequence.last_number += 1
        await db_session.commit()

        result = await db_session.execute(
            select(InvoiceSequence).where(
                InvoiceSequence.tenant_id == tenant_id,
                InvoiceSequence.prefix == "INV",
                InvoiceSequence.fiscal_year == "2026-27",
            )
        )
        assert result.scalar_one().last_number == 1

    async def test_different_fiscal_years_are_independent_counters(
        self, repo: InvoiceRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "INV", "2025-26")
        early = await repo.get_sequence_for_update(tenant_id, "INV", "2025-26")
        early.last_number += 1
        await db_session.commit()

        await repo.ensure_sequence_row(tenant_id, "INV", "2026-27")
        late = await repo.get_sequence_for_update(tenant_id, "INV", "2026-27")
        assert late.last_number == 0

    async def test_different_tenants_are_independent_counters(
        self, repo: InvoiceRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Sequence Tenant", slug=f"other-sequence-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()

        await repo.ensure_sequence_row(tenant_id, "INV", "2026-27")
        mine = await repo.get_sequence_for_update(tenant_id, "INV", "2026-27")
        mine.last_number += 1
        await db_session.commit()

        await repo.ensure_sequence_row(other_tenant.id, "INV", "2026-27")
        theirs = await repo.get_sequence_for_update(other_tenant.id, "INV", "2026-27")
        assert theirs.last_number == 0


class TestGetById:
    async def test_finds_invoice_in_own_tenant(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        invoice = await _make_invoice(db_session, tenant_id, company_id, remarks="Findable")
        found = await repo.get_by_id(invoice.id, tenant_id)
        assert found is not None
        assert found.remarks == "Findable"

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        invoice = await _make_invoice(db_session, tenant_id, company_id)
        assert await repo.get_by_id(invoice.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: InvoiceRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id(uuid.uuid4(), tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        invoice = await _make_invoice(
            db_session, tenant_id, company_id, deleted_at=datetime.now(UTC)
        )
        assert await repo.get_by_id(invoice.id, tenant_id) is None


async def _search(
    repo: InvoiceRepository,
    tenant_id: uuid.UUID,
    *,
    q: str | None = None,
    q_company_ids: list[uuid.UUID] | None = None,
    status: InvoiceStatus | None = None,
    company_id: uuid.UUID | None = None,
    invoice_date_from: date | None = None,
    invoice_date_to: date | None = None,
    sort: str = "-created_at",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Invoice], int]:
    return await repo.search(
        tenant_id,
        q=q,
        q_company_ids=q_company_ids,
        status=status,
        company_id=company_id,
        invoice_date_from=invoice_date_from,
        invoice_date_to=invoice_date_to,
        sort=sort,
        page=page,
        page_size=page_size,
    )


class TestSearchFilters:
    async def test_filters_by_status(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(db_session, tenant_id, company_id, status=InvoiceStatus.DRAFT)
        issued = await _make_invoice(db_session, tenant_id, company_id, status=InvoiceStatus.ISSUED)

        rows, total = await _search(repo, tenant_id, status=InvoiceStatus.ISSUED)
        assert total == 1
        assert rows[0].id == issued.id

    async def test_filters_by_company_id(
        self, repo: InvoiceRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company_a = await _make_company(db_session, tenant_id)
        company_b = await _make_company(db_session, tenant_id)
        target = await _make_invoice(db_session, tenant_id, company_a.id)
        await _make_invoice(db_session, tenant_id, company_b.id)

        rows, total = await _search(repo, tenant_id, company_id=company_a.id)
        assert total == 1
        assert rows[0].id == target.id

    async def test_filters_by_invoice_date_range(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        in_range = await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=date(2026, 7, 15)
        )
        await _make_invoice(db_session, tenant_id, company_id, invoice_date=date(2026, 9, 15))

        rows, total = await _search(
            repo, tenant_id, invoice_date_from=date(2026, 7, 1), invoice_date_to=date(2026, 7, 31)
        )
        assert total == 1
        assert rows[0].id == in_range.id

    async def test_combines_filters(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        target = await _make_invoice(db_session, tenant_id, company_id, status=InvoiceStatus.DRAFT)
        await _make_invoice(db_session, tenant_id, company_id, status=InvoiceStatus.ISSUED)
        other_company = await _make_company(db_session, tenant_id)
        await _make_invoice(db_session, tenant_id, other_company.id, status=InvoiceStatus.DRAFT)

        rows, total = await _search(
            repo, tenant_id, company_id=company_id, status=InvoiceStatus.DRAFT
        )
        assert total == 1
        assert rows[0].id == target.id

    async def test_excludes_soft_deleted_from_results(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(db_session, tenant_id, company_id, deleted_at=datetime.now(UTC))
        rows, total = await _search(repo, tenant_id)
        assert total == 0
        assert rows == []


class TestSearchQuery:
    async def test_matches_invoice_number_case_insensitively(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        target = await _make_invoice(
            db_session, tenant_id, company_id, invoice_number="INV-2026-0042"
        )
        await _make_invoice(db_session, tenant_id, company_id, invoice_number="INV-2026-0099")

        rows, total = await _search(repo, tenant_id, q="inv-2026-0042")
        assert total == 1
        assert rows[0].id == target.id

    async def test_matches_via_pre_resolved_company_ids(
        self, repo: InvoiceRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        matching_company = await _make_company(db_session, tenant_id, name="Ocean Fresh Traders")
        other_company = await _make_company(db_session, tenant_id, name="Irrelevant Co")
        target = await _make_invoice(db_session, tenant_id, matching_company.id)
        await _make_invoice(db_session, tenant_id, other_company.id)

        rows, total = await _search(repo, tenant_id, q="ocean", q_company_ids=[matching_company.id])
        assert total == 1
        assert rows[0].id == target.id

    async def test_q_with_no_matching_company_ids_still_matches_invoice_number(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        target = await _make_invoice(
            db_session, tenant_id, company_id, invoice_number="INV-SEARCHME"
        )

        rows, total = await _search(repo, tenant_id, q="searchme", q_company_ids=[])
        assert total == 1
        assert rows[0].id == target.id

    async def test_no_match_returns_empty(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(db_session, tenant_id, company_id, invoice_number="INV-0001")

        rows, total = await _search(repo, tenant_id, q="no-such-invoice", q_company_ids=[])
        assert total == 0
        assert rows == []

    async def test_blank_query_returns_everything(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(db_session, tenant_id, company_id)
        await _make_invoice(db_session, tenant_id, company_id)

        rows, total = await _search(repo, tenant_id, q="   ")
        assert total == 2


class TestSearchSorting:
    async def _seed_three(
        self, db_session: AsyncSession, tenant_id: uuid.UUID, company_id: uuid.UUID
    ) -> None:
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=date(2026, 7, 15), invoice_number="B"
        )
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=date(2026, 7, 1), invoice_number="A"
        )
        await _make_invoice(
            db_session, tenant_id, company_id, invoice_date=date(2026, 7, 30), invoice_number="C"
        )

    async def test_sort_by_invoice_date_ascending(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, company_id)
        rows, _ = await _search(repo, tenant_id, sort="invoice_date")
        assert [r.invoice_date for r in rows] == [
            date(2026, 7, 1),
            date(2026, 7, 15),
            date(2026, 7, 30),
        ]

    async def test_sort_by_invoice_number_descending(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, company_id)
        rows, _ = await _search(repo, tenant_id, sort="-invoice_number")
        assert [r.invoice_number for r in rows] == ["C", "B", "A"]

    async def test_sort_by_created_at_accepted(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, company_id)
        for sort in ("created_at", "-created_at"):
            rows, total = await _search(repo, tenant_id, sort=sort)
            assert total == 3
            assert len(rows) == 3

    async def test_id_tie_break_follows_the_primary_sort_direction(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        """A tied created_at (two rows inserted in the same instant) must not
        silently override the caller's requested direction - the id
        tie-break has to point the same way as the primary sort."""
        tied_at = datetime.now(UTC)
        older_id_row = await _make_invoice(db_session, tenant_id, company_id, created_at=tied_at)
        newer_id_row = await _make_invoice(db_session, tenant_id, company_id, created_at=tied_at)
        assert older_id_row.id < newer_id_row.id  # uuid7 is time-ordered

        desc_rows, _ = await _search(repo, tenant_id, sort="-created_at")
        assert [r.id for r in desc_rows] == [newer_id_row.id, older_id_row.id]

        asc_rows, _ = await _search(repo, tenant_id, sort="created_at")
        assert [r.id for r in asc_rows] == [older_id_row.id, newer_id_row.id]


class TestSearchPagination:
    async def test_page_size_limits_rows_and_total_reflects_full_count(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        for i in range(5):
            await _make_invoice(
                db_session, tenant_id, company_id, invoice_date=_INVOICE_DATE + timedelta(days=i)
            )

        rows, total = await _search(repo, tenant_id, sort="invoice_date", page=1, page_size=2)
        assert total == 5
        assert len(rows) == 2

    async def test_pages_do_not_overlap_and_cover_all_rows(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        for i in range(5):
            await _make_invoice(
                db_session, tenant_id, company_id, invoice_date=_INVOICE_DATE + timedelta(days=i)
            )

        seen_ids: set[uuid.UUID] = set()
        for page in (1, 2, 3):
            rows, _ = await _search(repo, tenant_id, sort="invoice_date", page=page, page_size=2)
            page_ids = {r.id for r in rows}
            assert not (page_ids & seen_ids), "pages overlapped"
            seen_ids |= page_ids
        assert len(seen_ids) == 5

    async def test_page_past_the_end_returns_empty(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_invoice(db_session, tenant_id, company_id)
        rows, total = await _search(repo, tenant_id, page=99, page_size=10)
        assert total == 1
        assert rows == []


class TestSearchTenantScoping:
    async def test_never_returns_rows_from_another_tenant(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        other_tenant = Tenant(
            name="Other Invoice Tenant", slug=f"other-invoice-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_company = await _make_company(db_session, other_tenant.id)

        mine = await _make_invoice(db_session, tenant_id, company_id)
        await _make_invoice(db_session, other_tenant.id, other_company.id)

        rows, total = await _search(repo, tenant_id)
        assert total == 1
        assert rows[0].id == mine.id


class TestGetItemById:
    async def test_finds_item_in_own_invoice_and_tenant(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
    ) -> None:
        item = await _make_invoice_item(
            db_session, tenant_id, invoice_id, fish_id, trip_catch_id, description="Findable"
        )
        found = await repo.get_item_by_id(item.id, invoice_id, tenant_id)
        assert found is not None
        assert found.description == "Findable"

    async def test_returns_none_for_a_different_invoice(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        invoice_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
    ) -> None:
        item = await _make_invoice_item(db_session, tenant_id, invoice_id, fish_id, trip_catch_id)
        other_invoice = await _make_invoice(db_session, tenant_id, company_id)
        assert await repo.get_item_by_id(item.id, other_invoice.id, tenant_id) is None

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
    ) -> None:
        item = await _make_invoice_item(db_session, tenant_id, invoice_id, fish_id, trip_catch_id)
        assert await repo.get_item_by_id(item.id, invoice_id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: InvoiceRepository, tenant_id: uuid.UUID, invoice_id: uuid.UUID
    ) -> None:
        assert await repo.get_item_by_id(uuid.uuid4(), invoice_id, tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
    ) -> None:
        item = await _make_invoice_item(
            db_session,
            tenant_id,
            invoice_id,
            fish_id,
            trip_catch_id,
            deleted_at=datetime.now(UTC),
        )
        assert await repo.get_item_by_id(item.id, invoice_id, tenant_id) is None


class TestNextLineNumber:
    async def test_starts_at_one_for_an_empty_invoice(
        self, repo: InvoiceRepository, tenant_id: uuid.UUID, invoice_id: uuid.UUID
    ) -> None:
        assert await repo.next_line_number(invoice_id, tenant_id) == 1

    async def test_increments_after_an_item_is_added(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
    ) -> None:
        await _make_invoice_item(
            db_session, tenant_id, invoice_id, fish_id, trip_catch_id, line_number=1
        )
        assert await repo.next_line_number(invoice_id, tenant_id) == 2

    async def test_does_not_reuse_a_deleted_items_line_number(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
    ) -> None:
        await _make_invoice_item(
            db_session,
            tenant_id,
            invoice_id,
            fish_id,
            trip_catch_id,
            line_number=1,
            deleted_at=datetime.now(UTC),
        )
        assert await repo.next_line_number(invoice_id, tenant_id) == 2

    async def test_is_independent_per_invoice(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        invoice_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
    ) -> None:
        await _make_invoice_item(
            db_session, tenant_id, invoice_id, fish_id, trip_catch_id, line_number=1
        )
        other_invoice = await _make_invoice(db_session, tenant_id, company_id)
        assert await repo.next_line_number(other_invoice.id, tenant_id) == 1


class TestSearchItems:
    async def test_matches_description_case_insensitively(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
    ) -> None:
        target = await _make_invoice_item(
            db_session,
            tenant_id,
            invoice_id,
            fish_id,
            trip_catch_id,
            line_number=1,
            description="Pomfret - Grade A",
        )
        await _make_invoice_item(
            db_session,
            tenant_id,
            invoice_id,
            fish_id,
            trip_catch_id,
            line_number=2,
            description="Irrelevant",
        )

        rows = await repo.search_items(invoice_id, tenant_id, q="pomfret", q_fish_ids=None)
        assert [r.id for r in rows] == [target.id]

    async def test_matches_via_pre_resolved_fish_ids(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        trip_id: uuid.UUID,
    ) -> None:
        matching_fish = await _make_fish(db_session, tenant_id, name="Pomfret")
        other_fish = await _make_fish(db_session, tenant_id, name="Sardine")
        matching_catch = await _make_trip_catch(db_session, tenant_id, trip_id, matching_fish.id)
        other_catch = await _make_trip_catch(db_session, tenant_id, trip_id, other_fish.id)
        target = await _make_invoice_item(
            db_session, tenant_id, invoice_id, matching_fish.id, matching_catch.id, line_number=1
        )
        await _make_invoice_item(
            db_session, tenant_id, invoice_id, other_fish.id, other_catch.id, line_number=2
        )

        rows = await repo.search_items(
            invoice_id, tenant_id, q="pomfret", q_fish_ids=[matching_fish.id]
        )
        assert [r.id for r in rows] == [target.id]

    async def test_q_with_no_matching_fish_ids_still_matches_description(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
    ) -> None:
        target = await _make_invoice_item(
            db_session,
            tenant_id,
            invoice_id,
            fish_id,
            trip_catch_id,
            line_number=1,
            description="Searchme",
        )

        rows = await repo.search_items(invoice_id, tenant_id, q="searchme", q_fish_ids=[])
        assert [r.id for r in rows] == [target.id]

    async def test_no_match_returns_empty(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
    ) -> None:
        await _make_invoice_item(
            db_session, tenant_id, invoice_id, fish_id, trip_catch_id, line_number=1
        )
        rows = await repo.search_items(invoice_id, tenant_id, q="no-such-item", q_fish_ids=[])
        assert rows == []

    async def test_blank_query_returns_everything(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
    ) -> None:
        await _make_invoice_item(
            db_session, tenant_id, invoice_id, fish_id, trip_catch_id, line_number=1
        )
        await _make_invoice_item(
            db_session, tenant_id, invoice_id, fish_id, trip_catch_id, line_number=2
        )

        rows = await repo.search_items(invoice_id, tenant_id, q="   ", q_fish_ids=None)
        assert len(rows) == 2

    async def test_ordered_by_line_number(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
    ) -> None:
        third = await _make_invoice_item(
            db_session, tenant_id, invoice_id, fish_id, trip_catch_id, line_number=3
        )
        first = await _make_invoice_item(
            db_session, tenant_id, invoice_id, fish_id, trip_catch_id, line_number=1
        )
        second = await _make_invoice_item(
            db_session, tenant_id, invoice_id, fish_id, trip_catch_id, line_number=2
        )

        rows = await repo.search_items(invoice_id, tenant_id, q=None, q_fish_ids=None)
        assert [r.id for r in rows] == [first.id, second.id, third.id]

    async def test_excludes_soft_deleted_from_results(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
    ) -> None:
        await _make_invoice_item(
            db_session,
            tenant_id,
            invoice_id,
            fish_id,
            trip_catch_id,
            line_number=1,
            deleted_at=datetime.now(UTC),
        )
        rows = await repo.search_items(invoice_id, tenant_id, q=None, q_fish_ids=None)
        assert rows == []

    async def test_scoped_to_one_invoice(
        self,
        repo: InvoiceRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        invoice_id: uuid.UUID,
        fish_id: uuid.UUID,
        trip_catch_id: uuid.UUID,
    ) -> None:
        target = await _make_invoice_item(
            db_session, tenant_id, invoice_id, fish_id, trip_catch_id, line_number=1
        )
        other_invoice = await _make_invoice(db_session, tenant_id, company_id)
        await _make_invoice_item(
            db_session, tenant_id, other_invoice.id, fish_id, trip_catch_id, line_number=1
        )

        rows = await repo.search_items(invoice_id, tenant_id, q=None, q_fish_ids=None)
        assert [r.id for r in rows] == [target.id]
