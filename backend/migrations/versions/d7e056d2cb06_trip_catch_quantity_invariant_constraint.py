"""trip catch quantity invariant constraint

Revision ID: d7e056d2cb06
Revises: d96d76e5af7a
Create Date: 2026-07-22 18:18:01.739881

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7e056d2cb06'
down_revision: Union[str, Sequence[str], None] = 'd96d76e5af7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        "ck_trip_catches_quantity_invariant",
        "trip_catches",
        "available_quantity + sold_quantity + waste_quantity = quantity_caught",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_trip_catches_quantity_invariant", "trip_catches", type_="check")
