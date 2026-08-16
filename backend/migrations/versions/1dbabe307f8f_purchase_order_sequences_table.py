"""purchase order sequences table

Revision ID: 1dbabe307f8f
Revises: 83010cc916fe
Create Date: 2026-08-15 20:29:13.355818

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1dbabe307f8f'
down_revision: Union[str, Sequence[str], None] = '83010cc916fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('purchase_order_sequences',
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('prefix', sa.String(length=10), nullable=False),
    sa.Column('fiscal_year', sa.String(length=7), nullable=False),
    sa.Column('last_number', sa.Integer(), server_default='0', nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('tenant_id', 'prefix', 'fiscal_year')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('purchase_order_sequences')
