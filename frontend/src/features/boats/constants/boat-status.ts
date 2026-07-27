import type { StatusFilterOption } from "@/components/filters";

/** Boats have no `status` field on the backend, only `is_active` (boolean) - this is the display/filter vocabulary derived from it, mirroring `fish-status.ts`. */
export type BoatStatus = "active" | "inactive";

export const BOAT_STATUS_VALUES = ["active", "inactive"] as const satisfies readonly BoatStatus[];

export const BOAT_STATUS_OPTIONS: StatusFilterOption<BoatStatus>[] = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
];

export const BOAT_STATUS_LABELS: Record<BoatStatus, string> = {
  active: "Active",
  inactive: "Inactive",
};

/** Badge variant per status, per `02_DESIGN_SYSTEM.md`'s Status Badge category default. */
export const BOAT_STATUS_BADGE_VARIANT: Record<BoatStatus, "default" | "secondary"> = {
  active: "default",
  inactive: "secondary",
};

export function toBoatStatus(isActive: boolean): BoatStatus {
  return isActive ? "active" : "inactive";
}
