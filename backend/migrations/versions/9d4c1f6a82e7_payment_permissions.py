"""payment permissions

Revision ID: 9d4c1f6a82e7
Revises: 37e193df7033
Create Date: 2026-07-23 13:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid6 import uuid7


# revision identifiers, used by Alembic.
revision: str = '9d4c1f6a82e7'
down_revision: Union[str, Sequence[str], None] = '37e193df7033'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# payment:view and payment:delete were already seeded in the baseline
# migration (67c33121fc54) alongside every other module's roadmap-wide RBAC
# surface, before this module existed - the same situation invoice:view/
# create/edit/issue/cancel found themselves in ahead of the invoices module
# (see migration a1c9f7e3d5b2's comment). That baseline also seeded
# payment:record and payment:bounce for ARCHITECTURE.md §14.1/§14.4's
# original allocate-on-record / cheque-bounce design; this sprint's as-built
# TASKS.md instead models payments as an explicit Draft -> Posted ->
# Cancelled state machine (the same kind of as-built deviation Invoice made
# from invoice_type/parent_invoice_id), so payment:record/bounce are left
# seeded but unused, the same way invoice:cancel sits unused pending a
# future credit-note sprint.
#
# payment:create/edit/post are the gap this migration fills - the create/
# edit/post-workflow codes TASKS.md Sprint 10 Session 1 actually asks for,
# seeded on top of the baseline set the same way a1c9f7e3d5b2 added
# invoice:delete.
_PERMISSIONS: list[tuple[str, str, str, str]] = [
    ("payment:create", "payment", "create", "Create a draft payment"),
    ("payment:edit", "payment", "edit", "Edit a draft payment"),
    ("payment:post", "payment", "post", "Post a payment, applying its allocations"),
]

# Granted to the same roles that already hold payment:record from the
# baseline seed (67c33121fc54): super_admin/admin (via _ALL_CODES),
# manager (payment:record was never in _MANAGER_CODES's exclusion set) and
# accountant (explicitly listed in _ACCOUNTANT_CODES). payment:post is a
# state transition, the same category as invoice:issue, which those same
# four roles already hold. `operator` gets none of these three - it never
# held payment:view or payment:record either (baseline's _OPERATOR_CODES is
# company:view/fish:view/invoice:view only).
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
