import uuid
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import hash_password
from app.modules.purchase.schemas import (
    PurchaseBillCreateRequest,
    PurchaseBillItemCreateRequest,
)
from app.modules.purchase.service import PurchaseService
from app.modules.supplier_payments.constants import SupplierPaymentStatus
from app.modules.supplier_payments.exceptions import (
    SupplierPaymentAllocationPaymentNotDraftError,
    SupplierPaymentNoAllocationsError,
    SupplierPaymentNotDraftError,
    SupplierPaymentNotFoundError,
)
from app.modules.supplier_payments.models import SupplierPayment
from app.modules.supplier_payments.schemas import (
    SupplierPaymentAllocationCreateRequest,
    SupplierPaymentAllocationUpdateRequest,
    SupplierPaymentCreateRequest,
    SupplierPaymentUpdateRequest,
)
from app.modules.supplier_payments.service import SupplierPaymentService
from app.modules.suppliers.models import Supplier

_BILL_DATE = date(2026, 7, 22)
_PAYMENT_DATE = date(2026, 7, 23)


@pytest.fixture
def supplier_payment_service(db_session: AsyncSession) -> SupplierPaymentService:
    return SupplierPaymentService(db_session)


@pytest.fixture
def purchase_service(db_session: AsyncSession) -> PurchaseService:
    return PurchaseService(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - keeps every assertion independent of
    whatever else exists in the seeded default tenant."""
    tenant = Tenant(
        name="Supplier Payment Post Test Tenant",
        slug=f"supplier-payment-post-test-{uuid.uuid4().hex[:8]}",
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


async def _posted_purchase_bill(
    purchase_service: PurchaseService,
    *,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID,
    actor_id: uuid.UUID,
    quantity: Decimal = Decimal("10.000"),
    rate: Decimal = Decimal("100.0000"),
) -> Any:
    """A fully posted purchase bill with a known balance_amount (quantity x
    rate, no tax/discount) - the default 10 x 100 = 1000.00."""
    bill = await purchase_service.create(
        PurchaseBillCreateRequest(supplier_id=supplier_id, bill_date=_BILL_DATE),
        tenant_id=tenant_id,
        actor_id=actor_id,
    )
    await purchase_service.add_item(
        bill.id,
        PurchaseBillItemCreateRequest(
            description="Pomfret - Grade A", quantity=quantity, unit="KG", rate=rate
        ),
        tenant_id=tenant_id,
    )
    return await purchase_service.post(bill.id, tenant_id=tenant_id, actor_id=actor_id)


async def _draft_supplier_payment_with_allocation(
    supplier_payment_service: SupplierPaymentService,
    *,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID,
    purchase_bill_id: uuid.UUID,
    actor_id: uuid.UUID,
    amount: Decimal = Decimal("1000.00"),
    allocated_amount: Decimal = Decimal("1000.00"),
) -> Any:
    payment = await supplier_payment_service.create(
        SupplierPaymentCreateRequest(
            supplier_id=supplier_id,
            payment_date=_PAYMENT_DATE,
            payment_method="cheque",
            amount=amount,
        ),
        tenant_id=tenant_id,
        actor_id=actor_id,
    )
    await supplier_payment_service.create_allocation(
        payment.id,
        SupplierPaymentAllocationCreateRequest(
            purchase_bill_id=purchase_bill_id, allocated_amount=allocated_amount
        ),
        tenant_id=tenant_id,
        actor_id=actor_id,
    )
    return payment


class TestSuccessfulPost:
    async def test_transitions_draft_to_posted(
        self,
        supplier_payment_service: SupplierPaymentService,
        purchase_service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _posted_purchase_bill(
            purchase_service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        payment = await _draft_supplier_payment_with_allocation(
            supplier_payment_service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            purchase_bill_id=bill.id,
            actor_id=actor_id,
        )

        posted = await supplier_payment_service.post(
            payment.id, tenant_id=tenant_id, actor_id=actor_id
        )

        assert posted.status == SupplierPaymentStatus.POSTED
        assert posted.payment_number == "SPAY/2026-27/00001"
        assert posted.allocated_amount == Decimal("1000.00")
        assert posted.unallocated_amount == Decimal("0.00")
        assert posted.posted_at is not None

    async def test_second_payment_in_the_same_fiscal_year_gets_the_next_number(
        self,
        supplier_payment_service: SupplierPaymentService,
        purchase_service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill_a = await _posted_purchase_bill(
            purchase_service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        payment_a = await _draft_supplier_payment_with_allocation(
            supplier_payment_service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            purchase_bill_id=bill_a.id,
            actor_id=actor_id,
        )
        posted_a = await supplier_payment_service.post(
            payment_a.id, tenant_id=tenant_id, actor_id=actor_id
        )
        assert posted_a.payment_number == "SPAY/2026-27/00001"

        bill_b = await _posted_purchase_bill(
            purchase_service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        payment_b = await _draft_supplier_payment_with_allocation(
            supplier_payment_service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            purchase_bill_id=bill_b.id,
            actor_id=actor_id,
        )
        posted_b = await supplier_payment_service.post(
            payment_b.id, tenant_id=tenant_id, actor_id=actor_id
        )
        assert posted_b.payment_number == "SPAY/2026-27/00002"

    async def test_partial_allocation_still_posts_with_the_correct_totals(
        self,
        supplier_payment_service: SupplierPaymentService,
        purchase_service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _posted_purchase_bill(
            purchase_service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        payment = await _draft_supplier_payment_with_allocation(
            supplier_payment_service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            purchase_bill_id=bill.id,
            actor_id=actor_id,
            amount=Decimal("1000.00"),
            allocated_amount=Decimal("400.00"),
        )

        posted = await supplier_payment_service.post(
            payment.id, tenant_id=tenant_id, actor_id=actor_id
        )

        assert posted.allocated_amount == Decimal("400.00")
        assert posted.unallocated_amount == Decimal("600.00")

    async def test_does_not_touch_purchase_bill_or_supplier_financials(
        self,
        supplier_payment_service: SupplierPaymentService,
        purchase_service: PurchaseService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        """Session 4's outstanding engine already keeps
        PurchaseBill.paid_amount/balance_amount/status and
        Supplier.outstanding_amount correct as of every allocation change
        made while the payment was draft - post() must leave them exactly
        as they were."""
        bill = await _posted_purchase_bill(
            purchase_service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        payment = await _draft_supplier_payment_with_allocation(
            supplier_payment_service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            purchase_bill_id=bill.id,
            actor_id=actor_id,
        )
        before_bill = await purchase_service.get(bill.id, tenant_id=tenant_id)
        before_supplier_row = (
            await db_session.execute(select(Supplier).where(Supplier.id == supplier_id))
        ).scalar_one()
        before_outstanding = before_supplier_row.outstanding_amount

        await supplier_payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        after_bill = await purchase_service.get(bill.id, tenant_id=tenant_id)
        after_supplier_row = (
            await db_session.execute(select(Supplier).where(Supplier.id == supplier_id))
        ).scalar_one()
        assert after_bill.status == before_bill.status
        assert after_bill.paid_amount == before_bill.paid_amount
        assert after_bill.balance_amount == before_bill.balance_amount
        assert after_supplier_row.outstanding_amount == before_outstanding


class TestDoublePost:
    async def test_posting_an_already_posted_payment_raises_not_draft(
        self,
        supplier_payment_service: SupplierPaymentService,
        purchase_service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _posted_purchase_bill(
            purchase_service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        payment = await _draft_supplier_payment_with_allocation(
            supplier_payment_service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            purchase_bill_id=bill.id,
            actor_id=actor_id,
        )
        await supplier_payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(SupplierPaymentNotDraftError):
            await supplier_payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

    async def test_double_post_does_not_assign_a_second_number(
        self,
        supplier_payment_service: SupplierPaymentService,
        purchase_service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _posted_purchase_bill(
            purchase_service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        payment = await _draft_supplier_payment_with_allocation(
            supplier_payment_service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            purchase_bill_id=bill.id,
            actor_id=actor_id,
        )
        posted = await supplier_payment_service.post(
            payment.id, tenant_id=tenant_id, actor_id=actor_id
        )

        with pytest.raises(SupplierPaymentNotDraftError):
            await supplier_payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        refetched = await supplier_payment_service.get(payment.id, tenant_id=tenant_id)
        assert refetched.payment_number == posted.payment_number

    async def test_cannot_post_a_cancelled_payment(
        self,
        supplier_payment_service: SupplierPaymentService,
        purchase_service: PurchaseService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _posted_purchase_bill(
            purchase_service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        payment = await _draft_supplier_payment_with_allocation(
            supplier_payment_service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            purchase_bill_id=bill.id,
            actor_id=actor_id,
        )
        row = (
            await db_session.execute(
                select(SupplierPayment).where(SupplierPayment.id == payment.id)
            )
        ).scalar_one()
        row.status = SupplierPaymentStatus.CANCELLED
        await db_session.commit()

        with pytest.raises(SupplierPaymentNotDraftError):
            await supplier_payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)


class TestEmptyAllocation:
    async def test_raises_no_allocations_for_a_draft_with_none(
        self,
        supplier_payment_service: SupplierPaymentService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        payment = await supplier_payment_service.create(
            SupplierPaymentCreateRequest(
                supplier_id=supplier_id,
                payment_date=_PAYMENT_DATE,
                payment_method="cheque",
                amount=Decimal("1000.00"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

        with pytest.raises(SupplierPaymentNoAllocationsError):
            await supplier_payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

    async def test_raises_no_allocations_when_the_only_allocation_was_removed(
        self,
        supplier_payment_service: SupplierPaymentService,
        purchase_service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _posted_purchase_bill(
            purchase_service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        payment = await _draft_supplier_payment_with_allocation(
            supplier_payment_service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            purchase_bill_id=bill.id,
            actor_id=actor_id,
        )
        allocations = await supplier_payment_service.list_allocations(
            payment.id, tenant_id=tenant_id
        )
        await supplier_payment_service.delete_allocation(
            payment.id, allocations[0].id, tenant_id=tenant_id
        )

        with pytest.raises(SupplierPaymentNoAllocationsError):
            await supplier_payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

    async def test_failed_post_leaves_the_payment_as_draft_without_a_number(
        self,
        supplier_payment_service: SupplierPaymentService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        payment = await supplier_payment_service.create(
            SupplierPaymentCreateRequest(
                supplier_id=supplier_id,
                payment_date=_PAYMENT_DATE,
                payment_method="cheque",
                amount=Decimal("1000.00"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

        with pytest.raises(SupplierPaymentNoAllocationsError):
            await supplier_payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        refetched = await supplier_payment_service.get(payment.id, tenant_id=tenant_id)
        assert refetched.status == SupplierPaymentStatus.DRAFT
        assert refetched.payment_number is None


class TestRollbackBehaviour:
    async def test_a_failed_post_does_not_leak_a_sequence_number(
        self,
        supplier_payment_service: SupplierPaymentService,
        purchase_service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        """A payment number is only ever generated after every validation
        passes (post()'s step 8 comes after steps 4/5/7) - a failed attempt
        must never punch a hole in the sequence."""
        payment = await supplier_payment_service.create(
            SupplierPaymentCreateRequest(
                supplier_id=supplier_id,
                payment_date=_PAYMENT_DATE,
                payment_method="cheque",
                amount=Decimal("1000.00"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        with pytest.raises(SupplierPaymentNoAllocationsError):
            await supplier_payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        bill = await _posted_purchase_bill(
            purchase_service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        good_payment = await _draft_supplier_payment_with_allocation(
            supplier_payment_service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            purchase_bill_id=bill.id,
            actor_id=actor_id,
        )
        posted = await supplier_payment_service.post(
            good_payment.id, tenant_id=tenant_id, actor_id=actor_id
        )

        # The failed attempt above must not have consumed sequence number 1.
        assert posted.payment_number == "SPAY/2026-27/00001"

    async def test_failed_post_rolls_back_and_the_payment_remains_editable(
        self,
        supplier_payment_service: SupplierPaymentService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        payment = await supplier_payment_service.create(
            SupplierPaymentCreateRequest(
                supplier_id=supplier_id,
                payment_date=_PAYMENT_DATE,
                payment_method="cheque",
                amount=Decimal("1000.00"),
            ),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        with pytest.raises(SupplierPaymentNoAllocationsError):
            await supplier_payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        # A draft payment is still editable after a failed post attempt -
        # proof the explicit rollback didn't leave the session/transaction
        # in a broken state.
        updated = await supplier_payment_service.update(
            payment.id,
            SupplierPaymentUpdateRequest(remarks="Still editable"),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        assert updated.remarks == "Still editable"


class TestImmutabilityAfterPost:
    async def test_posted_payment_cannot_be_updated(
        self,
        supplier_payment_service: SupplierPaymentService,
        purchase_service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _posted_purchase_bill(
            purchase_service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        payment = await _draft_supplier_payment_with_allocation(
            supplier_payment_service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            purchase_bill_id=bill.id,
            actor_id=actor_id,
        )
        await supplier_payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(SupplierPaymentNotDraftError):
            await supplier_payment_service.update(
                payment.id,
                SupplierPaymentUpdateRequest(remarks="Trying to edit"),
                tenant_id=tenant_id,
                actor_id=actor_id,
            )

    async def test_posted_payment_cannot_be_deleted(
        self,
        supplier_payment_service: SupplierPaymentService,
        purchase_service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _posted_purchase_bill(
            purchase_service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        payment = await _draft_supplier_payment_with_allocation(
            supplier_payment_service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            purchase_bill_id=bill.id,
            actor_id=actor_id,
        )
        await supplier_payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(SupplierPaymentNotDraftError):
            await supplier_payment_service.delete(
                payment.id, tenant_id=tenant_id, actor_id=actor_id
            )

    async def test_posted_payment_allocations_cannot_be_created_updated_or_deleted(
        self,
        supplier_payment_service: SupplierPaymentService,
        purchase_service: PurchaseService,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await _posted_purchase_bill(
            purchase_service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        other_bill = await _posted_purchase_bill(
            purchase_service, tenant_id=tenant_id, supplier_id=supplier_id, actor_id=actor_id
        )
        payment = await _draft_supplier_payment_with_allocation(
            supplier_payment_service,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            purchase_bill_id=bill.id,
            actor_id=actor_id,
        )
        allocations = await supplier_payment_service.list_allocations(
            payment.id, tenant_id=tenant_id
        )
        allocation_id = allocations[0].id
        await supplier_payment_service.post(payment.id, tenant_id=tenant_id, actor_id=actor_id)

        with pytest.raises(SupplierPaymentAllocationPaymentNotDraftError):
            await supplier_payment_service.create_allocation(
                payment.id,
                SupplierPaymentAllocationCreateRequest(
                    purchase_bill_id=other_bill.id, allocated_amount=Decimal("1.00")
                ),
                tenant_id=tenant_id,
                actor_id=actor_id,
            )

        with pytest.raises(SupplierPaymentAllocationPaymentNotDraftError):
            await supplier_payment_service.update_allocation(
                payment.id,
                allocation_id,
                SupplierPaymentAllocationUpdateRequest(allocated_amount=Decimal("1.00")),
                tenant_id=tenant_id,
            )

        with pytest.raises(SupplierPaymentAllocationPaymentNotDraftError):
            await supplier_payment_service.delete_allocation(
                payment.id, allocation_id, tenant_id=tenant_id
            )

    async def test_posting_belonging_to_another_tenant_is_not_found(
        self,
        supplier_payment_service: SupplierPaymentService,
        tenant_id: uuid.UUID,
    ) -> None:
        with pytest.raises(SupplierPaymentNotFoundError):
            await supplier_payment_service.post(
                uuid.uuid4(), tenant_id=tenant_id, actor_id=uuid.uuid4()
            )
