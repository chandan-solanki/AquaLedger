import {
  PROFITABILITY_FILTER_VALUES,
  type ProfitabilityFilter,
} from "@/features/reports/constants/profitability";
import type { TripProfitabilityParams } from "@/features/reports/types/trip-profitability";

export { PROFITABILITY_FILTER_VALUES as TRIP_PROFITABILITY_PROFITABILITY_VALUES };

/**
 * Trip Profitability filter/page state. Unlike the Ledgers' resource-key
 * filters, `boatId` is an optional narrowing filter, not a required
 * backend param - the report loads with every completed trip by default.
 * There is no `status` field - only `returned` trips are ever eligible (a
 * hard backend invariant), and no `sort` field - the backend's order is
 * fixed (`return date DESC, trip number DESC`), not client-configurable.
 */
export interface TripProfitabilityFilters {
  search: string;
  boatId: string | null;
  fromDate: string | null;
  toDate: string | null;
  profitability: ProfitabilityFilter | null;
  page: number;
  pageSize: number;
}

export const DEFAULT_TRIP_PROFITABILITY_FILTERS: TripProfitabilityFilters = {
  search: "",
  boatId: null,
  fromDate: null,
  toDate: null,
  profitability: null,
  page: 1,
  pageSize: 20,
};

/** Maps the client's filter state onto the backend's TripProfitabilityParams query shape. */
export function toTripProfitabilityParams(
  filters: TripProfitabilityFilters
): TripProfitabilityParams {
  return {
    boat_id: filters.boatId ?? undefined,
    from_date: filters.fromDate ?? undefined,
    to_date: filters.toDate ?? undefined,
    profitability: filters.profitability ?? undefined,
    q: filters.search.trim() || undefined,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
