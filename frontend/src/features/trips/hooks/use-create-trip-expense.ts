"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { tripExpenseKeys } from "@/features/trips/constants/query-keys";
import { tripExpenseService } from "@/features/trips/services/trip-expense-service";
import type { TripExpenseCreateRequest } from "@/features/trips/types/trip-expense";

export function useCreateTripExpense() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: TripExpenseCreateRequest) => tripExpenseService.createTripExpense(payload),
    onSuccess: (tripExpense) => {
      queryClient.invalidateQueries({ queryKey: tripExpenseKeys.byTrip(tripExpense.tripId) });
    },
  });
}
