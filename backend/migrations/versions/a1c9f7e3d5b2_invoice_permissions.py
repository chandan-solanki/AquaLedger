"""invoice permissions

Revision ID: a1c9f7e3d5b2
Revises: b3f6a1d94c27
Create Date: 2026-07-22 22:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid6 import uuid7


# revision identifiers, used by Alembic.
revision: str = 'a1c9f7e3d5b2'
down_revision: Union[str, Sequence[str], None] = 'b3f6a1d94c27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# invoice:view/create/edit/issue/cancel were already seeded in the baseline
# migration (67c33121fc54) alongside every other module's permission codes -
# the whole RBAC surface for the roadmap was defined upfront there, before
# most of the corresponding tables existed. invoice:delete is the one gap:
# it wasn't anticipated in that initial set (the baseline's invoice row only
# covers view/create/edit/issue/cancel), and the Session 2 DELETE endpoint
# needs it - same situation trip:delete (244f758929a6) fixed for trips.
_PERMISSIONS: list[tuple[str, str, str, str]] = [
    ("invoice:delete", "invoice", "delete", "Delete a draft invoice"),
]

# Granted to the same roles invoice:create/edit already went to in
# 67c33121fc54 (_ALL_CODES for super_admin/admin, _MANAGER_CODES for manager,
# _ACCOUNTANT_CODES for accountant): deleting a draft is strictly less
# consequential than issuing one, which those roles can already do.
# `operator` keeps invoice:view only, same as it does today.
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
