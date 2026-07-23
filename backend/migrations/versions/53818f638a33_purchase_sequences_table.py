"""purchase sequences table

Revision ID: 53818f638a33
Revises: 578d0e205274
Create Date: 2026-07-23 15:58:28.712050

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53818f638a33'
down_revision: Union[str, Sequence[str], None] = '578d0e205274'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('purchase_sequences',
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('prefix', sa.String(length=10), nullable=False),
    sa.Column('fiscal_year', sa.String(length=7), nullable=False),
    sa.Column('last_number', sa.Integer(), server_default='0', nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('tenant_id', 'prefix', 'fiscal_year')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('purchase_sequences')
