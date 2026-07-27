"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { tripKeys } from "@/features/trips/constants/query-keys";
import { tripService } from "@/features/trips/services/trip-service";
import type { TripCreateRequest } from "@/features/trips/types/trip";

export function useCreateTrip() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: TripCreateRequest) => tripService.createTrip(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tripKeys.lists() });
    },
  });
}
