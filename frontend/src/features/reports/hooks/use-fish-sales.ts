"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { reportKeys } from "@/features/reports/constants/query-keys";
import { toFishSalesParams } from "@/features/reports/schemas/fish-sales-filters";
import type { FishSalesFilters } from "@/features/reports/schemas/fish-sales-filters";
import type { FishSalesParams } from "@/features/reports/types/fish-sales";
import { reportsService } from "@/features/reports/services/reports-service";

/**
 * The Fish Sales Analytics report's server-side, paginated fetch - always
 * enabled, every entity filter is optional, not a required backend param
 * (mirrors `useSalesReport`). `keepPreviousData` keeps the current rows on
 * screen while a filter/page change is in flight.
 */
export function useFishSales(filters: FishSalesFilters) {
  const params = toFishSalesParams(filters);

  return useQuery({
    queryKey: reportKeys.fishSalesResult(params),
    queryFn: () => reportsService.getFishSales(params),
    placeholderData: keepPreviousData,
  });
}

/**
 * A single fish's Lifetime Summary, for the Fish Detail page's own Sales
 * Analytics tab - the same GET /reports/fish-sales endpoint, narrowed to
 * `fish_id` with no other filters and `page_size: 1` (a single fish can
 * only ever produce one row). A fish never sold yields an empty `rows`
 * array, not a 404 - the caller renders its own empty state for that case.
 */
export function useFishLifetimeSales(fishId: string | undefined) {
  const params: FishSalesParams = { fish_id: fishId, page: 1, page_size: 1 };

  return useQuery({
    queryKey: reportKeys.fishSalesResult(params),
    queryFn: () => reportsService.getFishSales(params),
    enabled: Boolean(fishId),
  });
}
