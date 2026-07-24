"""supplier payment permissions

Revision ID: 005c4ade9277
Revises: 59911f320635
Create Date: 2026-07-23 23:11:15.032482

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid6 import uuid7


# revision identifiers, used by Alembic.
revision: str = '005c4ade9277'
down_revision: Union[str, Sequence[str], None] = '59911f320635'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The full supplier_payment:* RBAC surface for Sprint 12 (TASKS.md). No
# supplier_payment permission existed anywhere before this sprint - the
# module is entirely new, so this migration seeds the complete set in one
# place, the same approach migration 578d0e205274 took for supplier:*/
# purchase:* rather than splitting a baseline subset from a later top-up
# (the pattern a1c9f7e3d5b2/9d4c1f6a82e7 followed for invoices/payments).
_PERMISSIONS: list[tuple[str, str, str, str]] = [
    ("supplier_payment:view", "supplier_payment", "view", "View supplier payments"),
    ("supplier_payment:create", "supplier_payment", "create", "Create draft supplier payments"),
    ("supplier_payment:edit", "supplier_payment", "edit", "Edit draft supplier payments"),
    ("supplier_payment:delete", "supplier_payment", "delete", "Delete draft supplier payments"),
    ("supplier_payment:post", "supplier_payment", "post", "Post a supplier payment"),
]

# TASKS.md Sprint 12 Session 1: "Grant: super_admin, admin, manager,
# accountant" - the same four roles payment:create/edit/post
# (9d4c1f6a82e7) and purchase:create/edit/post (578d0e205274) grant.
# `operator` gets none of these, consistent with its baseline read-only
# scope (company:view/fish:view/invoice:view only).
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
