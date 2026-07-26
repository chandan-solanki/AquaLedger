import type { StatusFilterOption } from "@/components/filters";

/** Fish has no `status` field on the backend, only `is_active` (boolean) - this is the display/filter vocabulary derived from it, mirroring `company-status.ts`. */
export type FishStatus = "active" | "inactive";

export const FISH_STATUS_VALUES = ["active", "inactive"] as const satisfies readonly FishStatus[];

export const FISH_STATUS_OPTIONS: StatusFilterOption<FishStatus>[] = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
];

export const FISH_STATUS_LABELS: Record<FishStatus, string> = {
  active: "Active",
  inactive: "Inactive",
};

/** Badge variant per status, per `02_DESIGN_SYSTEM.md`'s Status Badge category default. */
export const FISH_STATUS_BADGE_VARIANT: Record<FishStatus, "default" | "secondary"> = {
  active: "default",
  inactive: "secondary",
};

export function toFishStatus(isActive: boolean): FishStatus {
  return isActive ? "active" : "inactive";
}
