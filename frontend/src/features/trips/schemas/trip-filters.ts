import type { TripListParams, TripStatus } from "@/features/trips/types/trip";

/** Matches the backend's `_SORTABLE_FIELDS` (app/modules/trips/schemas.py) exactly. */
export const TRIP_SORT_FIELDS = [
  "trip_number",
  "departure_datetime",
  "created_at",
  "updated_at",
] as const;
export type TripSortField = (typeof TRIP_SORT_FIELDS)[number];

export const TRIP_SORT_DIRECTIONS = ["asc", "desc"] as const;
export type TripSortDirection = (typeof TRIP_SORT_DIRECTIONS)[number];

/**
 * `sort`/`direction` are kept separate here (rather than the backend's
 * combined `-field` string) since each is its own URL search param,
 * mirroring `BoatFilters` - `toTripListParams` recombines them into the wire
 * format the backend actually expects. `boat` holds a `boat_id` (selected
 * via the Boat filter's dropdown, not free text). The backend also supports
 * `trip_type` and departure/return date-range filters
 * (app/modules/trips/schemas.py's `TripListParams`) - left unwired to a UI
 * control until a later session's filter panel needs them.
 */
export interface TripFilters {
  search: string;
  status: TripStatus | null;
  boat: string | null;
  page: number;
  pageSize: number;
  sort: TripSortField;
  direction: TripSortDirection;
}

export const DEFAULT_TRIP_FILTERS: TripFilters = {
  search: "",
  status: null,
  boat: null,
  page: 1,
  pageSize: 20,
  sort: "created_at",
  direction: "desc",
};

/** Maps the client's filter state onto the backend's TripListParams query shape. */
export function toTripListParams(filters: TripFilters): TripListParams {
  return {
    q: filters.search.trim() || undefined,
    boat_id: filters.boat ?? undefined,
    status: filters.status ?? undefined,
    sort: filters.direction === "desc" ? `-${filters.sort}` : filters.sort,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
