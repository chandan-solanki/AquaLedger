"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { reportKeys } from "@/features/reports/constants/query-keys";
import { toBoatProfitabilityParams } from "@/features/reports/schemas/boat-profitability-filters";
import type { BoatProfitabilityFilters } from "@/features/reports/schemas/boat-profitability-filters";
import type { BoatProfitabilityParams } from "@/features/reports/types/boat-profitability";
import { reportsService } from "@/features/reports/services/reports-service";

/**
 * The Boat Profitability report's server-side, paginated fetch - always
 * enabled, `boat_id` is an optional filter, not a required backend param.
 * `keepPreviousData` keeps the current rows on screen while a filter/page
 * change is in flight.
 */
export function useBoatProfitability(filters: BoatProfitabilityFilters) {
  const params = toBoatProfitabilityParams(filters);

  return useQuery({
    queryKey: reportKeys.boatProfitabilityResult(params),
    queryFn: () => reportsService.getBoatProfitability(params),
    placeholderData: keepPreviousData,
  });
}

/**
 * A single boat's Lifetime Summary + Profit figures, for the Boat Detail
 * page's own Profitability tab - the same GET /reports/boat-profitability
 * endpoint, narrowed to `boat_id` with no date range (All Time) and
 * `page_size: 1` (a single boat can only ever produce one row). A boat with
 * zero completed trips yields an empty `rows` array, not a 404 - the caller
 * renders its own empty state for that case.
 */
export function useBoatLifetimeProfitability(boatId: string | undefined) {
  const params: BoatProfitabilityParams = { boat_id: boatId, page: 1, page_size: 1 };

  return useQuery({
    queryKey: reportKeys.boatProfitabilityResult(params),
    queryFn: () => reportsService.getBoatProfitability(params),
    enabled: Boolean(boatId),
  });
}
