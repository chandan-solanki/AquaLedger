"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { reportKeys } from "@/features/reports/constants/query-keys";
import { toTripProfitabilityParams } from "@/features/reports/schemas/trip-profitability-filters";
import type { TripProfitabilityFilters } from "@/features/reports/schemas/trip-profitability-filters";
import { reportsService } from "@/features/reports/services/reports-service";

/**
 * The Trip Profitability report's server-side, paginated fetch - always
 * enabled, `boat_id` is an optional filter, not a required backend param
 * (mirrors `useSalesReport`). `keepPreviousData` keeps the current rows on
 * screen while a filter/page change is in flight.
 */
export function useTripProfitability(filters: TripProfitabilityFilters) {
  const params = toTripProfitabilityParams(filters);

  return useQuery({
    queryKey: reportKeys.tripProfitabilityResult(params),
    queryFn: () => reportsService.getTripProfitability(params),
    placeholderData: keepPreviousData,
  });
}
