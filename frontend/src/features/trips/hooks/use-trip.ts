"use client";

import { useQuery } from "@tanstack/react-query";

import { tripKeys } from "@/features/trips/constants/query-keys";
import { tripService } from "@/features/trips/services/trip-service";

/** A single trip record by id — disabled until an id is available. */
export function useTrip(id: string | undefined) {
  return useQuery({
    queryKey: tripKeys.detail(id ?? ""),
    queryFn: () => tripService.getTrip(id as string),
    enabled: Boolean(id),
  });
}
