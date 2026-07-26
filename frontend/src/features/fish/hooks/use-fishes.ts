"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { fishKeys } from "@/features/fish/constants/query-keys";
import type { FishFilters } from "@/features/fish/schemas/fish-filters";
import { toFishListParams } from "@/features/fish/schemas/fish-filters";
import { fishService } from "@/features/fish/services/fish-service";

/**
 * Server-side, paginated fish list — every filter/sort/page change refetches
 * from the backend rather than filtering an already-loaded page client-side.
 * `keepPreviousData` keeps the current rows on screen (instead of flashing
 * to a loading state) while a filter/page change is in flight.
 */
export function useFishes(filters: FishFilters) {
  const params = toFishListParams(filters);

  return useQuery({
    queryKey: fishKeys.list(params),
    queryFn: () => fishService.listFish(params),
    placeholderData: keepPreviousData,
  });
}
