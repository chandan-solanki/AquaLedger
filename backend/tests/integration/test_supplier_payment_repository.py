import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Tenant
from app.modules.purchase.constants import PurchaseStatus
from app.modules.purchase.models import PurchaseBill
from app.modules.supplier_payments.constants import PaymentMethod, SupplierPaymentStatus
from app.modules.supplier_payments.models import (
    SupplierPayment,
    SupplierPaymentAllocation,
    SupplierPaymentSequence,
)
from app.modules.supplier_payments.repository import SupplierPaymentRepository
from app.modules.suppliers.models import Supplier

_PAYMENT_DATE = date(2026, 7, 1)


@pytest.fixture
async def repo(db_session: AsyncSession) -> SupplierPaymentRepository:
    return SupplierPaymentRepository(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - the seeded default tenant may already carry
    supplier payments from manual/exploratory testing, which would silently
    pollute any count-based assertion here."""
    tenant = Tenant(
        name="Supplier Payment Repo Test Tenant",
        slug=f"supplier-payment-repo-test-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant.id


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
    db_session: AsyncSession, tenant_id: uuid.UUID, supplier_id: uuid.UUID, **overrides: Any
) -> PurchaseBill:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "supplier_id": supplier_id,
        "bill_date": _PAYMENT_DATE,
        "status": PurchaseStatus.POSTED,
        "total_amount": Decimal("1000.00"),
        "balance_amount": Decimal("1000.00"),
    }
    defaults.update(overrides)
    purchase_bill = PurchaseBill(**defaults)
    db_session.add(purchase_bill)
    await db_session.commit()
    return purchase_bill


@pytest.fixture
async def purchase_bill_id(
    db_session: AsyncSession, tenant_id: uuid.UUID, supplier_id: uuid.UUID
) -> uuid.UUID:
    purchase_bill = await _make_purchase_bill(db_session, tenant_id, supplier_id)
    return purchase_bill.id


@pytest.fixture
async def supplier_payment_id(
    db_session: AsyncSession, tenant_id: uuid.UUID, supplier_id: uuid.UUID
) -> uuid.UUID:
    payment = await _make_supplier_payment(db_session, tenant_id, supplier_id)
    return payment.id


async def _make_allocation(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    supplier_payment_id: uuid.UUID,
    purchase_bill_id: uuid.UUID,
    **overrides: Any,
) -> SupplierPaymentAllocation:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "supplier_payment_id": supplier_payment_id,
        "purchase_bill_id": purchase_bill_id,
        "allocated_amount": Decimal("100.00"),
    }
    defaults.update(overrides)
    allocation = SupplierPaymentAllocation(**defaults)
    db_session.add(allocation)
    await db_session.commit()
    return allocation


async def _make_supplier_payment(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID,
    **overrides: Any,
) -> SupplierPayment:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "supplier_id": supplier_id,
        "payment_date": _PAYMENT_DATE,
        "payment_method": PaymentMethod.CHEQUE,
        "amount": Decimal("1000.00"),
        "allocated_amount": Decimal("0"),
        "unallocated_amount": Decimal("1000.00"),
        "status": SupplierPaymentStatus.DRAFT,
    }
    defaults.update(overrides)
    supplier_payment = SupplierPayment(**defaults)
    db_session.add(supplier_payment)
    await db_session.commit()
    return supplier_payment


class TestGetById:
    async def test_finds_supplier_payment_in_own_tenant(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        payment = await _make_supplier_payment(
            db_session, tenant_id, supplier_id, remarks="Findable"
        )
        found = await repo.get_by_id(payment.id, tenant_id)
        assert found is not None
        assert found.remarks == "Findable"

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        payment = await _make_supplier_payment(db_session, tenant_id, supplier_id)
        assert await repo.get_by_id(payment.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: SupplierPaymentRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id(uuid.uuid4(), tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        payment = await _make_supplier_payment(
            db_session, tenant_id, supplier_id, deleted_at=datetime.now(UTC)
        )
        assert await repo.get_by_id(payment.id, tenant_id) is None


async def _search(
    repo: SupplierPaymentRepository,
    tenant_id: uuid.UUID,
    *,
    q: str | None = None,
    q_supplier_ids: list[uuid.UUID] | None = None,
    status: SupplierPaymentStatus | None = None,
    supplier_id: uuid.UUID | None = None,
    payment_method: PaymentMethod | None = None,
    payment_date_from: date | None = None,
    payment_date_to: date | None = None,
    sort: str = "-created_at",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[SupplierPayment], int]:
    return await repo.search(
        tenant_id,
        q=q,
        q_supplier_ids=q_supplier_ids,
        status=status,
        supplier_id=supplier_id,
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
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_supplier_payment(
            db_session, tenant_id, supplier_id, status=SupplierPaymentStatus.DRAFT
        )
        posted = await _make_supplier_payment(
            db_session, tenant_id, supplier_id, status=SupplierPaymentStatus.POSTED
        )

        rows, total = await _search(repo, tenant_id, status=SupplierPaymentStatus.POSTED)
        assert total == 1
        assert rows[0].id == posted.id

    async def test_filters_by_supplier_id(
        self, repo: SupplierPaymentRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier_a = await _make_supplier(db_session, tenant_id)
        supplier_b = await _make_supplier(db_session, tenant_id)
        target = await _make_supplier_payment(db_session, tenant_id, supplier_a.id)
        await _make_supplier_payment(db_session, tenant_id, supplier_b.id)

        rows, total = await _search(repo, tenant_id, supplier_id=supplier_a.id)
        assert total == 1
        assert rows[0].id == target.id

    async def test_filters_by_payment_method(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_supplier_payment(
            db_session, tenant_id, supplier_id, payment_method=PaymentMethod.CASH
        )
        upi = await _make_supplier_payment(
            db_session, tenant_id, supplier_id, payment_method=PaymentMethod.UPI
        )

        rows, total = await _search(repo, tenant_id, payment_method=PaymentMethod.UPI)
        assert total == 1
        assert rows[0].id == upi.id

    async def test_filters_by_payment_date_range(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        in_range = await _make_supplier_payment(
            db_session, tenant_id, supplier_id, payment_date=date(2026, 7, 15)
        )
        await _make_supplier_payment(
            db_session, tenant_id, supplier_id, payment_date=date(2026, 9, 15)
        )

        rows, total = await _search(
            repo, tenant_id, payment_date_from=date(2026, 7, 1), payment_date_to=date(2026, 7, 31)
        )
        assert total == 1
        assert rows[0].id == in_range.id

    async def test_combines_filters(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        target = await _make_supplier_payment(
            db_session, tenant_id, supplier_id, status=SupplierPaymentStatus.DRAFT
        )
        await _make_supplier_payment(
            db_session, tenant_id, supplier_id, status=SupplierPaymentStatus.POSTED
        )
        other_supplier = await _make_supplier(db_session, tenant_id)
        await _make_supplier_payment(
            db_session, tenant_id, other_supplier.id, status=SupplierPaymentStatus.DRAFT
        )

        rows, total = await _search(
            repo, tenant_id, supplier_id=supplier_id, status=SupplierPaymentStatus.DRAFT
        )
        assert total == 1
        assert rows[0].id == target.id

    async def test_excludes_soft_deleted_from_results(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_supplier_payment(
            db_session, tenant_id, supplier_id, deleted_at=datetime.now(UTC)
        )
        rows, total = await _search(repo, tenant_id)
        assert total == 0
        assert rows == []


class TestSearchQuery:
    async def test_matches_payment_number_case_insensitively(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        target = await _make_supplier_payment(
            db_session, tenant_id, supplier_id, payment_number="SPAY-2026-0042"
        )
        await _make_supplier_payment(
            db_session, tenant_id, supplier_id, payment_number="SPAY-2026-0099"
        )

        rows, total = await _search(repo, tenant_id, q="spay-2026-0042")
        assert total == 1
        assert rows[0].id == target.id

    async def test_matches_reference_number_case_insensitively(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        target = await _make_supplier_payment(
            db_session, tenant_id, supplier_id, reference_number="REF778821"
        )
        await _make_supplier_payment(
            db_session, tenant_id, supplier_id, reference_number="REFOTHER"
        )

        rows, total = await _search(repo, tenant_id, q="ref778821")
        assert total == 1
        assert rows[0].id == target.id

    async def test_matches_via_pre_resolved_supplier_ids(
        self, repo: SupplierPaymentRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        matching_supplier = await _make_supplier(db_session, tenant_id, name="Ocean Fresh Traders")
        other_supplier = await _make_supplier(db_session, tenant_id, name="Irrelevant Co")
        target = await _make_supplier_payment(db_session, tenant_id, matching_supplier.id)
        await _make_supplier_payment(db_session, tenant_id, other_supplier.id)

        rows, total = await _search(
            repo, tenant_id, q="ocean", q_supplier_ids=[matching_supplier.id]
        )
        assert total == 1
        assert rows[0].id == target.id

    async def test_q_with_no_matching_supplier_ids_still_matches_payment_number(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        target = await _make_supplier_payment(
            db_session, tenant_id, supplier_id, payment_number="SPAY-SEARCHME"
        )

        rows, total = await _search(repo, tenant_id, q="searchme", q_supplier_ids=[])
        assert total == 1
        assert rows[0].id == target.id

    async def test_no_match_returns_empty(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_supplier_payment(db_session, tenant_id, supplier_id, payment_number="SPAY-0001")

        rows, total = await _search(repo, tenant_id, q="no-such-payment", q_supplier_ids=[])
        assert total == 0
        assert rows == []

    async def test_blank_query_returns_everything(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_supplier_payment(db_session, tenant_id, supplier_id)
        await _make_supplier_payment(db_session, tenant_id, supplier_id)

        rows, total = await _search(repo, tenant_id, q="   ")
        assert total == 2


class TestSearchSorting:
    async def _seed_three(
        self, db_session: AsyncSession, tenant_id: uuid.UUID, supplier_id: uuid.UUID
    ) -> None:
        await _make_supplier_payment(
            db_session,
            tenant_id,
            supplier_id,
            payment_date=date(2026, 7, 15),
            payment_number="B",
        )
        await _make_supplier_payment(
            db_session,
            tenant_id,
            supplier_id,
            payment_date=date(2026, 7, 1),
            payment_number="A",
        )
        await _make_supplier_payment(
            db_session,
            tenant_id,
            supplier_id,
            payment_date=date(2026, 7, 30),
            payment_number="C",
        )

    async def test_sort_by_payment_date_ascending(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, supplier_id)
        rows, _ = await _search(repo, tenant_id, sort="payment_date")
        assert [r.payment_date for r in rows] == [
            date(2026, 7, 1),
            date(2026, 7, 15),
            date(2026, 7, 30),
        ]

    async def test_sort_by_payment_number_descending(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, supplier_id)
        rows, _ = await _search(repo, tenant_id, sort="-payment_number")
        assert [r.payment_number for r in rows] == ["C", "B", "A"]

    async def test_sort_by_created_at_accepted(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await self._seed_three(db_session, tenant_id, supplier_id)
        for sort in ("created_at", "-created_at"):
            rows, total = await _search(repo, tenant_id, sort=sort)
            assert total == 3
            assert len(rows) == 3

    async def test_id_tie_break_follows_the_primary_sort_direction(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        tied_at = datetime.now(UTC)
        older_id_row = await _make_supplier_payment(
            db_session, tenant_id, supplier_id, created_at=tied_at
        )
        newer_id_row = await _make_supplier_payment(
            db_session, tenant_id, supplier_id, created_at=tied_at
        )
        assert older_id_row.id < newer_id_row.id  # uuid7 is time-ordered

        desc_rows, _ = await _search(repo, tenant_id, sort="-created_at")
        assert [r.id for r in desc_rows] == [newer_id_row.id, older_id_row.id]

        asc_rows, _ = await _search(repo, tenant_id, sort="created_at")
        assert [r.id for r in asc_rows] == [older_id_row.id, newer_id_row.id]


class TestSearchPagination:
    async def test_page_size_limits_rows_and_total_reflects_full_count(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        for i in range(5):
            await _make_supplier_payment(
                db_session, tenant_id, supplier_id, payment_date=_PAYMENT_DATE + timedelta(days=i)
            )

        rows, total = await _search(repo, tenant_id, sort="payment_date", page=1, page_size=2)
        assert total == 5
        assert len(rows) == 2

    async def test_pages_do_not_overlap_and_cover_all_rows(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        for i in range(5):
            await _make_supplier_payment(
                db_session, tenant_id, supplier_id, payment_date=_PAYMENT_DATE + timedelta(days=i)
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
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        await _make_supplier_payment(db_session, tenant_id, supplier_id)
        rows, total = await _search(repo, tenant_id, page=99, page_size=10)
        assert total == 1
        assert rows == []


class TestSearchTenantScoping:
    async def test_never_returns_rows_from_another_tenant(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        other_tenant = Tenant(
            name="Other Supplier Payment Tenant",
            slug=f"other-supplier-payment-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_supplier = await _make_supplier(db_session, other_tenant.id)

        mine = await _make_supplier_payment(db_session, tenant_id, supplier_id)
        await _make_supplier_payment(db_session, other_tenant.id, other_supplier.id)

        rows, total = await _search(repo, tenant_id)
        assert total == 1
        assert rows[0].id == mine.id


class TestGetAllocationById:
    async def test_finds_allocation_in_own_payment_and_tenant(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_payment_id: uuid.UUID,
        purchase_bill_id: uuid.UUID,
    ) -> None:
        allocation = await _make_allocation(
            db_session,
            tenant_id,
            supplier_payment_id,
            purchase_bill_id,
            allocated_amount=Decimal("250.00"),
        )
        found = await repo.get_allocation_by_id(allocation.id, supplier_payment_id, tenant_id)
        assert found is not None
        assert found.allocated_amount == Decimal("250.00")

    async def test_returns_none_for_a_different_supplier_payment(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        supplier_payment_id: uuid.UUID,
        purchase_bill_id: uuid.UUID,
    ) -> None:
        allocation = await _make_allocation(
            db_session, tenant_id, supplier_payment_id, purchase_bill_id
        )
        other_payment = await _make_supplier_payment(db_session, tenant_id, supplier_id)
        assert await repo.get_allocation_by_id(allocation.id, other_payment.id, tenant_id) is None

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_payment_id: uuid.UUID,
        purchase_bill_id: uuid.UUID,
    ) -> None:
        allocation = await _make_allocation(
            db_session, tenant_id, supplier_payment_id, purchase_bill_id
        )
        assert (
            await repo.get_allocation_by_id(allocation.id, supplier_payment_id, uuid.uuid4())
            is None
        )

    async def test_returns_none_for_unknown_id(
        self, repo: SupplierPaymentRepository, tenant_id: uuid.UUID, supplier_payment_id: uuid.UUID
    ) -> None:
        assert await repo.get_allocation_by_id(uuid.uuid4(), supplier_payment_id, tenant_id) is None


class TestListAllocations:
    async def test_returns_every_allocation_oldest_first(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        supplier_payment_id: uuid.UUID,
    ) -> None:
        bill_a = await _make_purchase_bill(db_session, tenant_id, supplier_id)
        bill_b = await _make_purchase_bill(db_session, tenant_id, supplier_id)
        first = await _make_allocation(db_session, tenant_id, supplier_payment_id, bill_a.id)
        second = await _make_allocation(db_session, tenant_id, supplier_payment_id, bill_b.id)

        rows = await repo.list_allocations(supplier_payment_id, tenant_id)
        assert [r.id for r in rows] == [first.id, second.id]

    async def test_scoped_to_one_supplier_payment(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        supplier_payment_id: uuid.UUID,
        purchase_bill_id: uuid.UUID,
    ) -> None:
        target = await _make_allocation(
            db_session, tenant_id, supplier_payment_id, purchase_bill_id
        )
        other_payment = await _make_supplier_payment(db_session, tenant_id, supplier_id)
        await _make_allocation(db_session, tenant_id, other_payment.id, purchase_bill_id)

        rows = await repo.list_allocations(supplier_payment_id, tenant_id)
        assert [r.id for r in rows] == [target.id]

    async def test_empty_when_no_allocations(
        self, repo: SupplierPaymentRepository, tenant_id: uuid.UUID, supplier_payment_id: uuid.UUID
    ) -> None:
        assert await repo.list_allocations(supplier_payment_id, tenant_id) == []


class TestDeleteAllocation:
    async def test_hard_deletes_the_row(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_payment_id: uuid.UUID,
        purchase_bill_id: uuid.UUID,
    ) -> None:
        allocation = await _make_allocation(
            db_session, tenant_id, supplier_payment_id, purchase_bill_id
        )
        await repo.delete_allocation(allocation)
        await db_session.commit()

        assert (
            await repo.get_allocation_by_id(allocation.id, supplier_payment_id, tenant_id) is None
        )


class TestSumAllocatedAmount:
    async def test_sums_every_active_allocation(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        supplier_payment_id: uuid.UUID,
    ) -> None:
        bill_a = await _make_purchase_bill(db_session, tenant_id, supplier_id)
        bill_b = await _make_purchase_bill(db_session, tenant_id, supplier_id)
        await _make_allocation(
            db_session,
            tenant_id,
            supplier_payment_id,
            bill_a.id,
            allocated_amount=Decimal("300.00"),
        )
        await _make_allocation(
            db_session,
            tenant_id,
            supplier_payment_id,
            bill_b.id,
            allocated_amount=Decimal("150.50"),
        )

        total = await repo.sum_allocated_amount(supplier_payment_id, tenant_id)
        assert total == Decimal("450.50")

    async def test_zero_when_no_allocations(
        self, repo: SupplierPaymentRepository, tenant_id: uuid.UUID, supplier_payment_id: uuid.UUID
    ) -> None:
        assert await repo.sum_allocated_amount(supplier_payment_id, tenant_id) == Decimal("0")

    async def test_excludes_a_deleted_allocation(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_payment_id: uuid.UUID,
        purchase_bill_id: uuid.UUID,
    ) -> None:
        allocation = await _make_allocation(
            db_session,
            tenant_id,
            supplier_payment_id,
            purchase_bill_id,
            allocated_amount=Decimal("300.00"),
        )
        await repo.delete_allocation(allocation)
        await db_session.commit()

        assert await repo.sum_allocated_amount(supplier_payment_id, tenant_id) == Decimal("0")

    async def test_scoped_to_one_supplier_payment(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        supplier_payment_id: uuid.UUID,
        purchase_bill_id: uuid.UUID,
    ) -> None:
        await _make_allocation(
            db_session,
            tenant_id,
            supplier_payment_id,
            purchase_bill_id,
            allocated_amount=Decimal("300.00"),
        )
        other_payment = await _make_supplier_payment(db_session, tenant_id, supplier_id)
        await _make_allocation(
            db_session,
            tenant_id,
            other_payment.id,
            purchase_bill_id,
            allocated_amount=Decimal("999.00"),
        )

        assert await repo.sum_allocated_amount(supplier_payment_id, tenant_id) == Decimal("300.00")


class TestSumAllocatedAmountByPurchaseBill:
    """Sprint 12 Session 4's outstanding engine input - unlike
    sum_allocated_amount (scoped to one supplier payment), this sums across
    every supplier payment that allocates to one purchase bill."""

    async def test_sums_across_multiple_supplier_payments(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        purchase_bill_id: uuid.UUID,
    ) -> None:
        payment_a = await _make_supplier_payment(db_session, tenant_id, supplier_id)
        payment_b = await _make_supplier_payment(db_session, tenant_id, supplier_id)
        await _make_allocation(
            db_session,
            tenant_id,
            payment_a.id,
            purchase_bill_id,
            allocated_amount=Decimal("300.00"),
        )
        await _make_allocation(
            db_session,
            tenant_id,
            payment_b.id,
            purchase_bill_id,
            allocated_amount=Decimal("150.50"),
        )

        total = await repo.sum_allocated_amount_by_purchase_bill(purchase_bill_id, tenant_id)
        assert total == Decimal("450.50")

    async def test_zero_when_no_allocations(
        self, repo: SupplierPaymentRepository, tenant_id: uuid.UUID, purchase_bill_id: uuid.UUID
    ) -> None:
        assert await repo.sum_allocated_amount_by_purchase_bill(
            purchase_bill_id, tenant_id
        ) == Decimal("0")

    async def test_excludes_a_deleted_allocation(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_payment_id: uuid.UUID,
        purchase_bill_id: uuid.UUID,
    ) -> None:
        allocation = await _make_allocation(
            db_session,
            tenant_id,
            supplier_payment_id,
            purchase_bill_id,
            allocated_amount=Decimal("300.00"),
        )
        await repo.delete_allocation(allocation)
        await db_session.commit()

        assert await repo.sum_allocated_amount_by_purchase_bill(
            purchase_bill_id, tenant_id
        ) == Decimal("0")

    async def test_scoped_to_one_purchase_bill(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        supplier_payment_id: uuid.UUID,
        purchase_bill_id: uuid.UUID,
    ) -> None:
        await _make_allocation(
            db_session,
            tenant_id,
            supplier_payment_id,
            purchase_bill_id,
            allocated_amount=Decimal("300.00"),
        )
        other_bill = await _make_purchase_bill(db_session, tenant_id, supplier_id)
        await _make_allocation(
            db_session,
            tenant_id,
            supplier_payment_id,
            other_bill.id,
            allocated_amount=Decimal("999.00"),
        )

        assert await repo.sum_allocated_amount_by_purchase_bill(
            purchase_bill_id, tenant_id
        ) == Decimal("300.00")

    async def test_scoped_to_one_tenant(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_payment_id: uuid.UUID,
        purchase_bill_id: uuid.UUID,
    ) -> None:
        await _make_allocation(
            db_session,
            tenant_id,
            supplier_payment_id,
            purchase_bill_id,
            allocated_amount=Decimal("300.00"),
        )
        assert await repo.sum_allocated_amount_by_purchase_bill(
            purchase_bill_id, uuid.uuid4()
        ) == Decimal("0")


class TestGetByIdForUpdate:
    """The Session 5 posting workflow's locked lookup - same scoping rules
    as get_by_id, plus a row lock. Functional correctness (does it find/
    scope the same way) is what's testable here; the actual lock's effect
    on a concurrent transaction isn't exercised by this single-session
    suite."""

    async def test_finds_payment_in_own_tenant(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        payment = await _make_supplier_payment(
            db_session, tenant_id, supplier_id, remarks="Lockable"
        )
        found = await repo.get_by_id_for_update(payment.id, tenant_id)
        assert found is not None
        assert found.remarks == "Lockable"

    async def test_returns_none_for_a_different_tenant(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        payment = await _make_supplier_payment(db_session, tenant_id, supplier_id)
        assert await repo.get_by_id_for_update(payment.id, uuid.uuid4()) is None

    async def test_returns_none_for_unknown_id(
        self, repo: SupplierPaymentRepository, tenant_id: uuid.UUID
    ) -> None:
        assert await repo.get_by_id_for_update(uuid.uuid4(), tenant_id) is None

    async def test_excludes_soft_deleted_rows(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        payment = await _make_supplier_payment(
            db_session, tenant_id, supplier_id, deleted_at=datetime.now(UTC)
        )
        assert await repo.get_by_id_for_update(payment.id, tenant_id) is None

    async def test_mutations_on_the_locked_row_persist_after_commit(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> None:
        payment = await _make_supplier_payment(db_session, tenant_id, supplier_id)
        locked = await repo.get_by_id_for_update(payment.id, tenant_id)
        assert locked is not None
        locked.payment_number = "SPAY/2026-27/00001"
        locked.status = SupplierPaymentStatus.POSTED
        await db_session.commit()

        refetched = await repo.get_by_id(payment.id, tenant_id)
        assert refetched is not None
        assert refetched.payment_number == "SPAY/2026-27/00001"
        assert refetched.status == SupplierPaymentStatus.POSTED


class TestHasAllocations:
    """Sprint 12 Session 5 posting workflow's "must have at least one
    allocation" existence check."""

    async def test_true_when_at_least_one_allocation_exists(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_payment_id: uuid.UUID,
        purchase_bill_id: uuid.UUID,
    ) -> None:
        await _make_allocation(db_session, tenant_id, supplier_payment_id, purchase_bill_id)
        assert await repo.has_allocations(supplier_payment_id, tenant_id) is True

    async def test_false_when_no_allocations(
        self, repo: SupplierPaymentRepository, tenant_id: uuid.UUID, supplier_payment_id: uuid.UUID
    ) -> None:
        assert await repo.has_allocations(supplier_payment_id, tenant_id) is False

    async def test_false_after_the_only_allocation_is_deleted(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_payment_id: uuid.UUID,
        purchase_bill_id: uuid.UUID,
    ) -> None:
        allocation = await _make_allocation(
            db_session, tenant_id, supplier_payment_id, purchase_bill_id
        )
        await repo.delete_allocation(allocation)
        await db_session.commit()
        assert await repo.has_allocations(supplier_payment_id, tenant_id) is False

    async def test_scoped_to_one_tenant(
        self,
        repo: SupplierPaymentRepository,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_payment_id: uuid.UUID,
        purchase_bill_id: uuid.UUID,
    ) -> None:
        await _make_allocation(db_session, tenant_id, supplier_payment_id, purchase_bill_id)
        assert await repo.has_allocations(supplier_payment_id, uuid.uuid4()) is False


class TestSequenceRow:
    """The Session 5 posting workflow's supplier payment numbering counter -
    ensure_sequence_row (`INSERT ... ON CONFLICT DO NOTHING`) followed by
    get_sequence_for_update (`SELECT ... FOR UPDATE`). Mirrors
    PurchaseRepository's own TestSequenceRow exactly."""

    async def test_ensure_creates_a_row_starting_at_zero(
        self, repo: SupplierPaymentRepository, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "SPAY", "2026-27")
        sequence = await repo.get_sequence_for_update(tenant_id, "SPAY", "2026-27")
        assert sequence.last_number == 0

    async def test_ensure_is_idempotent_and_does_not_reset_an_existing_counter(
        self, repo: SupplierPaymentRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "SPAY", "2026-27")
        sequence = await repo.get_sequence_for_update(tenant_id, "SPAY", "2026-27")
        sequence.last_number += 1
        await db_session.commit()

        # A second ensure_sequence_row call (as post() makes on every
        # supplier payment, not just the first per fiscal year) must not
        # clobber the counter back to zero.
        await repo.ensure_sequence_row(tenant_id, "SPAY", "2026-27")
        relocked = await repo.get_sequence_for_update(tenant_id, "SPAY", "2026-27")
        assert relocked.last_number == 1

    async def test_increment_persists_after_commit(
        self, repo: SupplierPaymentRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "SPAY", "2026-27")
        sequence = await repo.get_sequence_for_update(tenant_id, "SPAY", "2026-27")
        sequence.last_number += 1
        await db_session.commit()

        result = await db_session.execute(
            select(SupplierPaymentSequence).where(
                SupplierPaymentSequence.tenant_id == tenant_id,
                SupplierPaymentSequence.prefix == "SPAY",
                SupplierPaymentSequence.fiscal_year == "2026-27",
            )
        )
        assert result.scalar_one().last_number == 1

    async def test_different_fiscal_years_are_independent_counters(
        self, repo: SupplierPaymentRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await repo.ensure_sequence_row(tenant_id, "SPAY", "2025-26")
        early = await repo.get_sequence_for_update(tenant_id, "SPAY", "2025-26")
        early.last_number += 1
        await db_session.commit()

        await repo.ensure_sequence_row(tenant_id, "SPAY", "2026-27")
        late = await repo.get_sequence_for_update(tenant_id, "SPAY", "2026-27")
        assert late.last_number == 0

    async def test_different_tenants_are_independent_counters(
        self, repo: SupplierPaymentRepository, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(
            name="Other Supplier Payment Sequence Tenant",
            slug=f"other-sp-seq-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        await db_session.commit()

        await repo.ensure_sequence_row(tenant_id, "SPAY", "2026-27")
        mine = await repo.get_sequence_for_update(tenant_id, "SPAY", "2026-27")
        mine.last_number += 1
        await db_session.commit()

        await repo.ensure_sequence_row(other_tenant.id, "SPAY", "2026-27")
        theirs = await repo.get_sequence_for_update(other_tenant.id, "SPAY", "2026-27")
        assert theirs.last_number == 0
