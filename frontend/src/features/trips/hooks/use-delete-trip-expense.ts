"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { tripExpenseKeys } from "@/features/trips/constants/query-keys";
import { tripExpenseService } from "@/features/trips/services/trip-expense-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

export interface DeleteTripExpenseVariables {
  id: string;
  /** The owning trip's id - deletion returns no body (204), so the caller (already on that trip's Detail page) supplies it, letting invalidation stay scoped to exactly that trip's `byTrip` query rather than every trip's. */
  tripId: string;
}

/**
 * Owns the full delete outcome (cache invalidation, toast) so every call
 * site gets identical behavior, mirroring `useDeleteTripCatch` - no
 * post-delete navigation, since deleting an expense row happens inline on
 * the Trip Detail page's own table, not a page the user needs to leave.
 */
export function useDeleteTripExpense() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id }: DeleteTripExpenseVariables) => tripExpenseService.deleteTripExpense(id),
    onSuccess: (_data, { id, tripId }) => {
      queryClient.invalidateQueries({ queryKey: tripExpenseKeys.byTrip(tripId) });
      queryClient.removeQueries({ queryKey: tripExpenseKeys.detail(id) });
      toastSuccess("Trip expense deleted.");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
