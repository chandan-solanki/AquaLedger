"use client";

import { useQuery } from "@tanstack/react-query";

import { tripExpenseKeys } from "@/features/trips/constants/query-keys";
import { tripExpenseService } from "@/features/trips/services/trip-expense-service";

/** Max allowed by the backend (TripExpenseListParams.page_size, le=100) - the Trip Detail page's Expenses section shows every record for one trip, not a paginated list. */
const TRIP_EXPENSES_PAGE_SIZE = 100;

/** Every trip expense for one trip - disabled until a trip id is available. */
export function useTripExpenses(tripId: string | undefined) {
  return useQuery({
    queryKey: tripExpenseKeys.byTrip(tripId ?? ""),
    queryFn: () =>
      tripExpenseService.listTripExpenses({
        trip_id: tripId as string,
        page: 1,
        page_size: TRIP_EXPENSES_PAGE_SIZE,
      }),
    enabled: Boolean(tripId),
  });
}
