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
