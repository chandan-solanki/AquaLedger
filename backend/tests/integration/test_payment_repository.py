import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Tenant
from app.modules.companies.models import Company
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.models import Invoice
from app.modules.payments.constants import PaymentMethod, PaymentStatus
from app.modules.payments.models import Payment, PaymentAllocation, PaymentSequence
from app.modules.payments.repository import PaymentRepository

_PAYMENT_DATE = date(2026, 7, 1)
_INVOICE_DATE = date(2026, 7, 1)


@pytest.fixture
async def repo(db_session: AsyncSession) -> PaymentRepository:
    return PaymentRepository(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - the seeded default tenant may already carry
    payments from manual/exploratory testing, which would silently pollute
    any count-based assertion here."""
    tenant = Tenant(
        name="Payment Repo Test Tenant",
        slug=f"payment-repo-test-{uuid.uuid4().hex[:8]}",
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


async def _make_payment(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    company_id: uuid.UUID,
    **overrides: Any,
) -> Payment:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "company_id": company_id,
        "payment_date": _PAYMENT_DATE,
        "payment_method": PaymentMethod.CHEQUE,
        "amount": Decimal("1000.00"),
        "allocated_amount": Decimal("0"),
        "unallocated_amount": Decimal("1000.00"),
        "status": PaymentStatus.DRAFT,
    }
    defaults.update(overrides)
    payment = Payment(**defaults)
    db_session.add(payment)
    await db_session.commit()
    return payment


@pytest.fixture
async def payment_id(
    db_session: AsyncSession, tenant_id: uuid.UUID, company_id: uuid.UUID
) -> uuid.UUID:
    payment = await _make_payment(db_session, tenant_id, company_id)
    return payment.id


async def _make_invoice(
    db_session: AsyncSession, tenant_id: uuid.UUID, company_id: uuid.UUID, **overrides: Any
) -> Invoice:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "company_id": company_id,
        "invoice_date": _INVOICE_DATE,
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


@pytest.fixture
async def invoice_id(
    db_session: AsyncSession, tenant_id: uuid.UUID, company_id: uuid.UUID
) -> uuid.UUID:
    invoice = await _make_invoice(db_session, tenant_id, company_id)
    return invoice.id


async def _make_allocation(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    payment_id: uuid.UUID,
    invoice_id: uuid.UUID,
    **overrides: Any,
) -> PaymentAllocation:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "payment_id": payment_id,
        "invoice_id": invoice_id,
        "allocated_amount": Decimal("100.00"),
    }
    defaults.update(overrides)
    allocation = PaymentAllocation(**defaults)
    db_session.add(allocation)
    await db_session.commit()
    return allocation


class TestGetById:
    async def test_finds_payment_in_own_tenant(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        payment = await _make_payment(db_session, tenant_id, company_id, remarks="Findable")
        found = await repo.get_by_id(payment.id, tenant_id)
        assert found is not None
        assert found.remarks == "Findable"

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        payment = await _make_payment(db_session, tenant_id, company_id)
        assert await repo.get_by_id(payment.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: PaymentRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id(uuid.uuid4(), tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        payment = await _make_payment(
            db_session, tenant_id, company_id, deleted_at=datetime.now(UTC)
        )
        assert await repo.get_by_id(payment.id, tenant_id) is None


class TestGetByIdForUpdate:
    """The Session 5 posting workflow's locked lookup - same scoping rules
    as get_by_id, plus a row lock. Functional correctness (does it find/
    scope the same way) is what's testable here; the actual lock's effect
    on a concurrent transaction isn't exercised by this single-session
    suite."""

    async def test_finds_payment_in_own_tenant(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        payment = await _make_payment(db_session, tenant_id, company_id, remarks="Lockable")
        found = await repo.get_by_id_for_update(payment.id, tenant_id)
        assert found is not None
        assert found.remarks == "Lockable"

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        payment = await _make_payment(db_session, tenant_id, company_id)
        assert await repo.get_by_id_for_update(payment.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: PaymentRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id_for_update(uuid.uuid4(), tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        payment = await _make_payment(
            db_session, tenant_id, company_id, deleted_at=datetime.now(UTC)
        )
        assert await repo.get_by_id_for_update(payment.id, tenant_id) is None

    async def test_mutations_on_the_locked_row_persist_after_commit(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        payment = await _make_payment(db_session, tenant_id, company_id)
        locked = await repo.get_by_id_for_update(payment.id, tenant_id)
        assert locked is not None
        locked.payment_number = "PAY/2026-27/00001"
        locked.status = PaymentStatus.POSTED
        await db_session.commit()

        refetched = await repo.get_by_id(payment.id, tenant_id)
        assert refetched is not None
        assert refetched.payment_number == "PAY/2026-27/00001"
        assert refetched.status == PaymentStatus.POSTED


async def _search(
    repo: PaymentRepository,
    tenant_id: uuid.UUID,
    *,
    q: str | None = None,
    q_company_ids: list[uuid.UUID] | None = None,
    status: PaymentStatus | None = None,
    company_id: uuid.UUID | None = None,
    payment_method: PaymentMethod | None = None,
    payment_date_from: date | None = None,
    payment_date_to: date | None = None,
    sort: str = "-created_at",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Payment], int]:
    return await repo.search(
        tenant_id,
        q=q,
        q_company_ids=q_company_ids,
        status=status,
        company_id=company_id,
        payment_method=payment_method,
        payment_date_from=payment_date_from,
        payment_date_to=payment_date_to,
        sort=sort,
        page=page,
        page_size=page_size,
    )


class TestSearchFilters:
    async def test_filters_by_status(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_payment(db_session, tenant_id, company_id, status=PaymentStatus.DRAFT)
        posted = await _make_payment(db_session, tenant_id, company_id, status=PaymentStatus.POSTED)

        rows, total = await _search(repo, tenant_id, status=PaymentStatus.POSTED)
        assert total == 1
        assert rows[0].id == posted.id

    async def test_filters_by_company_id(
        self, repo: PaymentRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        company_a = await _make_company(db_session, tenant_id)
        company_b = await _make_company(db_session, tenant_id)
        target = await _make_payment(db_session, tenant_id, company_a.id)
        await _make_payment(db_session, tenant_id, company_b.id)

        rows, total = await _search(repo, tenant_id, company_id=company_a.id)
        assert total == 1
        assert rows[0].id == target.id

    async def test_filters_by_payment_method(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_payment(db_session, tenant_id, company_id, payment_method=PaymentMethod.CASH)
        upi = await _make_payment(
            db_session, tenant_id, company_id, payment_method=PaymentMethod.UPI
        )

        rows, total = await _search(repo, tenant_id, payment_method=PaymentMethod.UPI)
        assert total == 1
        assert rows[0].id == upi.id

    async def test_filters_by_payment_date_range(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        in_range = await _make_payment(
            db_session, tenant_id, company_id, payment_date=date(2026, 7, 15)
        )
        await _make_payment(db_session, tenant_id, company_id, payment_date=date(2026, 9, 15))

        rows, total = await _search(
            repo, tenant_id, payment_date_from=date(2026, 7, 1), payment_date_to=date(2026, 7, 31)
        )
        assert total == 1
        assert rows[0].id == in_range.id

    async def test_combines_filters(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        target = await _make_payment(db_session, tenant_id, company_id, status=PaymentStatus.DRAFT)
        await _make_payment(db_session, tenant_id, company_id, status=PaymentStatus.POSTED)
        other_company = await _make_company(db_session, tenant_id)
        await _make_payment(db_session, tenant_id, other_company.id, status=PaymentStatus.DRAFT)

        rows, total = await _search(
            repo, tenant_id, company_id=company_id, status=PaymentStatus.DRAFT
        )
        assert total == 1
        assert rows[0].id == target.id

    async def test_excludes_soft_deleted_from_results(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_payment(db_session, tenant_id, company_id, deleted_at=datetime.now(UTC))
        rows, total = await _search(repo, tenant_id)
        assert total == 0
        assert rows == []


class TestSearchQuery:
    async def test_matches_payment_number_case_insensitively(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        target = await _make_payment(
            db_session, tenant_id, company_id, payment_number="PAY-2026-0042"
        )
        await _make_payment(db_session, tenant_id, company_id, payment_number="PAY-2026-0099")

        rows, total = await _search(repo, tenant_id, q="pay-2026-0042")
        assert total == 1
        assert rows[0].id == target.id

    async def test_matches_reference_number_case_insensitively(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        target = await _make_payment(
            db_session, tenant_id, company_id, reference_number="REF445512"
        )
        await _make_payment(db_session, tenant_id, company_id, reference_number="REFOTHER")

        rows, total = await _search(repo, tenant_id, q="ref445512")
        assert total == 1
        assert rows[0].id == target.id

    async def test_matches_via_pre_resolved_company_ids(
        self, repo: PaymentRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        matching_company = await _make_company(db_session, tenant_id, name="Ocean Fresh Traders")
        other_company = await _make_company(db_session, tenant_id, name="Irrelevant Co")
        target = await _make_payment(db_session, tenant_id, matching_company.id)
        await _make_payment(db_session, tenant_id, other_company.id)

        rows, total = await _search(repo, tenant_id, q="ocean", q_company_ids=[matching_company.id])
        assert total == 1
        assert rows[0].id == target.id

    async def test_q_with_no_matching_company_ids_still_matches_payment_number(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        target = await _make_payment(
            db_session, tenant_id, company_id, payment_number="PAY-SEARCHME"
        )

        rows, total = await _search(repo, tenant_id, q="searchme", q_company_ids=[])
        assert total == 1
        assert rows[0].id == target.id

    async def test_no_match_returns_empty(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_payment(db_session, tenant_id, company_id, payment_number="PAY-0001")

        rows, total = await _search(repo, tenant_id, q="no-such-payment", q_company_ids=[])
        assert total == 0
        assert rows == []

    async def test_blank_query_returns_everything(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_payment(db_session, tenant_id, company_id)
        await _make_payment(db_session, tenant_id, company_id)

        rows, total = await _search(repo, tenant_id, q="   ")
        assert total == 2


class TestSearchSorting:
    async def _seed_three(
        self, db_session: AsyncSession, tenant_id: uuid.UUID, company_id: uuid.UUID
    ) -> None:
        await _make_payment(
            db_session,
            tenant_id,
            company_id,
            payment_date=date(2026, 7, 15),
            payment_number="B",
            amount=Decimal("200.00"),
        )
        await _make_payment(
            db_session,
            tenant_id,
            company_id,
            payment_date=date(2026, 7, 1),
            payment_number="A",
            amount=Decimal("100.00"),
        )
        await _make_payment(
            db_session,
            tenant_id,
            company_id,
            payment_date=date(2026, 7, 30),
            payment_number="C",
            amount=Decimal("300.00"),
        )

    async def test_sort_by_payment_date_ascending(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, company_id)
        rows, _ = await _search(repo, tenant_id, sort="payment_date")
        assert [r.payment_date for r in rows] == [
            date(2026, 7, 1),
            date(2026, 7, 15),
            date(2026, 7, 30),
        ]

    async def test_sort_by_payment_number_descending(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, company_id)
        rows, _ = await _search(repo, tenant_id, sort="-payment_number")
        assert [r.payment_number for r in rows] == ["C", "B", "A"]

    async def test_sort_by_amount_ascending(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, company_id)
        rows, _ = await _search(repo, tenant_id, sort="amount")
        assert [r.amount for r in rows] == [Decimal("100.00"), Decimal("200.00"), Decimal("300.00")]

    async def test_sort_by_created_at_accepted(
        self,
        repo: PaymentRepository,
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
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        tied_at = datetime.now(UTC)
        older_id_row = await _make_payment(db_session, tenant_id, company_id, created_at=tied_at)
        newer_id_row = await _make_payment(db_session, tenant_id, company_id, created_at=tied_at)
        assert older_id_row.id < newer_id_row.id  # uuid7 is time-ordered

        desc_rows, _ = await _search(repo, tenant_id, sort="-created_at")
        assert [r.id for r in desc_rows] == [newer_id_row.id, older_id_row.id]

        asc_rows, _ = await _search(repo, tenant_id, sort="created_at")
        assert [r.id for r in asc_rows] == [older_id_row.id, newer_id_row.id]


class TestSearchPagination:
    async def test_page_size_limits_rows_and_total_reflects_full_count(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        for i in range(5):
            await _make_payment(
                db_session, tenant_id, company_id, payment_date=_PAYMENT_DATE + timedelta(days=i)
            )

        rows, total = await _search(repo, tenant_id, sort="payment_date", page=1, page_size=2)
        assert total == 5
        assert len(rows) == 2

    async def test_pages_do_not_overlap_and_cover_all_rows(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        for i in range(5):
            await _make_payment(
                db_session, tenant_id, company_id, payment_date=_PAYMENT_DATE + timedelta(days=i)
            )

        seen_ids: set[uuid.UUID] = set()
        for page in (1, 2, 3):
            rows, _ = await _search(repo, tenant_id, sort="payment_date", page=page, page_size=2)
            page_ids = {r.id for r in rows}
            assert not (page_ids & seen_ids), "pages overlapped"
            seen_ids |= page_ids
        assert len(seen_ids) == 5

    async def test_page_past_the_end_returns_empty(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        await _make_payment(db_session, tenant_id, company_id)
        rows, total = await _search(repo, tenant_id, page=99, page_size=10)
        assert total == 1
        assert rows == []


class TestSearchTenantScoping:
    async def test_never_returns_rows_from_another_tenant(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        other_tenant = Tenant(
            name="Other Payment Tenant", slug=f"other-payment-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_company = await _make_company(db_session, other_tenant.id)

        mine = await _make_payment(db_session, tenant_id, company_id)
        await _make_payment(db_session, other_tenant.id, other_company.id)

        rows, total = await _search(repo, tenant_id)
        assert total == 1
        assert rows[0].id == mine.id
        assert rows[0].id == mine.id


class TestGetAllocationById:
    async def test_finds_allocation_in_own_payment_and_tenant(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        payment_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        allocation = await _make_allocation(
            db_session, tenant_id, payment_id, invoice_id, allocated_amount=Decimal("250.00")
        )
        found = await repo.get_allocation_by_id(allocation.id, payment_id, tenant_id)
        assert found is not None
        assert found.allocated_amount == Decimal("250.00")

    async def test_returns_none_for_a_different_payment(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        payment_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        allocation = await _make_allocation(db_session, tenant_id, payment_id, invoice_id)
        other_payment = await _make_payment(db_session, tenant_id, company_id)
        assert await repo.get_allocation_by_id(allocation.id, other_payment.id, tenant_id) is None

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        payment_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        allocation = await _make_allocation(db_session, tenant_id, payment_id, invoice_id)
        assert await repo.get_allocation_by_id(allocation.id, payment_id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: PaymentRepository, tenant_id: uuid.UUID, payment_id: uuid.UUID
    ) -> None:
        assert await repo.get_allocation_by_id(uuid.uuid4(), payment_id, tenant_id) is None


class TestListAllocations:
    async def test_returns_every_allocation_oldest_first(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        payment_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        invoice_a = await _make_invoice(db_session, tenant_id, company_id)
        invoice_b = await _make_invoice(db_session, tenant_id, company_id)
        first = await _make_allocation(db_session, tenant_id, payment_id, invoice_a.id)
        second = await _make_allocation(db_session, tenant_id, payment_id, invoice_b.id)

        rows = await repo.list_allocations(payment_id, tenant_id)
        assert [r.id for r in rows] == [first.id, second.id]

    async def test_scoped_to_one_payment(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        payment_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        target = await _make_allocation(db_session, tenant_id, payment_id, invoice_id)
        other_payment = await _make_payment(db_session, tenant_id, company_id)
        await _make_allocation(db_session, tenant_id, other_payment.id, invoice_id)

        rows = await repo.list_allocations(payment_id, tenant_id)
        assert [r.id for r in rows] == [target.id]

    async def test_empty_when_no_allocations(
        self, repo: PaymentRepository, tenant_id: uuid.UUID, payment_id: uuid.UUID
    ) -> None:
        assert await repo.list_allocations(payment_id, tenant_id) == []


class TestDeleteAllocation:
    async def test_hard_deletes_the_row(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        payment_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        allocation = await _make_allocation(db_session, tenant_id, payment_id, invoice_id)
        await repo.delete_allocation(allocation)
        await db_session.commit()

        assert await repo.get_allocation_by_id(allocation.id, payment_id, tenant_id) is None


class TestSumAllocatedAmount:
    async def test_sums_every_active_allocation(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        payment_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        invoice_a = await _make_invoice(db_session, tenant_id, company_id)
        invoice_b = await _make_invoice(db_session, tenant_id, company_id)
        await _make_allocation(
            db_session, tenant_id, payment_id, invoice_a.id, allocated_amount=Decimal("300.00")
        )
        await _make_allocation(
            db_session, tenant_id, payment_id, invoice_b.id, allocated_amount=Decimal("150.50")
        )

        total = await repo.sum_allocated_amount(payment_id, tenant_id)
        assert total == Decimal("450.50")

    async def test_zero_when_no_allocations(
        self, repo: PaymentRepository, tenant_id: uuid.UUID, payment_id: uuid.UUID
    ) -> None:
        assert await repo.sum_allocated_amount(payment_id, tenant_id) == Decimal("0")

    async def test_excludes_a_deleted_allocation(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        payment_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        allocation = await _make_allocation(
            db_session, tenant_id, payment_id, invoice_id, allocated_amount=Decimal("300.00")
        )
        await repo.delete_allocation(allocation)
        await db_session.commit()

        assert await repo.sum_allocated_amount(payment_id, tenant_id) == Decimal("0")

    async def test_scoped_to_one_payment(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        payment_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        await _make_allocation(
            db_session, tenant_id, payment_id, invoice_id, allocated_amount=Decimal("300.00")
        )
        other_payment = await _make_payment(db_session, tenant_id, company_id)
        await _make_allocation(
            db_session, tenant_id, other_payment.id, invoice_id, allocated_amount=Decimal("999.00")
        )

        assert await repo.sum_allocated_amount(payment_id, tenant_id) == Decimal("300.00")


class TestSumAllocatedAmountByInvoice:
    """Sprint 10 Session 4's outstanding engine input - unlike
    sum_allocated_amount (scoped to one payment), this sums across every
    payment that allocates to one invoice."""

    async def test_sums_across_multiple_payments(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        payment_a = await _make_payment(db_session, tenant_id, company_id)
        payment_b = await _make_payment(db_session, tenant_id, company_id)
        await _make_allocation(
            db_session, tenant_id, payment_a.id, invoice_id, allocated_amount=Decimal("300.00")
        )
        await _make_allocation(
            db_session, tenant_id, payment_b.id, invoice_id, allocated_amount=Decimal("150.50")
        )

        total = await repo.sum_allocated_amount_by_invoice(invoice_id, tenant_id)
        assert total == Decimal("450.50")

    async def test_zero_when_no_allocations(
        self, repo: PaymentRepository, tenant_id: uuid.UUID, invoice_id: uuid.UUID
    ) -> None:
        assert await repo.sum_allocated_amount_by_invoice(invoice_id, tenant_id) == Decimal("0")

    async def test_excludes_a_deleted_allocation(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        payment_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        allocation = await _make_allocation(
            db_session, tenant_id, payment_id, invoice_id, allocated_amount=Decimal("300.00")
        )
        await repo.delete_allocation(allocation)
        await db_session.commit()

        assert await repo.sum_allocated_amount_by_invoice(invoice_id, tenant_id) == Decimal("0")

    async def test_scoped_to_one_invoice(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        payment_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        await _make_allocation(
            db_session, tenant_id, payment_id, invoice_id, allocated_amount=Decimal("300.00")
        )
        other_invoice = await _make_invoice(db_session, tenant_id, company_id)
        await _make_allocation(
            db_session, tenant_id, payment_id, other_invoice.id, allocated_amount=Decimal("999.00")
        )

        assert await repo.sum_allocated_amount_by_invoice(invoice_id, tenant_id) == Decimal(
            "300.00"
        )

    async def test_scoped_to_one_tenant(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        payment_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        await _make_allocation(
            db_session, tenant_id, payment_id, invoice_id, allocated_amount=Decimal("300.00")
        )
        assert await repo.sum_allocated_amount_by_invoice(invoice_id, uuid.uuid4()) == Decimal("0")


class TestHasAllocations:
    """Sprint 10 Session 5 posting workflow's "must have at least one
    allocation" existence check."""

    async def test_true_when_at_least_one_allocation_exists(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        payment_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        await _make_allocation(db_session, tenant_id, payment_id, invoice_id)
        assert await repo.has_allocations(payment_id, tenant_id) is True

    async def test_false_when_no_allocations(
        self, repo: PaymentRepository, tenant_id: uuid.UUID, payment_id: uuid.UUID
    ) -> None:
        assert await repo.has_allocations(payment_id, tenant_id) is False

    async def test_false_after_the_only_allocation_is_deleted(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        payment_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        allocation = await _make_allocation(db_session, tenant_id, payment_id, invoice_id)
        await repo.delete_allocation(allocation)
        await db_session.commit()

        assert await repo.has_allocations(payment_id, tenant_id) is False

    async def test_scoped_to_one_payment(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        company_id: uuid.UUID,
        payment_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        other_payment = await _make_payment(db_session, tenant_id, company_id)
        await _make_allocation(db_session, tenant_id, other_payment.id, invoice_id)

        assert await repo.has_allocations(payment_id, tenant_id) is False

    async def test_scoped_to_one_tenant(
        self,
        repo: PaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        payment_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> None:
        await _make_allocation(db_session, tenant_id, payment_id, invoice_id)
        assert await repo.has_allocations(payment_id, uuid.uuid4()) is False


class TestPaymentSequence:
    """The Session 5 posting workflow's payment numbering counter
    (ARCHITECTURE.md §13.1) - ensure_sequence_row (`INSERT ... ON CONFLICT
    DO NOTHING`) followed by get_sequence_for_update (`SELECT ... FOR
    UPDATE`). Mirrors InvoiceRepository's TestSequenceRow exactly."""

    async def test_ensure_creates_a_row_starting_at_zero(
        self, repo: PaymentRepository, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "PAY", "2026-27")
        sequence = await repo.get_sequence_for_update(tenant_id, "PAY", "2026-27")
        assert sequence.last_number == 0

    async def test_ensure_is_idempotent_and_does_not_reset_an_existing_counter(
        self, repo: PaymentRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "PAY", "2026-27")
        sequence = await repo.get_sequence_for_update(tenant_id, "PAY", "2026-27")
        sequence.last_number += 1
        await db_session.commit()

        # A second ensure_sequence_row call (as post() makes on every
        # payment, not just the first per fiscal year) must not clobber the
        # counter back to zero.
        await repo.ensure_sequence_row(tenant_id, "PAY", "2026-27")
        relocked = await repo.get_sequence_for_update(tenant_id, "PAY", "2026-27")
        assert relocked.last_number == 1

    async def test_increment_persists_after_commit(
        self, repo: PaymentRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "PAY", "2026-27")
        sequence = await repo.get_sequence_for_update(tenant_id, "PAY", "2026-27")
        sequence.last_number += 1
        await db_session.commit()

        result = await db_session.execute(
            select(PaymentSequence).where(
                PaymentSequence.tenant_id == tenant_id,
                PaymentSequence.prefix == "PAY",
                PaymentSequence.fiscal_year == "2026-27",
            )
        )
        assert result.scalar_one().last_number == 1

    async def test_different_fiscal_years_are_independent_counters(
        self, repo: PaymentRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "PAY", "2025-26")
        early = await repo.get_sequence_for_update(tenant_id, "PAY", "2025-26")
        early.last_number += 1
        await db_session.commit()

        await repo.ensure_sequence_row(tenant_id, "PAY", "2026-27")
        late = await repo.get_sequence_for_update(tenant_id, "PAY", "2026-27")
        assert late.last_number == 0

    async def test_different_tenants_are_independent_counters(
        self, repo: PaymentRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Payment Sequence Tenant", slug=f"other-pay-sequence-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()

        await repo.ensure_sequence_row(tenant_id, "PAY", "2026-27")
        mine = await repo.get_sequence_for_update(tenant_id, "PAY", "2026-27")
        mine.last_number += 1
        await db_session.commit()

        await repo.ensure_sequence_row(other_tenant.id, "PAY", "2026-27")
        theirs = await repo.get_sequence_for_update(other_tenant.id, "PAY", "2026-27")
        assert theirs.last_number == 0
