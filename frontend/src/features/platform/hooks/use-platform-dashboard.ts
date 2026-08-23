"use client";

import { useQuery } from "@tanstack/react-query";

import { platformDashboardKeys } from "@/features/platform/constants/query-keys";
import { platformDashboardService } from "@/features/platform/services/platform-dashboard-service";

const FIVE_MINUTES_MS = 5 * 60 * 1000;

/**
 * The platform admin's landing summary — mirrors useDashboard()'s rationale
 * exactly: a 5-minute staleTime since tenant counts are lifecycle
 * aggregates, not fast-moving list data, with a manual Refresh button
 * (wired to `refetch()` by the page) as the intended way to force a
 * recompute sooner.
 */
export function usePlatformDashboard() {
  return useQuery({
    queryKey: platformDashboardKeys.summary(),
    queryFn: platformDashboardService.getDashboard,
    staleTime: FIVE_MINUTES_MS,
  });
}
