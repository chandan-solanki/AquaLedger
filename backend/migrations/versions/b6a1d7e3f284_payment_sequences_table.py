"""payment sequences table

Revision ID: b6a1d7e3f284
Revises: 9d4c1f6a82e7
Create Date: 2026-07-23 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6a1d7e3f284'
down_revision: Union[str, Sequence[str], None] = '9d4c1f6a82e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('payment_sequences',
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('prefix', sa.String(length=10), nullable=False),
    sa.Column('fiscal_year', sa.String(length=7), nullable=False),
    sa.Column('last_number', sa.Integer(), server_default='0', nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('tenant_id', 'prefix', 'fiscal_year')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('payment_sequences')
