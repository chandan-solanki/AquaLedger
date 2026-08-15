"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import {
  DEFAULT_SALES_REPORT_FILTERS,
  SALES_REPORT_PAID_STATUS_VALUES,
  SALES_REPORT_STATUS_VALUES,
} from "@/features/reports/schemas/sales-report-filters";

const salesReportFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_SALES_REPORT_FILTERS.search),
  customerId: parseAsString,
  fromDate: parseAsString,
  toDate: parseAsString,
  status: parseAsStringEnum([...SALES_REPORT_STATUS_VALUES]),
  paidStatus: parseAsStringEnum([...SALES_REPORT_PAID_STATUS_VALUES]),
  page: parseAsInteger.withDefault(DEFAULT_SALES_REPORT_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_SALES_REPORT_FILTERS.pageSize),
};

/**
 * Sales Report filter/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10), mirroring `useInvoiceFilters`.
 */
export function useSalesReportFilters() {
  return useQueryStates(salesReportFilterParsers, { history: "push" });
}
