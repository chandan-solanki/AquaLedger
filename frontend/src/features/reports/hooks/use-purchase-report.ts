"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { reportKeys } from "@/features/reports/constants/query-keys";
import { toPurchaseReportParams } from "@/features/reports/schemas/purchase-report-filters";
import type { PurchaseReportFilters } from "@/features/reports/schemas/purchase-report-filters";
import { reportsService } from "@/features/reports/services/reports-service";

/**
 * The Purchase Report's server-side, paginated fetch. Mirrors
 * `useSalesReport` exactly, on the buy side - always enabled, since
 * `supplier_id` is an optional filter, not a required backend param.
 */
export function usePurchaseReport(filters: PurchaseReportFilters) {
  const params = toPurchaseReportParams(filters);

  return useQuery({
    queryKey: reportKeys.purchaseReportResult(params),
    queryFn: () => reportsService.getPurchaseReport(params),
    placeholderData: keepPreviousData,
  });
}
