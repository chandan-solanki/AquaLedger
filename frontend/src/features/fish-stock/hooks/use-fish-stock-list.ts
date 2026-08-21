"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { fishStockKeys } from "@/features/fish-stock/constants/query-keys";
import type { FishStockFilters } from "@/features/fish-stock/schemas/fish-stock-filters";
import { toFishStockListParams } from "@/features/fish-stock/schemas/fish-stock-filters";
import { fishStockService } from "@/features/fish-stock/services/fish-stock-service";

/**
 * Server-side, paginated Fish Stock list — every filter/page change refetches
 * from the backend's aggregation rather than filtering an already-loaded
 * page client-side (Session 2's GET /fish-stock already does the summing).
 * `keepPreviousData` keeps the current rows on screen while a filter/page
 * change is in flight, mirroring `useFishes`.
 */
export function useFishStockList(filters: FishStockFilters) {
  const params = toFishStockListParams(filters);

  return useQuery({
    queryKey: fishStockKeys.list(params),
    queryFn: () => fishStockService.listFishStock(params),
    placeholderData: keepPreviousData,
  });
}
