"""delivery challans and items tables

Revision ID: c6f18b3d94a2
Revises: a1f4e8c2b7d9
Create Date: 2026-08-16 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6f18b3d94a2'
down_revision: Union[str, Sequence[str], None] = 'a1f4e8c2b7d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('delivery_challans',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('invoice_id', sa.UUID(), nullable=False),
    sa.Column('challan_number', sa.String(length=50), nullable=True),
    sa.Column('challan_date', sa.Date(), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='draft', nullable=False),
    sa.Column('remarks', sa.Text(), nullable=True),
    sa.Column('dispatched_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('next_item_line_number', sa.Integer(), server_default='1', nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_delivery_challans_tenant', 'delivery_challans', ['tenant_id'], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('ix_delivery_challans_tenant_challan_date', 'delivery_challans', ['tenant_id', 'challan_date'], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('ix_delivery_challans_tenant_challan_number', 'delivery_challans', ['tenant_id', 'challan_number'], unique=True, postgresql_where=sa.text('deleted_at IS NULL AND challan_number IS NOT NULL'))
    op.create_index('ix_delivery_challans_tenant_invoice', 'delivery_challans', ['tenant_id', 'invoice_id'], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('ix_delivery_challans_tenant_status', 'delivery_challans', ['tenant_id', 'status'], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_table('delivery_challan_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('delivery_challan_id', sa.UUID(), nullable=False),
    sa.Column('invoice_item_id', sa.UUID(), nullable=False),
    sa.Column('line_number', sa.Integer(), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=12, scale=3), nullable=False),
    sa.Column('unit', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['delivery_challan_id'], ['delivery_challans.id'], ),
    sa.ForeignKeyConstraint(['invoice_item_id'], ['invoice_items.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_delivery_challan_items_tenant', 'delivery_challan_items', ['tenant_id'], unique=False)
    op.create_index('ix_delivery_challan_items_tenant_challan', 'delivery_challan_items', ['tenant_id', 'delivery_challan_id'], unique=False)
    op.create_index('ix_delivery_challan_items_tenant_invoice_item', 'delivery_challan_items', ['tenant_id', 'invoice_item_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_delivery_challan_items_tenant_invoice_item', table_name='delivery_challan_items')
    op.drop_index('ix_delivery_challan_items_tenant_challan', table_name='delivery_challan_items')
    op.drop_index('ix_delivery_challan_items_tenant', table_name='delivery_challan_items')
    op.drop_table('delivery_challan_items')
    op.drop_index('ix_delivery_challans_tenant_status', table_name='delivery_challans', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_index('ix_delivery_challans_tenant_invoice', table_name='delivery_challans', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_index('ix_delivery_challans_tenant_challan_number', table_name='delivery_challans', postgresql_where=sa.text('deleted_at IS NULL AND challan_number IS NOT NULL'))
    op.drop_index('ix_delivery_challans_tenant_challan_date', table_name='delivery_challans', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_index('ix_delivery_challans_tenant', table_name='delivery_challans', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_table('delivery_challans')
