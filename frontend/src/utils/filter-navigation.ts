import type { NavItem } from "@/config/navigation";
import { hasAnyPermission, hasPermission } from "@/utils/permissions";

function isItemVisible(item: NavItem, permissions: readonly string[], isSuperuser: boolean): boolean {
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
  isSuperuser: boolean
): NavItem[] {
  const result: NavItem[] = [];

  for (const item of items) {
    if (item.children) {
      const children = filterNavigation(item.children, permissions, isSuperuser);
      if (children.length > 0) {
        result.push({ ...item, children });
      }
      continue;
    }

    if (isItemVisible(item, permissions, isSuperuser)) {
      result.push(item);
    }
  }

  return result;
}
