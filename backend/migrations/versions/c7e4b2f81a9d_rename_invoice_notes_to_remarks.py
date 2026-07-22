"""rename invoice notes to remarks

Revision ID: c7e4b2f81a9d
Revises: a1c9f7e3d5b2
Create Date: 2026-07-22 23:05:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c7e4b2f81a9d'
down_revision: Union[str, Sequence[str], None] = 'a1c9f7e3d5b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Sprint 9 Session 2's request schemas use "remarks" (matching
    # trip_catches' free-text field), not the "notes" name Session 1's
    # models.py shipped with - no endpoint has ever used this column, so a
    # plain rename is safe this early.
    op.alter_column("invoices", "notes", new_column_name="remarks")


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("invoices", "remarks", new_column_name="notes")
