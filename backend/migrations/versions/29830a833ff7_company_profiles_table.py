"""company profiles table

Revision ID: 29830a833ff7
Revises: 4d7b3f0a91ce
Create Date: 2026-08-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29830a833ff7'
down_revision: Union[str, Sequence[str], None] = '4d7b3f0a91ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('company_profiles',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('legal_name', sa.String(length=255), nullable=False),
    sa.Column('display_name', sa.String(length=255), nullable=True),
    sa.Column('company_code', sa.String(length=50), nullable=True),
    sa.Column('address_line1', sa.String(length=255), nullable=True),
    sa.Column('address_line2', sa.String(length=255), nullable=True),
    sa.Column('city', sa.String(length=100), nullable=True),
    sa.Column('state', sa.String(length=100), nullable=True),
    sa.Column('state_code', sa.String(length=2), nullable=True),
    sa.Column('pincode', sa.String(length=10), nullable=True),
    sa.Column('country', sa.String(length=100), nullable=True),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('alt_phone', sa.String(length=20), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('website', sa.String(length=255), nullable=True),
    sa.Column('gstin', sa.String(length=15), nullable=True),
    sa.Column('pan', sa.String(length=10), nullable=True),
    sa.Column('logo_storage_key', sa.String(length=500), nullable=True),
    sa.Column('logo_content_type', sa.String(length=50), nullable=True),
    sa.Column('logo_uploaded_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_company_profiles_tenant_id', 'company_profiles', ['tenant_id'], unique=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_company_profiles_tenant_id', table_name='company_profiles')
    op.drop_table('company_profiles')
    # ### end Alembic commands ###
