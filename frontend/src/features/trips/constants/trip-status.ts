import type { StatusFilterOption } from "@/components/filters";
import type { TripStatus } from "@/features/trips/types/trip";

export const TRIP_STATUS_VALUES = [
  "planned",
  "departed",
  "returned",
  "cancelled",
] as const satisfies readonly TripStatus[];

export const TRIP_STATUS_OPTIONS: StatusFilterOption<TripStatus>[] = [
  { value: "planned", label: "Planned" },
  { value: "departed", label: "Departed" },
  { value: "returned", label: "Returned" },
  { value: "cancelled", label: "Cancelled" },
];

export const TRIP_STATUS_LABELS: Record<TripStatus, string> = {
  planned: "Planned",
  departed: "Departed",
  returned: "Returned",
  cancelled: "Cancelled",
};

/**
 * Badge variant per status, per `02_DESIGN_SYSTEM.md` §13's Status System -
 * `planned` (not yet underway) reads as neutral/outline, `departed` (the
 * boat is actively at sea) as the primary/active `default`, `returned`
 * (a resolved, positive close) as `secondary`, and `cancelled` as
 * `destructive`, the closest match to the design system's "muted danger"
 * guidance among this component's actual variants.
 */
export const TRIP_STATUS_BADGE_VARIANT: Record<
  TripStatus,
  "default" | "secondary" | "outline" | "destructive"
> = {
  planned: "outline",
  departed: "default",
  returned: "secondary",
  cancelled: "destructive",
};
