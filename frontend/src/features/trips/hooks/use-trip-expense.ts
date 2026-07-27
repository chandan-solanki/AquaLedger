"use client";

import { useQuery } from "@tanstack/react-query";

import { tripExpenseKeys } from "@/features/trips/constants/query-keys";
import { tripExpenseService } from "@/features/trips/services/trip-expense-service";

/** A single trip expense record by id — disabled until an id is available. */
export function useTripExpense(id: string | undefined) {
  return useQuery({
    queryKey: tripExpenseKeys.detail(id ?? ""),
    queryFn: () => tripExpenseService.getTripExpense(id as string),
    enabled: Boolean(id),
  });
}
