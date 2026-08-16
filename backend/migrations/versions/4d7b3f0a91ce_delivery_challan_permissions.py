"""delivery challan permissions

Revision ID: 4d7b3f0a91ce
Revises: 9e5a2c7f4b18
Create Date: 2026-08-16 09:00:12.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid6 import uuid7


# revision identifiers, used by Alembic.
revision: str = '4d7b3f0a91ce'
down_revision: Union[str, Sequence[str], None] = '9e5a2c7f4b18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The full delivery_challan:* RBAC surface for Sprint 12 Session 14
# (TASKS.md). No delivery_challan permission existed anywhere before this
# session - the module is entirely new, so this migration seeds the
# complete set in one place, mirroring 83010cc916fe (purchase_order:*)'s own
# posture.
_PERMISSIONS: list[tuple[str, str, str, str]] = [
    ("delivery_challan:view", "delivery_challan", "view", "View delivery challans"),
    ("delivery_challan:create", "delivery_challan", "create", "Create draft delivery challans"),
    ("delivery_challan:edit", "delivery_challan", "edit", "Edit draft delivery challans"),
    ("delivery_challan:delete", "delivery_challan", "delete", "Delete draft delivery challans"),
    ("delivery_challan:dispatch", "delivery_challan", "dispatch", "Dispatch a delivery challan"),
    ("delivery_challan:deliver", "delivery_challan", "deliver", "Mark a delivery challan delivered"),
    ("delivery_challan:cancel", "delivery_challan", "cancel", "Cancel a delivery challan"),
]

# Same four roles purchase_order:*/purchase:* grant (83010cc916fe / 578d0e205274) -
# `operator` gets none, consistent with its baseline read-only scope.
_GRANTED_TO_ROLES = ["super_admin", "admin", "manager", "accountant"]


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
