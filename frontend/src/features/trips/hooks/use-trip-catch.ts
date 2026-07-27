"use client";

import { useQuery } from "@tanstack/react-query";

import { tripCatchKeys } from "@/features/trips/constants/query-keys";
import { tripCatchService } from "@/features/trips/services/trip-catch-service";

/** A single trip catch record by id — disabled until an id is available. */
export function useTripCatch(id: string | undefined) {
  return useQuery({
    queryKey: tripCatchKeys.detail(id ?? ""),
    queryFn: () => tripCatchService.getTripCatch(id as string),
    enabled: Boolean(id),
  });
}
