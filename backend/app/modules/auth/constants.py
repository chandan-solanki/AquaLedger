from enum import StrEnum


class AccountStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    PASSWORD_EXPIRED = "password_expired"  # noqa: S105 - enum value, not a credential


class TenantStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


# The one tenant seeded by migration 67c33121fc54 - the only reliable source
# of "what system roles/permissions does a tenant get" (Sprint 17 Session 2
# audit: that seed data is deliberately not importable from app/, so new
# tenants replicate this tenant's live roles/role_permissions at
# provisioning time rather than a second hardcoded copy that would drift).
DEFAULT_TENANT_SLUG = "default"


# System role names. Roles are admin-editable data; these are only the
# ones seeded by default (see migrations for the seeded permission set).
SUPER_ADMIN_ROLE = "super_admin"
ADMIN_ROLE = "admin"
MANAGER_ROLE = "manager"
ACCOUNTANT_ROLE = "accountant"
OPERATOR_ROLE = "operator"

SYSTEM_ROLES = (
    SUPER_ADMIN_ROLE,
    ADMIN_ROLE,
    MANAGER_ROLE,
    ACCOUNTANT_ROLE,
    OPERATOR_ROLE,
)
