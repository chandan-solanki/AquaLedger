"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import type { ComboboxOption } from "@/components/form";
import { tripKeys, tripService } from "@/features/trips";
import type { TripListParams } from "@/features/trips";

const TRIP_OPTIONS_PARAMS: TripListParams = { sort: "trip_number", page: 1, page_size: 100 };

/**
 * Every trip for this tenant, for the Fish Sales Analytics report's Trip
 * selector - sourced from the Trips feature's own public surface
 * (`@/features/trips`), never another feature's internals (mirrors
 * `useCustomerOptions`'s own stated rule).
 */
export function useTripOptions() {
  const query = useQuery({
    queryKey: tripKeys.list(TRIP_OPTIONS_PARAMS),
    queryFn: () => tripService.listTrips(TRIP_OPTIONS_PARAMS),
    staleTime: 5 * 60 * 1000,
  });

  const trips = query.data?.data;

  return useMemo(() => {
    const list = trips ?? [];
    return {
      options: list.map((trip): ComboboxOption => ({ value: trip.id, label: trip.tripNumber })),
      nameById: new Map(list.map((trip) => [trip.id, trip.tripNumber])),
      isLoading: query.isLoading,
    };
  }, [trips, query.isLoading]);
}
