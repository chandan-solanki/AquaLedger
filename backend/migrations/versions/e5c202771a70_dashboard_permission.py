"""dashboard permission

Revision ID: e5c202771a70
Revises: e2b8f4a91c6d
Create Date: 2026-07-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid6 import uuid7


# revision identifiers, used by Alembic.
revision: str = 'e5c202771a70'
down_revision: Union[str, Sequence[str], None] = 'e2b8f4a91c6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The dashboard module is read-only (TASKS.md Sprint 10 Session 1) and has
# exactly one permission - contrast with trip:view/create/edit/.../purchase:*
# which each seed a full CRUD surface (578d0e205274, f27a4c6e9b13, etc.).
_PERMISSIONS: list[tuple[str, str, str, str]] = [
    ("dashboard:view", "dashboard", "view", "View the owner's dashboard overview"),
]

# Mirrors 578d0e205274 (purchase management)'s grant list: the four roles
# with cross-module financial visibility. `operator`'s baseline scope
# (company:view/fish:view/invoice:view only) doesn't include dashboard-level
# aggregates across payments/trips/purchase bills, so it's excluded here too.
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
