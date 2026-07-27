"use client";

import { useQuery } from "@tanstack/react-query";

import { tripCatchKeys } from "@/features/trips/constants/query-keys";
import { tripCatchService } from "@/features/trips/services/trip-catch-service";

/** Max allowed by the backend (TripCatchListParams.page_size, le=100) - the Trip Detail page's Catch section shows every record for one trip, not a paginated list. */
const TRIP_CATCHES_PAGE_SIZE = 100;

/** Every trip catch for one trip - disabled until a trip id is available. */
export function useTripCatches(tripId: string | undefined) {
  return useQuery({
    queryKey: tripCatchKeys.byTrip(tripId ?? ""),
    queryFn: () =>
      tripCatchService.listTripCatches({
        trip_id: tripId as string,
        page: 1,
        page_size: TRIP_CATCHES_PAGE_SIZE,
      }),
    enabled: Boolean(tripId),
  });
}
