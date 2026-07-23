"""purchase management permissions

Revision ID: 578d0e205274
Revises: d5381c02e1f3
Create Date: 2026-07-23 15:58:25.609543

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid6 import uuid7


# revision identifiers, used by Alembic.
revision: str = '578d0e205274'
down_revision: Union[str, Sequence[str], None] = 'd5381c02e1f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The full supplier:*/purchase:* RBAC surface for Sprint 11 (TASKS.md).
# Unlike payment:view/delete or invoice:view/create (already present in the
# baseline migration 67c33121fc54 ahead of their modules), no supplier or
# purchase permission existed anywhere before this sprint - both modules are
# entirely new, so this migration seeds the complete set in one place
# rather than splitting a baseline subset from a later top-up (the pattern
# a1c9f7e3d5b2/9d4c1f6a82e7 followed for invoices/payments).
_PERMISSIONS: list[tuple[str, str, str, str]] = [
    ("supplier:view", "supplier", "view", "View supplier records"),
    ("supplier:create", "supplier", "create", "Create supplier records"),
    ("supplier:edit", "supplier", "edit", "Edit supplier records"),
    ("supplier:delete", "supplier", "delete", "Delete supplier records"),
    ("purchase:view", "purchase", "view", "View purchase bills"),
    ("purchase:create", "purchase", "create", "Create draft purchase bills"),
    ("purchase:edit", "purchase", "edit", "Edit draft purchase bills"),
    ("purchase:delete", "purchase", "delete", "Delete draft purchase bills"),
    ("purchase:post", "purchase", "post", "Post a purchase bill"),
]

# TASKS.md Sprint 11 Session 1: "Grant: super_admin, admin, manager,
# accountant" - the same four roles payment:create/edit/post
# (9d4c1f6a82e7) grants. `operator` gets none of these, consistent with its
# baseline read-only scope (company:view/fish:view/invoice:view only).
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
