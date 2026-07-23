import uuid
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Tenant
from app.modules.purchase.constants import PurchaseStatus
from app.modules.purchase.models import PurchaseBill, PurchaseBillItem
from app.modules.suppliers.models import Supplier


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    tenant = Tenant(name="Purchase Test Tenant", slug=f"purchase-test-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    await db_session.commit()
    return tenant.id


@pytest.fixture
async def supplier(db_session: AsyncSession, tenant_id: uuid.UUID) -> Supplier:
    supplier = Supplier(
        tenant_id=tenant_id,
        code=f"SUP-{uuid.uuid4().hex[:8]}",
        name=f"Supplier {uuid.uuid4().hex[:8]}",
    )
    db_session.add(supplier)
    await db_session.commit()
    return supplier


async def _make_bill(
    db_session: AsyncSession, tenant_id: uuid.UUID, supplier_id: uuid.UUID, **overrides: Any
) -> PurchaseBill:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "supplier_id": supplier_id,
        "bill_date": date(2026, 7, 23),
    }
    defaults.update(overrides)
    bill = PurchaseBill(**defaults)
    db_session.add(bill)
    await db_session.commit()
    return bill


class TestPurchaseBillModel:
    async def test_creates_with_default_status_and_zero_totals(
        self, db_session: AsyncSession, tenant_id: uuid.UUID, supplier: Supplier
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier.id)
        await db_session.refresh(bill)
        assert bill.status == PurchaseStatus.DRAFT
        assert bill.bill_number is None
        assert bill.total_amount == 0
        assert bill.balance_amount == 0
        assert bill.posted_at is None
        assert bill.deleted_at is None
        assert bill.next_item_line_number == 1

    async def test_supplier_relationship_resolves(
        self, db_session: AsyncSession, tenant_id: uuid.UUID, supplier: Supplier
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier.id)
        await db_session.refresh(bill, attribute_names=["supplier"])
        assert bill.supplier.id == supplier.id

    async def test_reverse_relationship_from_supplier_resolves(
        self, db_session: AsyncSession, tenant_id: uuid.UUID, supplier: Supplier
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier.id)
        await db_session.refresh(supplier, attribute_names=["purchase_bills"])
        assert [b.id for b in supplier.purchase_bills] == [bill.id]

    async def test_two_draft_bills_with_null_bill_number_do_not_conflict(
        self, db_session: AsyncSession, tenant_id: uuid.UUID, supplier: Supplier
    ) -> None:
        # bill_number is NULL for both - the partial unique index only
        # applies once a number is assigned (Session 5), so this must not raise.
        await _make_bill(db_session, tenant_id, supplier.id)
        await _make_bill(db_session, tenant_id, supplier.id)

    async def test_duplicate_bill_number_within_tenant_is_rejected(
        self, db_session: AsyncSession, tenant_id: uuid.UUID, supplier: Supplier
    ) -> None:
        await _make_bill(db_session, tenant_id, supplier.id, bill_number="PUR/2026-27/00001")
        with pytest.raises(IntegrityError):
            await _make_bill(db_session, tenant_id, supplier.id, bill_number="PUR/2026-27/00001")


class TestPurchaseBillItemModel:
    async def test_creates_and_resolves_reverse_relationship(
        self, db_session: AsyncSession, tenant_id: uuid.UUID, supplier: Supplier
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier.id)
        item = PurchaseBillItem(
            tenant_id=tenant_id,
            purchase_bill_id=bill.id,
            line_number=1,
            quantity=Decimal("50.000"),
            unit="KG",
            rate=Decimal("450.0000"),
        )
        db_session.add(item)
        await db_session.commit()

        await db_session.refresh(bill, attribute_names=["items"])
        assert [i.id for i in bill.items] == [item.id]

        await db_session.refresh(item, attribute_names=["purchase_bill"])
        assert item.purchase_bill.id == bill.id

    async def test_multiple_lines_are_ordered_by_line_number(
        self, db_session: AsyncSession, tenant_id: uuid.UUID, supplier: Supplier
    ) -> None:
        bill = await _make_bill(db_session, tenant_id, supplier.id)
        for line_number in (3, 1, 2):
            db_session.add(
                PurchaseBillItem(
                    tenant_id=tenant_id,
                    purchase_bill_id=bill.id,
                    line_number=line_number,
                    quantity=Decimal("1.000"),
                    unit="KG",
                    rate=Decimal("1.0000"),
                )
            )
        await db_session.commit()

        result = await db_session.execute(
            select(PurchaseBillItem)
            .where(PurchaseBillItem.purchase_bill_id == bill.id)
            .order_by(PurchaseBillItem.line_number)
        )
        assert [row.line_number for row in result.scalars().all()] == [1, 2, 3]
