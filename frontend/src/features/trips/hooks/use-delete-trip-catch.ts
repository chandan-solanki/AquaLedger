"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { tripCatchKeys } from "@/features/trips/constants/query-keys";
import { tripCatchService } from "@/features/trips/services/trip-catch-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

export interface DeleteTripCatchVariables {
  id: string;
  /** The owning trip's id - deletion returns no body (204), so the caller (already on that trip's Detail page) supplies it, letting invalidation stay scoped to exactly that trip's `byTrip` query rather than every trip's. */
  tripId: string;
}

/**
 * Owns the full delete outcome (cache invalidation, toast) so every call
 * site gets identical behavior, mirroring `useDeleteBoat`/`useDeleteTrip` -
 * minus the post-delete navigation those have, since deleting a catch row
 * happens inline on the Trip Detail page's own table, not a page the user
 * needs to leave.
 */
export function useDeleteTripCatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id }: DeleteTripCatchVariables) => tripCatchService.deleteTripCatch(id),
    onSuccess: (_data, { id, tripId }) => {
      queryClient.invalidateQueries({ queryKey: tripCatchKeys.byTrip(tripId) });
      queryClient.removeQueries({ queryKey: tripCatchKeys.detail(id) });
      toastSuccess("Trip catch deleted.");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
