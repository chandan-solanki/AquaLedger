"""document records source fields

Revision ID: e2a7c5f0b834
Revises: d7f2b6c8a915
Create Date: 2026-08-22 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e2a7c5f0b834'
down_revision: Union[str, Sequence[str], None] = 'd7f2b6c8a915'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Both columns are nullable - every DocumentRecord created in Sessions
    # 6/7 (before this migration) has no source_type/source_id and must
    # remain valid; there is no backfill (the source module/id of an
    # already-generated document isn't reconstructable after the fact,
    # only new generations populate it going forward).
    op.add_column('document_records', sa.Column('source_type', sa.String(length=30), nullable=True))
    op.add_column('document_records', sa.Column('source_id', sa.UUID(), nullable=True))
    op.create_index(
        'ix_document_records_tenant_source', 'document_records',
        ['tenant_id', 'source_type', 'source_id'], unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_document_records_tenant_source', table_name='document_records')
    op.drop_column('document_records', 'source_id')
    op.drop_column('document_records', 'source_type')
