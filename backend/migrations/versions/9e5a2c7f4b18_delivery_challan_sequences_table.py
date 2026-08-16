"""delivery challan sequences table

Revision ID: 9e5a2c7f4b18
Revises: c6f18b3d94a2
Create Date: 2026-08-16 09:00:06.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e5a2c7f4b18'
down_revision: Union[str, Sequence[str], None] = 'c6f18b3d94a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('delivery_challan_sequences',
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('prefix', sa.String(length=10), nullable=False),
    sa.Column('fiscal_year', sa.String(length=7), nullable=False),
    sa.Column('last_number', sa.Integer(), server_default='0', nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('tenant_id', 'prefix', 'fiscal_year')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('delivery_challan_sequences')
