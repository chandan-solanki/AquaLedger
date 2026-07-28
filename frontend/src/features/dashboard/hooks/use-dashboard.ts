"use client";

import { useQuery } from "@tanstack/react-query";

import { dashboardKeys } from "@/features/dashboard/constants/query-keys";
import { dashboardService } from "@/features/dashboard/services/dashboard-service";

const FIVE_MINUTES_MS = 5 * 60 * 1000;

/**
 * The owner's homepage summary — a single consolidated fetch, per this
 * sprint's backend (GET /dashboard does all the aggregation server-side).
 * A 5-minute `staleTime` (overriding the app's 30-second default,
 * `lib/query-client.ts`) reflects that these are business aggregates, not
 * fast-moving list data — a manual Refresh button (wired to `refetch()` by
 * the page) is the intended way to force a recompute sooner.
 */
export function useDashboard() {
  return useQuery({
    queryKey: dashboardKeys.summary(),
    queryFn: dashboardService.getDashboard,
    staleTime: FIVE_MINUTES_MS,
  });
}
