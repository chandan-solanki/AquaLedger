"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { tripKeys } from "@/features/trips/constants/query-keys";
import type { TripFilters } from "@/features/trips/schemas/trip-filters";
import { toTripListParams } from "@/features/trips/schemas/trip-filters";
import { tripService } from "@/features/trips/services/trip-service";

/**
 * Server-side, paginated trip list — every filter/sort/page change refetches
 * from the backend rather than filtering an already-loaded page client-side.
 * `keepPreviousData` keeps the current rows on screen (instead of flashing
 * to a loading state) while a filter/page change is in flight.
 */
export function useTrips(filters: TripFilters) {
  const params = toTripListParams(filters);

  return useQuery({
    queryKey: tripKeys.list(params),
    queryFn: () => tripService.listTrips(params),
    placeholderData: keepPreviousData,
  });
}
