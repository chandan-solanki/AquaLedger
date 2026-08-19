import type { StatusFilterOption } from "@/components/filters";

/**
 * Every action code any module currently writes via
 * AuthRepository.add_audit_log (app/modules/auth/repository.py) - auth's
 * own login/logout/password-change events plus the Users module's
 * create/update/status/role-change events added in this session
 * (app/modules/users/service.py). A future module's new action code still
 * renders correctly without a frontend change - see humanizeAuditAction's
 * fallback below.
 */
export const AUDIT_LOG_ACTION_LABELS: Record<string, string> = {
  login_success: "Login",
  login_failed: "Login Failed",
  logout: "Logout",
  password_changed: "Password Changed",
  user_created: "User Created",
  user_updated: "User Updated",
  user_activated: "User Activated",
  user_deactivated: "User Deactivated",
  user_role_changed: "Role Changed",
};

/** Badge variant per action - destructive for security-negative events
 * (failed login, deactivation), default for creation/activation, secondary
 * for a plain edit, outline for routine session events. */
export const AUDIT_LOG_ACTION_BADGE_VARIANT: Record<
  string,
  "default" | "secondary" | "destructive" | "outline"
> = {
  login_success: "outline",
  login_failed: "destructive",
  logout: "outline",
  password_changed: "secondary",
  user_created: "default",
  user_updated: "secondary",
  user_activated: "default",
  user_deactivated: "destructive",
  user_role_changed: "secondary",
};

/** Falls back to a humanized version of the raw code for an action this
 * frontend doesn't have a label for yet, rather than hiding it. */
export function humanizeAuditAction(action: string): string {
  return (
    AUDIT_LOG_ACTION_LABELS[action] ??
    action
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ")
  );
}

export const AUDIT_LOG_ACTION_OPTIONS: StatusFilterOption<string>[] = Object.entries(
  AUDIT_LOG_ACTION_LABELS
).map(([value, label]) => ({ value, label }));

/** Every entity_type any module currently writes - "user" only, today. */
export const AUDIT_LOG_ENTITY_TYPE_LABELS: Record<string, string> = {
  user: "User",
};

export function humanizeAuditEntityType(entityType: string): string {
  return (
    AUDIT_LOG_ENTITY_TYPE_LABELS[entityType] ??
    entityType.charAt(0).toUpperCase() + entityType.slice(1)
  );
}

export const AUDIT_LOG_ENTITY_TYPE_OPTIONS: StatusFilterOption<string>[] = Object.entries(
  AUDIT_LOG_ENTITY_TYPE_LABELS
).map(([value, label]) => ({ value, label }));
