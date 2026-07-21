"""trip delete permission

Revision ID: 244f758929a6
Revises: 72e2043a7f04
Create Date: 2026-07-21 18:49:17.302693

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid6 import uuid7


# revision identifiers, used by Alembic.
revision: str = '244f758929a6'
down_revision: Union[str, Sequence[str], None] = '72e2043a7f04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Seed data is inlined (not imported from app.modules.trips.permissions) so
# this migration replays identically regardless of future changes to app
# code - same rationale as migration 72d5f6096c81. trip:view/create/edit/close
# were already seeded in 67c33121fc54; this adds the delete code the
# Session 2 DELETE endpoint requires.
_PERMISSIONS: list[tuple[str, str, str, str]] = [
    ("trip:delete", "trip", "delete", "Delete a trip"),
]

# Granted to the same roles trip:create/edit/close already went to (via
# _ALL_CODES/_MANAGER_CODES in 67c33121fc54): super_admin, admin, manager.
_GRANTED_TO_ROLES = ["super_admin", "admin", "manager"]


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    permissions_table = sa.table(
        "permissions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("resource", sa.String),
        sa.column("action", sa.String),
        sa.column("description", sa.String),
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", postgresql.UUID(as_uuid=True)),
        sa.column("permission_id", postgresql.UUID(as_uuid=True)),
    )
    roles_table = sa.table(
        "roles",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
    )

    permission_ids = {code: uuid7() for code, *_ in _PERMISSIONS}
    bind.execute(
        permissions_table.insert(),
        [
            {
                "id": permission_ids[code],
                "code": code,
                "resource": resource,
                "action": action,
                "description": description,
            }
            for code, resource, action, description in _PERMISSIONS
        ],
    )

    role_ids = bind.execute(
        sa.select(roles_table.c.id).where(roles_table.c.name.in_(_GRANTED_TO_ROLES))
    ).scalars().all()

    bind.execute(
        role_permissions_table.insert(),
        [
            {"role_id": role_id, "permission_id": permission_id}
            for role_id in role_ids
            for permission_id in permission_ids.values()
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    codes = [code for code, *_ in _PERMISSIONS]

    bind.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code = ANY(:codes))"
        ),
        {"codes": codes},
    )
    bind.execute(sa.text("DELETE FROM permissions WHERE code = ANY(:codes)"), {"codes": codes})
