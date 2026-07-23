import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import hash_password
from app.modules.purchase.constants import PurchaseStatus
from app.modules.purchase.exceptions import (
    PurchaseBillEmptyError,
    PurchaseBillNotDraftError,
    PurchaseTotalsInvalidError,
)
from app.modules.purchase.models import PurchaseBill, PurchaseBillItem
from app.modules.purchase.schemas import (
    PurchaseBillCreateRequest,
    PurchaseBillItemCreateRequest,
    PurchaseBillItemUpdateRequest,
    PurchaseBillUpdateRequest,
)
from app.modules.purchase.service import PurchaseService
from app.modules.suppliers.models import Supplier

_BILL_DATE = date(2026, 7, 22)


@pytest.fixture
def service(db_session: AsyncSession) -> PurchaseService:
    return PurchaseService(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - keeps every assertion independent of
    whatever else exists in the seeded default tenant."""
    tenant = Tenant(
        name="Purchase Posting Test Tenant", slug=f"purchase-posting-test-{uuid.uuid4().hex[:8]}"
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant.id


@pytest.fixture
async def actor_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    """created_by/updated_by are real FKs to users.id, so PurchaseService
    calls (unlike HTTP-level tests) need an actual user row."""
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


async def _make_supplier(
    db_session: AsyncSession, tenant_id: uuid.UUID, **overrides: object
) -> Supplier:
    defaults: dict[str, object] = {
        "tenant_id": tenant_id,
        "code": f"SUP-{uuid.uuid4().hex[:8]}",
        "name": f"Supplier {uuid.uuid4().hex[:8]}",
    }
    defaults.update(overrides)
    supplier = Supplier(**defaults)  # type: ignore[arg-type]
    db_session.add(supplier)
    await db_session.commit()
    return supplier


@pytest.fixture
async def supplier_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    supplier = await _make_supplier(db_session, tenant_id)
    return supplier.id


async def _draft_bill_with_item(
    service: PurchaseService,
    *,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID,
    actor_id: uuid.UUID,
    quantity: Decimal = Decimal("10.000"),
    rate: Decimal = Decimal("100.0000"),
    tax_rate: Decimal = Decimal("0"),
    bill_date: date = _BILL_DATE,
) -> object:
    bill = await service.create(
        PurchaseBillCreateRequest(supplier_id=supplier_id, bill_date=bill_date),
        tenant_id=tenant_id,
        actor_id=actor_id,
    )
    await service.add_item(
        bill.id,
        PurchaseBillItemCreateRequest(
            description="Item", quantity=quantity, unit="KG", rate=rate, tax_rate=tax_rate
        ),
        tenant_id=tenant_id,
    )
    return bill


class TestSuccessfulPost:
    async def test_transitions_draft_to_posted(
        self,
        service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _draft_bill_with_item(
            service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )

        posted = await service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)

        assert posted.status == PurchaseStatus.POSTED
        assert posted.bill_number == "PUR/2026-27/00001"

    async def test_posted_at_is_populated(
        self,
        service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _draft_bill_with_item(
            service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        assert bill.posted_at is None

        before = datetime.now(UTC)
        posted = await service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)
        after = datetime.now(UTC)

        assert posted.posted_at is not None
        assert before <= posted.posted_at <= after

    async def test_second_bill_in_the_same_fiscal_year_gets_the_next_number(
        self,
        service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill_a = await _draft_bill_with_item(
            service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        posted_a = await service.post(bill_a.id, tenant_id=tenant_id, actor_id=actor_id)
        assert posted_a.bill_number == "PUR/2026-27/00001"

        bill_b = await _draft_bill_with_item(
            service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        posted_b = await service.post(bill_b.id, tenant_id=tenant_id, actor_id=actor_id)
        assert posted_b.bill_number == "PUR/2026-27/00002"

    async def test_recalculates_totals_immediately_before_post(
        self,
        service: PurchaseService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        """Even if a line's stored total were somehow stale, post() must
        never trust it - it always recomputes from quantity/rate/discount/
        tax immediately before posting."""
        bill = await _draft_bill_with_item(
            service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            actor_id=actor_id,
            quantity=Decimal("50.000"),
            rate=Decimal("450.0000"),
            tax_rate=Decimal("5.00"),
        )
        # Correct line_total is 23625.00 - corrupt it directly via the ORM,
        # bypassing the service entirely, to prove post() doesn't trust it.
        result = await db_session.execute(
            select(PurchaseBillItem).where(PurchaseBillItem.purchase_bill_id == bill.id)
        )
        item = result.scalar_one()
        item.line_total = Decimal("1.00")
        await db_session.commit()

        posted = await service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)

        assert posted.total_amount == Decimal("23625.00")
        assert posted.balance_amount == Decimal("23625.00")


class TestDoublePost:
    async def test_posting_an_already_posted_bill_raises_not_draft(
        self,
        service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _draft_bill_with_item(
            service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        await service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(PurchaseBillNotDraftError):
            await service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)

    async def test_double_post_does_not_double_credit_supplier_outstanding(
        self,
        service: PurchaseService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _draft_bill_with_item(
            service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        posted = await service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(PurchaseBillNotDraftError):
            await service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)

        supplier_row = (
            await db_session.execute(select(Supplier).where(Supplier.id == supplier_id))
        ).scalar_one()
        assert supplier_row.outstanding_amount == posted.balance_amount

    async def test_cannot_post_a_cancelled_bill(
        self,
        service: PurchaseService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _draft_bill_with_item(
            service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        row = (
            await db_session.execute(select(PurchaseBill).where(PurchaseBill.id == bill.id))
        ).scalar_one()
        row.status = PurchaseStatus.CANCELLED
        await db_session.commit()

        with pytest.raises(PurchaseBillNotDraftError):
            await service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)


class TestEmptyBill:
    async def test_raises_empty_for_a_draft_with_no_items(
        self,
        service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await service.create(
            PurchaseBillCreateRequest(supplier_id=supplier_id, bill_date=_BILL_DATE),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

        with pytest.raises(PurchaseBillEmptyError):
            await service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)

    async def test_raises_empty_when_the_only_item_was_deleted(
        self,
        service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _draft_bill_with_item(
            service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        items = await service.list_items(bill.id, tenant_id=tenant_id, q=None, sort="line_number")
        await service.delete_item(bill.id, items[0].id, tenant_id=tenant_id)

        with pytest.raises(PurchaseBillEmptyError):
            await service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)

    async def test_empty_bill_is_not_left_mutated_after_the_failed_attempt(
        self,
        service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await service.create(
            PurchaseBillCreateRequest(supplier_id=supplier_id, bill_date=_BILL_DATE),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

        with pytest.raises(PurchaseBillEmptyError):
            await service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)

        refetched = await service.get(bill.id, tenant_id=tenant_id)
        assert refetched.status == PurchaseStatus.DRAFT
        assert refetched.bill_number is None


class TestRollbackBehaviour:
    async def test_totals_overflow_rolls_back_the_whole_transaction(
        self,
        service: PurchaseService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        """quantity (up to 12,3) and rate (up to 12,4) are independently
        bounded by the request schema, but their product is not - corrupt
        an existing item directly via the ORM, bypassing those bounds
        entirely, to force the final pre-post recalculation to overflow.
        The whole transaction (status/bill_number/posted_at/supplier
        outstanding) must roll back together."""
        bill = await _draft_bill_with_item(
            service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        result = await db_session.execute(
            select(PurchaseBillItem).where(PurchaseBillItem.purchase_bill_id == bill.id)
        )
        item = result.scalar_one()
        item.quantity = Decimal("999999999.999")
        item.rate = Decimal("99999999.9999")
        await db_session.commit()

        with pytest.raises(PurchaseTotalsInvalidError):
            await service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)

        # post()'s explicit rollback on failure expires every object in this
        # shared session's identity map - re-query rather than touching the
        # expired objects' attributes.
        refetched = await service.get(bill.id, tenant_id=tenant_id)
        assert refetched.status == PurchaseStatus.DRAFT
        assert refetched.bill_number is None
        assert refetched.posted_at is None

        supplier_row = (
            await db_session.execute(select(Supplier).where(Supplier.id == supplier_id))
        ).scalar_one()
        assert supplier_row.outstanding_amount == Decimal("0.00")


class TestSupplierOutstandingUpdated:
    async def test_increases_outstanding_by_the_posted_balance(
        self,
        service: PurchaseService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _draft_bill_with_item(
            service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            actor_id=actor_id,
            quantity=Decimal("50.000"),
            rate=Decimal("450.0000"),
            tax_rate=Decimal("5.00"),
        )

        posted = await service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)

        supplier_row = (
            await db_session.execute(select(Supplier).where(Supplier.id == supplier_id))
        ).scalar_one()
        assert supplier_row.outstanding_amount == posted.balance_amount
        assert posted.balance_amount == Decimal("23625.00")

    async def test_accumulates_across_multiple_posted_bills_for_the_same_supplier(
        self,
        service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
        db_session: AsyncSession,
    ) -> None:
        bill_a = await _draft_bill_with_item(
            service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            actor_id=actor_id,
            quantity=Decimal("10.000"),
            rate=Decimal("100.0000"),
        )
        posted_a = await service.post(bill_a.id, tenant_id=tenant_id, actor_id=actor_id)

        bill_b = await _draft_bill_with_item(
            service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            actor_id=actor_id,
            quantity=Decimal("20.000"),
            rate=Decimal("100.0000"),
        )
        posted_b = await service.post(bill_b.id, tenant_id=tenant_id, actor_id=actor_id)

        supplier_row = (
            await db_session.execute(select(Supplier).where(Supplier.id == supplier_id))
        ).scalar_one()
        assert supplier_row.outstanding_amount == posted_a.balance_amount + posted_b.balance_amount
        assert supplier_row.outstanding_amount == Decimal("3000.00")

    async def test_does_not_affect_other_suppliers(
        self,
        service: PurchaseService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        other_supplier = await _make_supplier(db_session, tenant_id)
        bill = await _draft_bill_with_item(
            service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        await service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)

        other_row = (
            await db_session.execute(select(Supplier).where(Supplier.id == other_supplier.id))
        ).scalar_one()
        assert other_row.outstanding_amount == Decimal("0.00")


class TestPurchaseNumberSequence:
    async def test_different_fiscal_years_get_independent_sequences(
        self,
        service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        early_bill = await _draft_bill_with_item(
            service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            actor_id=actor_id,
            bill_date=date(2026, 3, 15),  # FY 2025-26
        )
        posted_early = await service.post(early_bill.id, tenant_id=tenant_id, actor_id=actor_id)
        assert posted_early.bill_number == "PUR/2025-26/00001"

        late_bill = await _draft_bill_with_item(
            service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            actor_id=actor_id,
            bill_date=date(2026, 7, 22),  # FY 2026-27
        )
        posted_late = await service.post(late_bill.id, tenant_id=tenant_id, actor_id=actor_id)
        assert posted_late.bill_number == "PUR/2026-27/00001"

    async def test_different_tenants_get_independent_sequences(
        self,
        service: PurchaseService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _draft_bill_with_item(
            service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        posted = await service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)
        assert posted.bill_number == "PUR/2026-27/00001"

        other_tenant = Tenant(
            name="Other Posting Tenant", slug=f"other-posting-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        other_user = User(
            tenant_id=other_tenant.id,
            email=f"other-post-{uuid.uuid4().hex[:8]}@fisherp.local",
            username=f"other-post-{uuid.uuid4().hex[:8]}",
            password_hash=hash_password("Whatever@123"),
            full_name="Other Tenant User",
            status=AccountStatus.ACTIVE,
            is_superuser=False,
        )
        db_session.add(other_user)
        await db_session.commit()
        other_supplier = await _make_supplier(db_session, other_tenant.id)

        other_bill = await _draft_bill_with_item(
            service,
            tenant_id=other_tenant.id,
            supplier_id=other_supplier.id,
            actor_id=other_user.id,
        )
        other_posted = await service.post(
            other_bill.id, tenant_id=other_tenant.id, actor_id=other_user.id
        )
        assert other_posted.bill_number == "PUR/2026-27/00001"


class TestImmutabilityAfterPost:
    async def test_posted_bill_cannot_be_updated(
        self,
        service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _draft_bill_with_item(
            service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        await service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(PurchaseBillNotDraftError):
            await service.update(
                bill.id,
                PurchaseBillUpdateRequest(remarks="Trying to edit"),
                tenant_id=tenant_id,
                actor_id=actor_id,
            )

    async def test_posted_bill_cannot_be_deleted(
        self,
        service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _draft_bill_with_item(
            service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        await service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(PurchaseBillNotDraftError):
            await service.delete(bill.id, tenant_id=tenant_id, actor_id=actor_id)

    async def test_posted_bill_items_cannot_be_added_updated_or_deleted(
        self,
        service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _draft_bill_with_item(
            service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        items = await service.list_items(bill.id, tenant_id=tenant_id, q=None, sort="line_number")
        item_id = items[0].id
        await service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(PurchaseBillNotDraftError):
            await service.add_item(
                bill.id,
                PurchaseBillItemCreateRequest(
                    description="New", quantity=Decimal("1.000"), unit="KG", rate=Decimal("1.0000")
                ),
                tenant_id=tenant_id,
            )

        with pytest.raises(PurchaseBillNotDraftError):
            await service.update_item(
                bill.id,
                item_id,
                PurchaseBillItemUpdateRequest(quantity=Decimal("1.000")),
                tenant_id=tenant_id,
            )

        with pytest.raises(PurchaseBillNotDraftError):
            await service.delete_item(bill.id, item_id, tenant_id=tenant_id)
