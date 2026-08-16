"""purchase bill purchase order link

Revision ID: a1f4e8c2b7d9
Revises: 1dbabe307f8f
Create Date: 2026-08-15 21:00:00.000000

Sprint 12 Session 12: adds the optional Purchase Order -> Purchase Bill
relationship. Both new columns are nullable - existing standalone purchase
bills (created before this migration, or created afterward without a PO)
are completely unaffected. No explicit ondelete on either FK, matching the
existing convention for every other cross-table FK in this schema (e.g.
purchase_bills.supplier_id, purchase_order_items.purchase_order_id) - both
PurchaseOrder and PurchaseOrderItem rows a bill could reference are never
hard-deleted in practice (PurchaseOrder is soft-deleted, and
PurchaseOrderItem can only be hard-deleted while its parent order is DRAFT,
a state a bill is never allowed to link against), so the default
RESTRICT-like behavior is never actually exercised - it's just a defensive
guarantee, not a behavior change.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1f4e8c2b7d9'
down_revision: Union[str, Sequence[str], None] = '1dbabe307f8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('purchase_bills', sa.Column('purchase_order_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'purchase_bills_purchase_order_id_fkey',
        'purchase_bills', 'purchase_orders', ['purchase_order_id'], ['id'],
    )
    op.create_index(
        'ix_purchase_bills_tenant_purchase_order', 'purchase_bills',
        ['tenant_id', 'purchase_order_id'], unique=False,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )

    op.add_column('purchase_bill_items', sa.Column('purchase_order_item_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'purchase_bill_items_purchase_order_item_id_fkey',
        'purchase_bill_items', 'purchase_order_items', ['purchase_order_item_id'], ['id'],
    )
    op.create_index(
        'ix_purchase_bill_items_purchase_order_item', 'purchase_bill_items',
        ['purchase_order_item_id'], unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_purchase_bill_items_purchase_order_item', table_name='purchase_bill_items')
    op.drop_constraint('purchase_bill_items_purchase_order_item_id_fkey', 'purchase_bill_items', type_='foreignkey')
    op.drop_column('purchase_bill_items', 'purchase_order_item_id')

    op.drop_index('ix_purchase_bills_tenant_purchase_order', table_name='purchase_bills', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_constraint('purchase_bills_purchase_order_id_fkey', 'purchase_bills', type_='foreignkey')
    op.drop_column('purchase_bills', 'purchase_order_id')
