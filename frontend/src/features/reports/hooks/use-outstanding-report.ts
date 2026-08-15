"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { reportKeys } from "@/features/reports/constants/query-keys";
import { toOutstandingReportParams } from "@/features/reports/schemas/outstanding-report-filters";
import type { OutstandingReportFilters } from "@/features/reports/schemas/outstanding-report-filters";
import { reportsService } from "@/features/reports/services/reports-service";

/**
 * The Outstanding Report's server-side, paginated fetch - always enabled
 * (no required entity like the Ledgers; `entityType` just selects which
 * tab's rows come back). `keepPreviousData` keeps the current rows on
 * screen while a filter/tab/page change is in flight.
 */
export function useOutstandingReport(filters: OutstandingReportFilters) {
  const params = toOutstandingReportParams(filters);

  return useQuery({
    queryKey: reportKeys.outstandingReportResult(params),
    queryFn: () => reportsService.getOutstandingReport(params),
    placeholderData: keepPreviousData,
  });
}
