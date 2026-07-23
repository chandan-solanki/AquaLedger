"""suppliers table

Revision ID: 4c8d1766df97
Revises: b6a1d7e3f284
Create Date: 2026-07-23 15:58:12.122796

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c8d1766df97'
down_revision: Union[str, Sequence[str], None] = 'b6a1d7e3f284'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('suppliers',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('legal_name', sa.String(length=255), nullable=True),
    sa.Column('gstin', sa.String(length=15), nullable=True),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('address', sa.Text(), nullable=True),
    sa.Column('city', sa.String(length=100), nullable=True),
    sa.Column('state', sa.String(length=100), nullable=True),
    sa.Column('country', sa.String(length=100), nullable=True),
    sa.Column('contact_person', sa.String(length=255), nullable=True),
    sa.Column('credit_days', sa.Integer(), server_default='0', nullable=False),
    sa.Column('opening_balance', sa.Numeric(precision=14, scale=2), server_default='0', nullable=False),
    sa.Column('outstanding_amount', sa.Numeric(precision=14, scale=2), server_default='0', nullable=False),
    sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_suppliers_tenant', 'suppliers', ['tenant_id'], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('ix_suppliers_tenant_code', 'suppliers', ['tenant_id', 'code'], unique=True, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('ix_suppliers_tenant_name', 'suppliers', ['tenant_id', sa.literal_column('lower(name)')], unique=True, postgresql_where=sa.text('deleted_at IS NULL'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_suppliers_tenant_name', table_name='suppliers', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_index('ix_suppliers_tenant_code', table_name='suppliers', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_index('ix_suppliers_tenant', table_name='suppliers', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_table('suppliers')
