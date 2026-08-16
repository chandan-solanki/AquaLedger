"""purchase orders and items tables

Revision ID: 997e88cb00b1
Revises: e2a7c5f0b834
Create Date: 2026-08-15 20:29:06.989427

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '997e88cb00b1'
down_revision: Union[str, Sequence[str], None] = 'e2a7c5f0b834'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('purchase_orders',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('supplier_id', sa.UUID(), nullable=False),
    sa.Column('po_number', sa.String(length=50), nullable=True),
    sa.Column('order_date', sa.Date(), nullable=False),
    sa.Column('expected_delivery_date', sa.Date(), nullable=True),
    sa.Column('status', sa.String(length=20), server_default='draft', nullable=False),
    sa.Column('subtotal', sa.Numeric(precision=14, scale=2), server_default='0', nullable=False),
    sa.Column('discount_amount', sa.Numeric(precision=14, scale=2), server_default='0', nullable=False),
    sa.Column('taxable_amount', sa.Numeric(precision=14, scale=2), server_default='0', nullable=False),
    sa.Column('tax_amount', sa.Numeric(precision=14, scale=2), server_default='0', nullable=False),
    sa.Column('transport_charge', sa.Numeric(precision=14, scale=2), server_default='0', nullable=False),
    sa.Column('other_charge', sa.Numeric(precision=14, scale=2), server_default='0', nullable=False),
    sa.Column('round_off', sa.Numeric(precision=6, scale=2), server_default='0', nullable=False),
    sa.Column('total_amount', sa.Numeric(precision=14, scale=2), server_default='0', nullable=False),
    sa.Column('remarks', sa.Text(), nullable=True),
    sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('next_item_line_number', sa.Integer(), server_default='1', nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_purchase_orders_tenant', 'purchase_orders', ['tenant_id'], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('ix_purchase_orders_tenant_order_date', 'purchase_orders', ['tenant_id', 'order_date'], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('ix_purchase_orders_tenant_po_number', 'purchase_orders', ['tenant_id', 'po_number'], unique=True, postgresql_where=sa.text('deleted_at IS NULL AND po_number IS NOT NULL'))
    op.create_index('ix_purchase_orders_tenant_status', 'purchase_orders', ['tenant_id', 'status'], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('ix_purchase_orders_tenant_supplier', 'purchase_orders', ['tenant_id', 'supplier_id'], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_table('purchase_order_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('purchase_order_id', sa.UUID(), nullable=False),
    sa.Column('line_number', sa.Integer(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('quantity', sa.Numeric(precision=12, scale=3), nullable=False),
    sa.Column('unit', sa.String(length=20), nullable=False),
    sa.Column('rate', sa.Numeric(precision=12, scale=4), nullable=False),
    sa.Column('discount_percent', sa.Numeric(precision=5, scale=2), server_default='0', nullable=False),
    sa.Column('discount_amount', sa.Numeric(precision=14, scale=2), server_default='0', nullable=False),
    sa.Column('taxable_amount', sa.Numeric(precision=14, scale=2), server_default='0', nullable=False),
    sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), server_default='0', nullable=False),
    sa.Column('tax_amount', sa.Numeric(precision=14, scale=2), server_default='0', nullable=False),
    sa.Column('line_total', sa.Numeric(precision=14, scale=2), server_default='0', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['purchase_order_id'], ['purchase_orders.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_purchase_order_items_tenant', 'purchase_order_items', ['tenant_id'], unique=False)
    op.create_index('ix_purchase_order_items_tenant_order', 'purchase_order_items', ['tenant_id', 'purchase_order_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_purchase_order_items_tenant_order', table_name='purchase_order_items')
    op.drop_index('ix_purchase_order_items_tenant', table_name='purchase_order_items')
    op.drop_table('purchase_order_items')
    op.drop_index('ix_purchase_orders_tenant_supplier', table_name='purchase_orders', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_index('ix_purchase_orders_tenant_status', table_name='purchase_orders', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_index('ix_purchase_orders_tenant_po_number', table_name='purchase_orders', postgresql_where=sa.text('deleted_at IS NULL AND po_number IS NOT NULL'))
    op.drop_index('ix_purchase_orders_tenant_order_date', table_name='purchase_orders', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_index('ix_purchase_orders_tenant', table_name='purchase_orders', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_table('purchase_orders')
