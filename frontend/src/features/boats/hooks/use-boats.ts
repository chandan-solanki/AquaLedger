"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { boatKeys } from "@/features/boats/constants/query-keys";
import type { BoatFilters } from "@/features/boats/schemas/boat-filters";
import { toBoatListParams } from "@/features/boats/schemas/boat-filters";
import { boatService } from "@/features/boats/services/boat-service";

/**
 * Server-side, paginated boat list — every filter/sort/page change refetches
 * from the backend rather than filtering an already-loaded page client-side.
 * `keepPreviousData` keeps the current rows on screen (instead of flashing
 * to a loading state) while a filter/page change is in flight.
 */
export function useBoats(filters: BoatFilters) {
  const params = toBoatListParams(filters);

  return useQuery({
    queryKey: boatKeys.list(params),
    queryFn: () => boatService.listBoats(params),
    placeholderData: keepPreviousData,
  });
}
