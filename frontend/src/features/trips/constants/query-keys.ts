import type { TripListParams } from "@/features/trips/types/trip";

export const tripKeys = {
  all: () => ["trips"] as const,
  lists: () => [...tripKeys.all(), "list"] as const,
  list: (params: TripListParams) => [...tripKeys.lists(), params] as const,
  details: () => [...tripKeys.all(), "detail"] as const,
  detail: (id: string) => [...tripKeys.details(), id] as const,
};

/**
 * Trip Catch/Expenses are only ever listed one way - all records for one
 * trip (the Trip Detail page's sub-tables, see `use-trip-catches.ts`/
 * `use-trip-expenses.ts`) - so each key builder has a single `byTrip` entry
 * rather than the fuller `list(params)` shape `tripKeys` needs for its
 * filterable List page. `detail(id)` was added in Session 6 for the
 * Edit page's single-record fetch (`use-trip-catch.ts`/`use-trip-expense.ts`)
 * and for scoping mutation cache invalidation, mirroring `tripKeys.detail`.
 */
export const tripCatchKeys = {
  all: () => ["trip-catches"] as const,
  byTrip: (tripId: string) => [...tripCatchKeys.all(), "trip", tripId] as const,
  details: () => [...tripCatchKeys.all(), "detail"] as const,
  detail: (id: string) => [...tripCatchKeys.details(), id] as const,
};

export const tripExpenseKeys = {
  all: () => ["trip-expenses"] as const,
  byTrip: (tripId: string) => [...tripExpenseKeys.all(), "trip", tripId] as const,
  details: () => [...tripExpenseKeys.all(), "detail"] as const,
  detail: (id: string) => [...tripExpenseKeys.details(), id] as const,
};
