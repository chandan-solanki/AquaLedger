"""trip expense permissions

Revision ID: f27a4c6e9b13
Revises: e148278488ca
Create Date: 2026-07-22 19:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid6 import uuid7


# revision identifiers, used by Alembic.
revision: str = 'f27a4c6e9b13'
down_revision: Union[str, Sequence[str], None] = 'e148278488ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Seed data is inlined (not imported from app.modules.trip_expenses.permissions)
# so this migration replays identically regardless of future changes to app
# code - same rationale as migration d96d76e5af7a. trip_expenses is a brand
# new module (Sprint 8), so all four codes are seeded together here rather
# than view-now/manage-later like boats.
_VIEW_PERMISSION: tuple[str, str, str, str] = (
    "trip_expense:view", "trip_expense", "view", "View trip expenses"
)
_MANAGE_PERMISSIONS: list[tuple[str, str, str, str]] = [
    ("trip_expense:create", "trip_expense", "create", "Record a trip expense"),
    ("trip_expense:edit", "trip_expense", "edit", "Edit a trip expense"),
    ("trip_expense:delete", "trip_expense", "delete", "Delete a trip expense"),
]
_ALL_PERMISSIONS = [_VIEW_PERMISSION, *_MANAGE_PERMISSIONS]

# Mirrors the trip_catch:view / trip_catch:create+edit+delete role split from
# d96d76e5af7a: accountant can see trip expenses (they feed trip
# profitability calculations, ARCHITECTURE.md §16) but only
# super_admin/admin/manager record or change them.
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
