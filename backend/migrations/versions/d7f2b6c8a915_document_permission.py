"""document permission

Revision ID: d7f2b6c8a915
Revises: c4e9a2f1d7b3
Create Date: 2026-08-15 00:00:01.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid6 import uuid7


# revision identifiers, used by Alembic.
revision: str = "d7f2b6c8a915"
down_revision: Union[str, Sequence[str], None] = "c4e9a2f1d7b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The Document Center is read-only (Sprint 12 Session 6) and has exactly
# one permission - the same "single view permission, no CRUD surface"
# shape b8d1f4a726c9 (reports_permission)/e5c202771a70 (dashboard_permission)
# established for the last two read-only modules; download reuses this
# same code rather than a separate document:download.
_PERMISSIONS: list[tuple[str, str, str, str]] = [
    ("document:view", "document", "view", "View and download generated business documents"),
]

# Mirrors b8d1f4a726c9's grant list exactly: the same roles with
# cross-module financial visibility that reports:view went to.
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

    role_ids = (
        bind.execute(sa.select(roles_table.c.id).where(roles_table.c.name.in_(_GRANTED_TO_ROLES)))
        .scalars()
        .all()
    )

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
