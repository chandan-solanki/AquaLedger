"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { tripKeys } from "@/features/trips/constants/query-keys";
import { tripService } from "@/features/trips/services/trip-service";
import type { TripUpdateRequest } from "@/features/trips/types/trip";

export interface UpdateTripVariables {
  id: string;
  payload: TripUpdateRequest;
}

export function useUpdateTrip() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: UpdateTripVariables) => tripService.updateTrip(id, payload),
    onSuccess: (trip) => {
      queryClient.invalidateQueries({ queryKey: tripKeys.lists() });
      queryClient.invalidateQueries({ queryKey: tripKeys.detail(trip.id) });
    },
  });
}
