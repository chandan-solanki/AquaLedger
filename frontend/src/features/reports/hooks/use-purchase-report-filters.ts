"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import {
  DEFAULT_PURCHASE_REPORT_FILTERS,
  PURCHASE_REPORT_PAID_STATUS_VALUES,
  PURCHASE_REPORT_STATUS_VALUES,
} from "@/features/reports/schemas/purchase-report-filters";

const purchaseReportFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_PURCHASE_REPORT_FILTERS.search),
  supplierId: parseAsString,
  fromDate: parseAsString,
  toDate: parseAsString,
  status: parseAsStringEnum([...PURCHASE_REPORT_STATUS_VALUES]),
  paidStatus: parseAsStringEnum([...PURCHASE_REPORT_PAID_STATUS_VALUES]),
  page: parseAsInteger.withDefault(DEFAULT_PURCHASE_REPORT_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_PURCHASE_REPORT_FILTERS.pageSize),
};

/**
 * Purchase Report filter/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10), mirroring `useSalesReportFilters`.
 */
export function usePurchaseReportFilters() {
  return useQueryStates(purchaseReportFilterParsers, { history: "push" });
}
