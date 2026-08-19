import type { StatusFilterOption } from "@/components/filters";
import type { UserAccountStatus, UserStatusAction } from "@/features/users/types/user";

/** Every status the backend can report, including the two system-managed
 * ones (locked, password_expired) that never appear as filter/action
 * options - they're display-only outcomes of AuthService's own logic. */
export const USER_STATUS_LABELS: Record<UserAccountStatus, string> = {
  active: "Active",
  inactive: "Inactive",
  locked: "Locked",
  password_expired: "Password Expired",
};

/** Badge variant per status, per `02_DESIGN_SYSTEM.md`'s Status Badge category default. */
export const USER_STATUS_BADGE_VARIANT: Record<
  UserAccountStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  active: "default",
  inactive: "secondary",
  locked: "destructive",
  password_expired: "outline",
};

/** Only active/inactive are usable as a list filter or an admin-triggered status action. */
export const USER_STATUS_ACTION_VALUES = ["active", "inactive"] as const satisfies readonly UserStatusAction[];

export const USER_STATUS_FILTER_OPTIONS: StatusFilterOption<UserAccountStatus>[] = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
  { value: "locked", label: "Locked" },
  { value: "password_expired", label: "Password Expired" },
];
