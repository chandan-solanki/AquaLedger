"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { reportKeys } from "@/features/reports/constants/query-keys";
import { toAgingReportParams } from "@/features/reports/schemas/aging-report-filters";
import type { AgingReportFilters } from "@/features/reports/schemas/aging-report-filters";
import { reportsService } from "@/features/reports/services/reports-service";

/** Mirrors `useOutstandingReport` exactly. */
export function useAgingReport(filters: AgingReportFilters) {
  const params = toAgingReportParams(filters);

  return useQuery({
    queryKey: reportKeys.agingReportResult(params),
    queryFn: () => reportsService.getAgingReport(params),
    placeholderData: keepPreviousData,
  });
}
