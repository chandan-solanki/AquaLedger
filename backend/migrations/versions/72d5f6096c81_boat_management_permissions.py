"""boat management permissions

Revision ID: 72d5f6096c81
Revises: 0066331bf93b
Create Date: 2026-07-21 17:24:03.381265

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid6 import uuid7


# revision identifiers, used by Alembic.
revision: str = '72d5f6096c81'
down_revision: Union[str, Sequence[str], None] = '0066331bf93b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Seed data is inlined (not imported from app.modules.boats.permissions) so
# this migration replays identically regardless of future changes to app
# code - same rationale as migration 67c33121fc54. `boat:view` was already
# seeded there; this adds the create/edit/delete codes the Session 2 CRUD
# endpoints require.
_PERMISSIONS: list[tuple[str, str, str, str]] = [
    ("boat:create", "boat", "create", "Create a boat"),
    ("boat:edit", "boat", "edit", "Edit a boat"),
    ("boat:delete", "boat", "delete", "Delete a boat"),
]

# Granted to the same roles fish:manage went to (Phase 4 master-data
# precedent): super_admin/admin implicitly have everything, manager
# operates the fleet day to day. accountant/operator keep boat:view only.
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
