/**
 * Pure RBAC permission checks (07_FRONTEND_ARCHITECTURE.md §11). A
 * read-only reflection of the backend's resource:action permission model —
 * never a security boundary on its own, since every gated action is
 * re-validated server-side regardless of what these return. Mirrors the
 * backend's own superuser bypass (app/modules/auth/permissions.py).
 */

export function hasPermission(
  permissions: readonly string[],
  code: string,
  isSuperuser = false
): boolean {
  return isSuperuser || permissions.includes(code);
}

export function hasAnyPermission(
  permissions: readonly string[],
  codes: readonly string[],
  isSuperuser = false
): boolean {
  return isSuperuser || codes.some((code) => permissions.includes(code));
}

export function hasAllPermissions(
  permissions: readonly string[],
  codes: readonly string[],
  isSuperuser = false
): boolean {
  return isSuperuser || codes.every((code) => permissions.includes(code));
}
