import type { StatusFilterOption } from "@/components/filters";
import type { TenantStatus } from "@/features/platform/types/tenant";

export const TENANT_STATUS_VALUES = ["active", "suspended", "inactive"] as const satisfies readonly TenantStatus[];

export const TENANT_STATUS_OPTIONS: StatusFilterOption<TenantStatus>[] = [
  { value: "active", label: "Active" },
  { value: "suspended", label: "Suspended" },
  { value: "inactive", label: "Inactive" },
];

export const TENANT_STATUS_LABELS: Record<TenantStatus, string> = {
  active: "Active",
  suspended: "Suspended",
  inactive: "Inactive",
};

/**
 * Badge variant per status, per `02_DESIGN_SYSTEM.md`'s Status Badge
 * category default. "suspended" is `destructive` (an active tenant that has
 * just been cut off - the same urgency as a "locked" user account);
 * "inactive" is `secondary` (a deliberate, settled state, not an in-progress
 * problem) - the two must never share a color, since a platform admin needs
 * to tell them apart at a glance.
 */
export const TENANT_STATUS_BADGE_VARIANT: Record<TenantStatus, "default" | "secondary" | "destructive"> = {
  active: "default",
  suspended: "destructive",
  inactive: "secondary",
};
