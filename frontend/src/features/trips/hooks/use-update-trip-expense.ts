"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { tripExpenseKeys } from "@/features/trips/constants/query-keys";
import { tripExpenseService } from "@/features/trips/services/trip-expense-service";
import type { TripExpenseUpdateRequest } from "@/features/trips/types/trip-expense";

export interface UpdateTripExpenseVariables {
  id: string;
  payload: TripExpenseUpdateRequest;
}

export function useUpdateTripExpense() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: UpdateTripExpenseVariables) =>
      tripExpenseService.updateTripExpense(id, payload),
    onSuccess: (tripExpense) => {
      queryClient.invalidateQueries({ queryKey: tripExpenseKeys.byTrip(tripExpense.tripId) });
      queryClient.invalidateQueries({ queryKey: tripExpenseKeys.detail(tripExpense.id) });
    },
  });
}
