"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { tripCatchKeys } from "@/features/trips/constants/query-keys";
import { tripCatchService } from "@/features/trips/services/trip-catch-service";
import type { TripCatchUpdateRequest } from "@/features/trips/types/trip-catch";

export interface UpdateTripCatchVariables {
  id: string;
  payload: TripCatchUpdateRequest;
}

export function useUpdateTripCatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: UpdateTripCatchVariables) => tripCatchService.updateTripCatch(id, payload),
    onSuccess: (tripCatch) => {
      queryClient.invalidateQueries({ queryKey: tripCatchKeys.byTrip(tripCatch.tripId) });
      queryClient.invalidateQueries({ queryKey: tripCatchKeys.detail(tripCatch.id) });
    },
  });
}
