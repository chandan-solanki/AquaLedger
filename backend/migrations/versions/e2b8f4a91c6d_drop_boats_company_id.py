"""drop boats.company_id

Revision ID: e2b8f4a91c6d
Revises: d74bbc8c12ed
Create Date: 2026-07-27 10:00:00.000000

Boat ownership is `tenant_id` only - a boat belongs to the fishing business
itself, never to a `Company` (a `Company` is a customer/buyer). Drops the
`company_id` column, its FK to `companies` and its index; every other boat
column and row is left untouched, so no boat data is lost.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2b8f4a91c6d'
down_revision: Union[str, Sequence[str], None] = 'd74bbc8c12ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index('ix_boats_tenant_company', table_name='boats', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_constraint('boats_company_id_fkey', 'boats', type_='foreignkey')
    op.drop_column('boats', 'company_id')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('boats', sa.Column('company_id', sa.UUID(), nullable=True))
    op.create_foreign_key('boats_company_id_fkey', 'boats', 'companies', ['company_id'], ['id'])
    op.create_index('ix_boats_tenant_company', 'boats', ['tenant_id', 'company_id'], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
