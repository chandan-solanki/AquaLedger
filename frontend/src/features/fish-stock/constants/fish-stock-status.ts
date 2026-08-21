import type { StatusFilterOption } from "@/components/filters";

/**
 * Fish Stock has no `status` of its own - the `is_active` filter it exposes
 * is the underlying fish master's own active flag, per the backend's
 * `FishStockListParams.is_active` (app/modules/trip_catches/schemas.py).
 * A local copy of the active/inactive vocabulary, not imported from the
 * `fish` feature - mirrors `fish-status.ts`'s own shape.
 */
export type FishStockStatus = "active" | "inactive";

export const FISH_STOCK_STATUS_VALUES = [
  "active",
  "inactive",
] as const satisfies readonly FishStockStatus[];

export const FISH_STOCK_STATUS_OPTIONS: StatusFilterOption<FishStockStatus>[] = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
];

export const FISH_STOCK_STATUS_LABELS: Record<FishStockStatus, string> = {
  active: "Active",
  inactive: "Inactive",
};
