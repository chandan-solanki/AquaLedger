"""purchase order permissions

Revision ID: 83010cc916fe
Revises: 997e88cb00b1
Create Date: 2026-08-15 20:29:12.730606

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid6 import uuid7


# revision identifiers, used by Alembic.
revision: str = '83010cc916fe'
down_revision: Union[str, Sequence[str], None] = '997e88cb00b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The full purchase_order:* RBAC surface for Sprint 12 Session 9 (TASKS.md).
# No purchase_order permission existed anywhere before this session - the
# module is entirely new, so this migration seeds the complete set in one
# place, mirroring 578d0e205274 (purchase:*)'s own posture.
_PERMISSIONS: list[tuple[str, str, str, str]] = [
    ("purchase_order:view", "purchase_order", "view", "View purchase orders"),
    ("purchase_order:create", "purchase_order", "create", "Create draft purchase orders"),
    ("purchase_order:edit", "purchase_order", "edit", "Edit draft purchase orders"),
    ("purchase_order:delete", "purchase_order", "delete", "Delete draft purchase orders"),
    ("purchase_order:confirm", "purchase_order", "confirm", "Confirm a purchase order"),
    ("purchase_order:cancel", "purchase_order", "cancel", "Cancel a purchase order"),
    ("purchase_order:fulfill", "purchase_order", "fulfill", "Mark a purchase order fulfilled"),
]

# Same four roles purchase:create/edit/delete/post (578d0e205274) grants -
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
