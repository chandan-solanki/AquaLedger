"""trip catch permissions

Revision ID: d96d76e5af7a
Revises: 3bfa1e6eab63
Create Date: 2026-07-22 17:41:57.867315

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid6 import uuid7


# revision identifiers, used by Alembic.
revision: str = 'd96d76e5af7a'
down_revision: Union[str, Sequence[str], None] = '3bfa1e6eab63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Seed data is inlined (not imported from app.modules.trip_catches.permissions)
# so this migration replays identically regardless of future changes to app
# code - same rationale as migration 72d5f6096c81. trip_catches is a brand
# new module (Sprint 7), so all four codes are seeded together here rather
# than view-now/manage-later like boats.
_VIEW_PERMISSION: tuple[str, str, str, str] = (
    "trip_catch:view", "trip_catch", "view", "View trip catches"
)
_MANAGE_PERMISSIONS: list[tuple[str, str, str, str]] = [
    ("trip_catch:create", "trip_catch", "create", "Record a trip catch"),
    ("trip_catch:edit", "trip_catch", "edit", "Edit a trip catch"),
    ("trip_catch:delete", "trip_catch", "delete", "Delete a trip catch"),
]
_ALL_PERMISSIONS = [_VIEW_PERMISSION, *_MANAGE_PERMISSIONS]

# Mirrors the trip:view / trip:create+edit+close+delete role split from
# 67c33121fc54 + 244f758929a6: accountant can see catches (they feed
# invoicing later) but only super_admin/admin/manager record or change them.
_VIEW_ROLES = ["super_admin", "admin", "manager", "accountant"]
_MANAGE_ROLES = ["super_admin", "admin", "manager"]


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

    permission_ids = {code: uuid7() for code, *_ in _ALL_PERMISSIONS}
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
            for code, resource, action, description in _ALL_PERMISSIONS
        ],
    )

    role_id_by_name = dict(
        bind.execute(sa.select(roles_table.c.name, roles_table.c.id)).all()
    )

    grants = [
        {"role_id": role_id_by_name[role], "permission_id": permission_ids[_VIEW_PERMISSION[0]]}
        for role in _VIEW_ROLES
        if role in role_id_by_name
    ]
    grants += [
        {"role_id": role_id_by_name[role], "permission_id": permission_ids[code]}
        for role in _MANAGE_ROLES
        if role in role_id_by_name
        for code, *_ in _MANAGE_PERMISSIONS
    ]
    bind.execute(role_permissions_table.insert(), grants)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    codes = [code for code, *_ in _ALL_PERMISSIONS]

    bind.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code = ANY(:codes))"
        ),
        {"codes": codes},
    )
    bind.execute(sa.text("DELETE FROM permissions WHERE code = ANY(:codes)"), {"codes": codes})
