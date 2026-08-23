"""Migration-time system-permission propagation (Sprint 17 Session 3).

## Why this exists

Every permission-adding migration before this one (67c33121fc54 and the 13
that followed it) resolved a target role purely by NAME, with NO tenant
filter:

    role_ids = bind.execute(
        sa.select(roles_table.c.id).where(roles_table.c.name.in_(_GRANTED_TO_ROLES))
    ).scalars().all()

That was safe only because exactly one tenant (`default`) existed at the
time each of those migrations ran. Sprint 17 Session 2 made tenant
provisioning real, so a migration written that way today would silently
grant a new permission to the default tenant's roles only, leaving every
other tenant's "admin"/"manager"/etc. role permanently behind. This module
is the fix: a permission grant made through `propagate_permission_grant`
reaches every tenant's copy of a named role, not just one.

## Why this lives outside app/

This helper is imported by Alembic migration files, and every migration in
this project is written to stay historically replayable without depending
on mutable application code (see 67c33121fc54's own comment: "Seed data is
inlined ... so this migration replays identically regardless of future
changes to app code"). Importing `app.modules.auth.models` here would
violate exactly that guarantee - if a future refactor renamed a column or
changed a relationship on the ORM `Role`/`Permission`/`RolePermission`
classes, every past migration that had imported them could break on replay
against a from-scratch database. The tables below are therefore local,
minimal `sa.Table` definitions naming only the columns this helper actually
touches - a second, deliberately narrow description of the same physical
tables the ORM also describes, not a shared import between the two.

## What a migration must still say explicitly

This helper does not hide *what* is being granted or *to whom* - every
call site passes the permission's code/resource/action/description and the
exact target role names as literal arguments, in the migration file
itself. That is what "historically replayable" actually requires: the
migration file alone must be enough to understand and reproduce what it
did. Factoring out the repeated SQL pattern (the part that was copy-pasted
13 times and got the tenant-scoping wrong every time) is the opposite of
hiding intent - it makes the one part worth sharing (the coverage
guarantee) impossible to get wrong again.

## Failure policy for a tenant missing the target role

If any tenant does not have a role by the expected name, this raises
`RuntimeError` and grants nothing at all (Postgres migrations in this
project run inside one transaction per migration, so raising here aborts
the whole `upgrade()`, not just the affected tenant - see env.py's
`do_run_migrations`/"Will assume transactional DDL"). This is a deliberate
fail-loud policy: a tenant missing an expected system role is corrupted
data, and silently skipping it, or fabricating a replacement role from
inside a permission migration, would both hide that corruption behind an
unrelated change. An operator must fix the corrupted tenant's role set
(or decide, out of band, that it is intentionally custom) before the
migration can proceed for every tenant.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection
from uuid6 import uuid7

_metadata = sa.MetaData()

_permissions = sa.Table(
    "permissions",
    _metadata,
    sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
    sa.Column("code", sa.String(100)),
    sa.Column("resource", sa.String(50)),
    sa.Column("action", sa.String(50)),
    sa.Column("description", sa.String(255)),
)

_roles = sa.Table(
    "roles",
    _metadata,
    sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
    sa.Column("tenant_id", PG_UUID(as_uuid=True)),
    sa.Column("name", sa.String(100)),
)

_role_permissions = sa.Table(
    "role_permissions",
    _metadata,
    sa.Column("role_id", PG_UUID(as_uuid=True), primary_key=True),
    sa.Column("permission_id", PG_UUID(as_uuid=True), primary_key=True),
)

_tenants = sa.Table(
    "tenants",
    _metadata,
    sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
    sa.Column("slug", sa.String(100)),
)


def propagate_permission_grant(
    bind: Connection,
    *,
    code: str,
    resource: str,
    action: str,
    description: str,
    granted_to_roles: Sequence[str],
) -> None:
    """Idempotently ensure permission `code` exists (inserted once, it is
    global reference data - `auth.models.Permission`, not tenant-scoped)
    and is granted to each role named in `granted_to_roles`, for EVERY
    tenant that has one.

    Idempotent: re-running against a database that already has the
    permission and/or some of the grants creates no duplicate rows (the
    permission upsert matches on its unique `code`; each grant upsert
    matches on the `role_permissions` composite primary key
    `(role_id, permission_id)`).

    Raises RuntimeError, granting nothing, if any tenant lacks a role named
    in `granted_to_roles` - see this module's docstring for why that is a
    deliberate fail-loud policy rather than a silent skip or auto-repair.
    Coverage is validated in full BEFORE any row is written - a real
    Alembic migration's transaction would roll back either way (this
    project's migrations run with transactional DDL), but this function
    does not lean on that: it never mutates anything unless every requested
    role is confirmed present for every tenant first.
    """
    tenant_ids = set(bind.execute(sa.select(_tenants.c.id)).scalars().all())

    role_rows_by_name: dict[str, list[tuple[uuid.UUID, uuid.UUID]]] = {}
    for role_name in granted_to_roles:
        rows = bind.execute(
            sa.select(_roles.c.id, _roles.c.tenant_id).where(_roles.c.name == role_name)
        ).all()
        covered_tenant_ids = {row.tenant_id for row in rows}
        missing = tenant_ids - covered_tenant_ids
        if missing:
            raise RuntimeError(
                f"propagate_permission_grant({code!r}): {len(missing)} tenant(s) have no "
                f"role named {role_name!r} - refusing to grant anything. "
                f"Missing tenant ids: {sorted(str(t) for t in missing)}"
            )
        role_rows_by_name[role_name] = [(row.id, row.tenant_id) for row in rows]

    bind.execute(
        pg_insert(_permissions)
        .values(id=uuid7(), code=code, resource=resource, action=action, description=description)
        .on_conflict_do_nothing(index_elements=["code"])
    )
    permission_id = bind.execute(
        sa.select(_permissions.c.id).where(_permissions.c.code == code)
    ).scalar_one()

    for role_ids_and_tenants in role_rows_by_name.values():
        for role_id, _tenant_id in role_ids_and_tenants:
            bind.execute(
                pg_insert(_role_permissions)
                .values(role_id=role_id, permission_id=permission_id)
                .on_conflict_do_nothing(index_elements=["role_id", "permission_id"])
            )
