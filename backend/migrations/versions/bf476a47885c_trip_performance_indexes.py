"""trip performance indexes

Revision ID: bf476a47885c
Revises: a3f5c9d1e874
Create Date: 2026-08-24 23:55:04.890277

Sprint 18 Session 1 performance audit: every sibling module with the same
`tenant_id [+status] ORDER BY <date>` query shape (invoices, payments,
purchase_orders, purchase_bills, supplier_payments, delivery_challans)
already has a matching `(tenant_id, status)` and `(tenant_id, <default sort
column>)` partial index pair. `trips` was the one outlier - its list
endpoint's default sort is `-created_at` (TripListParams) and its status
filter is common, but neither had a supporting index. Harmless at current
dev-DB row counts (the planner correctly prefers a sequential scan there)
but the same wall every sibling index exists to avoid once a tenant
accumulates thousands of trips.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf476a47885c'
down_revision: Union[str, Sequence[str], None] = 'a3f5c9d1e874'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        'ix_trips_tenant_status',
        'trips',
        ['tenant_id', 'status'],
        unique=False,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )
    op.create_index(
        'ix_trips_tenant_created_at',
        'trips',
        ['tenant_id', 'created_at'],
        unique=False,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'ix_trips_tenant_created_at', table_name='trips', postgresql_where=sa.text('deleted_at IS NULL')
    )
    op.drop_index(
        'ix_trips_tenant_status', table_name='trips', postgresql_where=sa.text('deleted_at IS NULL')
    )
