import type { NavItem } from "@/config/navigation";
import { hasAnyPermission, hasPermission } from "@/utils/permissions";

function isItemVisible(
  item: NavItem,
  permissions: readonly string[],
  isSuperuser: boolean,
  isPlatformAdmin: boolean
): boolean {
  // Sprint 17: `platformOnly` is a strictly separate boundary from
  // permission codes and `isSuperuser` - it is never satisfied by holding
  // every permission or by the tenant superuser bypass, only by the
  // platform-admin flag itself (mirrors the backend's require_platform_admin,
  // which has no is_superuser exception either).
  if (item.platformOnly && !isPlatformAdmin) return false;
  // Sprint 17 Session 5: the inverse case - an item with no permission gate
  // (visible to every ordinary tenant role) that would still be a dead,
  // redirecting duplicate for a platform admin, since TenantDashboardGuard
  // already sends them straight to /platform/dashboard.
  if (item.hiddenForPlatformAdmin && isPlatformAdmin) return false;
  if (!item.permission) return true;
  if (Array.isArray(item.permission)) return hasAnyPermission(permissions, item.permission, isSuperuser);
  return hasPermission(permissions, item.permission, isSuperuser);
}

/**
 * Filters the navigation tree down to what the current user can actually
 * see — unauthorized items are removed entirely, never rendered-and-disabled
 * (03_INFORMATION_ARCHITECTURE.md §13). A group is kept only if at least
 * one of its children survives filtering, per §3's "group visible to any
 * role with read access to at least one child" rule.
 */
export function filterNavigation(
  items: readonly NavItem[],
  permissions: readonly string[],
  isSuperuser: boolean,
  isPlatformAdmin = false
): NavItem[] {
  const result: NavItem[] = [];

  for (const item of items) {
    if (item.children) {
      const children = filterNavigation(item.children, permissions, isSuperuser, isPlatformAdmin);
      if (children.length > 0) {
        result.push({ ...item, children });
      }
      continue;
    }

    if (isItemVisible(item, permissions, isSuperuser, isPlatformAdmin)) {
      result.push(item);
    }
  }

  return result;
}
