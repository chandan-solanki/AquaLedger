import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import hash_password
from app.modules.purchase.schemas import (
    PurchaseBillCreateRequest,
    PurchaseBillItemCreateRequest,
    PurchaseBillItemUpdateRequest,
)
from app.modules.purchase.service import PurchaseService
from app.modules.suppliers.models import Supplier

_BILL_DATE = date(2026, 7, 23)


@pytest.fixture
def service(db_session: AsyncSession) -> PurchaseService:
    return PurchaseService(db_session)


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test - keeps every assertion independent of
    whatever else exists in the seeded default tenant."""
    tenant = Tenant(
        name="Purchase Recalc Test Tenant", slug=f"purchase-recalc-test-{uuid.uuid4().hex[:8]}"
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant.id


@pytest.fixture
async def actor_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    """created_by/updated_by are real FKs to users.id, so PurchaseService
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


@pytest.fixture
async def supplier_id(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    supplier = Supplier(
        tenant_id=tenant_id,
        code=f"SUP-{uuid.uuid4().hex[:8]}",
        name=f"Supplier {uuid.uuid4().hex[:8]}",
    )
    db_session.add(supplier)
    await db_session.commit()
    return supplier.id


class TestRecalculateAfterAddItem:
    async def test_adding_first_item_sets_line_and_bill_totals(
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

        item = await service.add_item(
            bill.id,
            PurchaseBillItemCreateRequest(
                description="Pomfret - Grade A",
                quantity=Decimal("50.000"),
                unit="KG",
                rate=Decimal("450.0000"),
                tax_rate=Decimal("5.00"),
            ),
            tenant_id=tenant_id,
        )
        assert item.taxable_amount == Decimal("22500.00")
        assert item.tax_amount == Decimal("1125.00")
        assert item.line_total == Decimal("23625.00")

        refetched = await service.get(bill.id, tenant_id=tenant_id)
        assert refetched.subtotal == Decimal("23625.00")
        assert refetched.taxable_amount == Decimal("22500.00")
        assert refetched.tax_amount == Decimal("1125.00")
        assert refetched.total_amount == Decimal("23625.00")
        assert refetched.balance_amount == Decimal("23625.00")
        assert refetched.paid_amount == Decimal("0.00")

    async def test_adding_second_item_sums_both_into_bill_totals(
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
        await service.add_item(
            bill.id,
            PurchaseBillItemCreateRequest(
                description="Item 1", quantity=Decimal("10"), unit="KG", rate=Decimal("100")
            ),
            tenant_id=tenant_id,
        )
        await service.add_item(
            bill.id,
            PurchaseBillItemCreateRequest(
                description="Item 2",
                quantity=Decimal("5"),
                unit="KG",
                rate=Decimal("50"),
                discount_percent=Decimal("10"),
            ),
            tenant_id=tenant_id,
        )

        # item 1: 10*100=1000, item 2: 5*50=250 - 10% (25) = 225
        refetched = await service.get(bill.id, tenant_id=tenant_id)
        assert refetched.subtotal == Decimal("1225.00")
        assert refetched.discount_amount == Decimal("25.00")
        assert refetched.total_amount == Decimal("1225.00")


class TestRecalculateAfterUpdateItem:
    async def test_updating_quantity_recalculates_item_and_bill(
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
        item = await service.add_item(
            bill.id,
            PurchaseBillItemCreateRequest(
                description="Item", quantity=Decimal("10"), unit="KG", rate=Decimal("100")
            ),
            tenant_id=tenant_id,
        )
        assert item.line_total == Decimal("1000.00")

        updated = await service.update_item(
            bill.id,
            item.id,
            PurchaseBillItemUpdateRequest(quantity=Decimal("20")),
            tenant_id=tenant_id,
        )
        assert updated.line_total == Decimal("2000.00")

        refetched = await service.get(bill.id, tenant_id=tenant_id)
        assert refetched.subtotal == Decimal("2000.00")
        assert refetched.total_amount == Decimal("2000.00")

    async def test_updating_rate_only_still_recalculates_bill(
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
        item = await service.add_item(
            bill.id,
            PurchaseBillItemCreateRequest(
                description="Item", quantity=Decimal("10"), unit="KG", rate=Decimal("100")
            ),
            tenant_id=tenant_id,
        )

        await service.update_item(
            bill.id,
            item.id,
            PurchaseBillItemUpdateRequest(rate=Decimal("150")),
            tenant_id=tenant_id,
        )

        refetched = await service.get(bill.id, tenant_id=tenant_id)
        assert refetched.total_amount == Decimal("1500.00")


class TestRecalculateAfterDeleteItem:
    async def test_deleting_one_of_two_items_recalculates_down(
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
        item_a = await service.add_item(
            bill.id,
            PurchaseBillItemCreateRequest(
                description="Item A", quantity=Decimal("10"), unit="KG", rate=Decimal("100")
            ),
            tenant_id=tenant_id,
        )
        await service.add_item(
            bill.id,
            PurchaseBillItemCreateRequest(
                description="Item B", quantity=Decimal("5"), unit="KG", rate=Decimal("50")
            ),
            tenant_id=tenant_id,
        )

        before = await service.get(bill.id, tenant_id=tenant_id)
        assert before.subtotal == Decimal("1250.00")

        await service.delete_item(bill.id, item_a.id, tenant_id=tenant_id)

        after = await service.get(bill.id, tenant_id=tenant_id)
        assert after.subtotal == Decimal("250.00")
        assert after.total_amount == Decimal("250.00")

    async def test_deleting_the_only_item_zeroes_line_totals_but_keeps_charges(
        self,
        service: PurchaseService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await service.create(
            PurchaseBillCreateRequest(supplier_id=supplier_id, bill_date=_BILL_DATE),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        # transport_charge has no request field yet (Session 5), so set it
        # directly on the row - the recalculation must still honor whatever
        # value is already there.
        bill_row = await service._get_or_raise(bill.id, tenant_id)
        bill_row.transport_charge = Decimal("50.00")
        await db_session.commit()

        item = await service.add_item(
            bill.id,
            PurchaseBillItemCreateRequest(
                description="Item", quantity=Decimal("10"), unit="KG", rate=Decimal("100")
            ),
            tenant_id=tenant_id,
        )

        await service.delete_item(bill.id, item.id, tenant_id=tenant_id)

        after = await service.get(bill.id, tenant_id=tenant_id)
        assert after.subtotal == Decimal("0.00")
        assert after.taxable_amount == Decimal("0.00")
        # transport_charge still contributes even with zero items.
        assert after.total_amount == Decimal("50.00")
        assert after.balance_amount == Decimal("50.00")


class TestRecalculateWithTransportAndOtherCharges:
    async def test_total_amount_includes_both_charges(
        self,
        service: PurchaseService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await service.create(
            PurchaseBillCreateRequest(supplier_id=supplier_id, bill_date=_BILL_DATE),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        bill_row = await service._get_or_raise(bill.id, tenant_id)
        bill_row.transport_charge = Decimal("100.00")
        bill_row.other_charge = Decimal("25.00")
        await db_session.commit()

        await service.add_item(
            bill.id,
            PurchaseBillItemCreateRequest(
                description="Item", quantity=Decimal("10"), unit="KG", rate=Decimal("100")
            ),
            tenant_id=tenant_id,
        )

        refetched = await service.get(bill.id, tenant_id=tenant_id)
        # subtotal 1000 + transport 100 + other 25 = 1125
        assert refetched.subtotal == Decimal("1000.00")
        assert refetched.total_amount == Decimal("1125.00")
        assert refetched.balance_amount == Decimal("1125.00")


class TestSequentialMutationsStayCorrect:
    async def test_add_update_add_delete_sequence_keeps_totals_correct(
        self,
        service: PurchaseService,
        db_session: AsyncSession,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        bill = await service.create(
            PurchaseBillCreateRequest(supplier_id=supplier_id, bill_date=_BILL_DATE),
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        bill_row = await service._get_or_raise(bill.id, tenant_id)
        bill_row.transport_charge = Decimal("20.00")
        await db_session.commit()

        item_a = await service.add_item(
            bill.id,
            PurchaseBillItemCreateRequest(
                description="Item A",
                quantity=Decimal("10"),
                unit="KG",
                rate=Decimal("100"),
                tax_rate=Decimal("10"),
            ),
            tenant_id=tenant_id,
        )
        # subtotal = 1000 + 100 tax = 1100; total = 1100 + 20 = 1120
        step1 = await service.get(bill.id, tenant_id=tenant_id)
        assert step1.total_amount == Decimal("1120.00")

        await service.update_item(
            bill.id,
            item_a.id,
            PurchaseBillItemUpdateRequest(quantity=Decimal("5")),
            tenant_id=tenant_id,
        )
        # subtotal = 500 + 50 tax = 550; total = 550 + 20 = 570
        step2 = await service.get(bill.id, tenant_id=tenant_id)
        assert step2.total_amount == Decimal("570.00")

        item_b = await service.add_item(
            bill.id,
            PurchaseBillItemCreateRequest(
                description="Item B", quantity=Decimal("2"), unit="KG", rate=Decimal("50")
            ),
            tenant_id=tenant_id,
        )
        # + 100 -> subtotal 650; total 670
        step3 = await service.get(bill.id, tenant_id=tenant_id)
        assert step3.total_amount == Decimal("670.00")

        await service.delete_item(bill.id, item_a.id, tenant_id=tenant_id)
        # only item_b remains: subtotal 100; total 120
        step4 = await service.get(bill.id, tenant_id=tenant_id)
        assert step4.subtotal == Decimal("100.00")
        assert step4.total_amount == Decimal("120.00")

        remaining_items = await service.list_items(
            bill.id, tenant_id=tenant_id, q=None, sort="line_number"
        )
        assert [i.id for i in remaining_items] == [item_b.id]
