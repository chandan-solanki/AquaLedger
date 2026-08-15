"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { reportKeys } from "@/features/reports/constants/query-keys";
import type { FishSalesHistoryParams } from "@/features/reports/types/fish-sales-history";
import { reportsService } from "@/features/reports/services/reports-service";

/**
 * The Fish Detail page's own Sales History section - one row per
 * individual sale of the given fish, paginated server-side. `fish_id` is
 * required (GET /reports/fish-sales-history's own posture) - this hook is
 * only ever called once a fish id is known.
 */
export function useFishSalesHistory(fishId: string | undefined, page: number, pageSize: number) {
  const params: FishSalesHistoryParams = { fish_id: fishId ?? "", page, page_size: pageSize };

  return useQuery({
    queryKey: reportKeys.fishSalesHistoryResult(params),
    queryFn: () => reportsService.getFishSalesHistory(params),
    enabled: Boolean(fishId),
    placeholderData: keepPreviousData,
  });
}
