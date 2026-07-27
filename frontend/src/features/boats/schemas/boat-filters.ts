import type { BoatListParams } from "@/features/boats/types/boat";
import type { BoatStatus } from "@/features/boats/constants/boat-status";

/** Matches the backend's `_SORTABLE_FIELDS` (app/modules/boats/schemas.py) exactly. */
export const BOAT_SORT_FIELDS = ["name", "code", "created_at", "updated_at"] as const;
export type BoatSortField = (typeof BOAT_SORT_FIELDS)[number];

export const BOAT_SORT_DIRECTIONS = ["asc", "desc"] as const;
export type BoatSortDirection = (typeof BOAT_SORT_DIRECTIONS)[number];

/**
 * `sort`/`direction` are kept separate here (rather than the backend's
 * combined `-field` string) since each is its own URL search param,
 * mirroring `FishFilters` - `toBoatListParams` recombines them into the wire
 * format the backend actually expects.
 */
export interface BoatFilters {
  search: string;
  status: BoatStatus | null;
  boatType: string;
  insuranceExpired: boolean | null;
  licenseExpired: boolean | null;
  page: number;
  pageSize: number;
  sort: BoatSortField;
  direction: BoatSortDirection;
}

export const DEFAULT_BOAT_FILTERS: BoatFilters = {
  search: "",
  status: null,
  boatType: "",
  insuranceExpired: null,
  licenseExpired: null,
  page: 1,
  pageSize: 20,
  sort: "created_at",
  direction: "desc",
};

/** Maps the client's filter state onto the backend's BoatListParams query shape. */
export function toBoatListParams(filters: BoatFilters): BoatListParams {
  return {
    q: filters.search.trim() || undefined,
    boat_type: filters.boatType.trim() || undefined,
    is_active: filters.status === "active" ? true : filters.status === "inactive" ? false : undefined,
    insurance_expired: filters.insuranceExpired ?? undefined,
    license_expired: filters.licenseExpired ?? undefined,
    sort: filters.direction === "desc" ? `-${filters.sort}` : filters.sort,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
