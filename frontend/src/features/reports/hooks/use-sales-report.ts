"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { reportKeys } from "@/features/reports/constants/query-keys";
import { toSalesReportParams } from "@/features/reports/schemas/sales-report-filters";
import type { SalesReportFilters } from "@/features/reports/schemas/sales-report-filters";
import { reportsService } from "@/features/reports/services/reports-service";

/**
 * The Sales Report's server-side, paginated fetch. Unlike the Ledgers'
 * hooks, this is always enabled - `customer_id` is an optional filter, not
 * a required backend param, so the report loads with every issued invoice
 * by default. `keepPreviousData` keeps the current rows on screen while a
 * filter/page change is in flight.
 */
export function useSalesReport(filters: SalesReportFilters) {
  const params = toSalesReportParams(filters);

  return useQuery({
    queryKey: reportKeys.salesReportResult(params),
    queryFn: () => reportsService.getSalesReport(params),
    placeholderData: keepPreviousData,
  });
}
