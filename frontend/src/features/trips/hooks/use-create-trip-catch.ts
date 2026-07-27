"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { tripCatchKeys } from "@/features/trips/constants/query-keys";
import { tripCatchService } from "@/features/trips/services/trip-catch-service";
import type { TripCatchCreateRequest } from "@/features/trips/types/trip-catch";

export function useCreateTripCatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: TripCatchCreateRequest) => tripCatchService.createTripCatch(payload),
    onSuccess: (tripCatch) => {
      queryClient.invalidateQueries({ queryKey: tripCatchKeys.byTrip(tripCatch.tripId) });
    },
  });
}
