import {
  PROFITABILITY_FILTER_VALUES,
  type ProfitabilityFilter,
} from "@/features/reports/constants/profitability";
import type { BoatProfitabilityParams } from "@/features/reports/types/boat-profitability";

export { PROFITABILITY_FILTER_VALUES as BOAT_PROFITABILITY_PROFITABILITY_VALUES };

/**
 * Boat Profitability filter/page state. Default range is All Time
 * (TASKS.md Sprint 11 Session 4 Phase A) - `fromDate`/`toDate` are an
 * opt-in narrowing filter, not a required range. `minTrips` is a plain
 * number (not a min/max range) - "Minimum Trips" is the report's own
 * literal filter name. No `sort` field - the backend's order is fixed
 * (`profit DESC, boat name ASC`), not client-configurable.
 */
export interface BoatProfitabilityFilters {
  search: string;
  boatId: string | null;
  fromDate: string | null;
  toDate: string | null;
  minTrips: number | null;
  profitability: ProfitabilityFilter | null;
  page: number;
  pageSize: number;
}

export const DEFAULT_BOAT_PROFITABILITY_FILTERS: BoatProfitabilityFilters = {
  search: "",
  boatId: null,
  fromDate: null,
  toDate: null,
  minTrips: null,
  profitability: null,
  page: 1,
  pageSize: 20,
};

/** Maps the client's filter state onto the backend's BoatProfitabilityParams query shape. */
export function toBoatProfitabilityParams(
  filters: BoatProfitabilityFilters
): BoatProfitabilityParams {
  return {
    boat_id: filters.boatId ?? undefined,
    from_date: filters.fromDate ?? undefined,
    to_date: filters.toDate ?? undefined,
    min_trips: filters.minTrips ?? undefined,
    profitability: filters.profitability ?? undefined,
    q: filters.search.trim() || undefined,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
