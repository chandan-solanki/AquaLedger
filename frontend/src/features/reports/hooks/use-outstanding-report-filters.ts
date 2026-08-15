"use client";

import { parseAsBoolean, parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import {
  DEFAULT_OUTSTANDING_REPORT_FILTERS,
  OUTSTANDING_REPORT_ENTITY_TYPE_VALUES,
  OUTSTANDING_REPORT_RISK_LEVEL_VALUES,
} from "@/features/reports/schemas/outstanding-report-filters";

const outstandingReportFilterParsers = {
  entityType: parseAsStringEnum([...OUTSTANDING_REPORT_ENTITY_TYPE_VALUES]).withDefault(
    DEFAULT_OUTSTANDING_REPORT_FILTERS.entityType
  ),
  search: parseAsString.withDefault(DEFAULT_OUTSTANDING_REPORT_FILTERS.search),
  outstandingOnly: parseAsBoolean.withDefault(DEFAULT_OUTSTANDING_REPORT_FILTERS.outstandingOnly),
  overdueOnly: parseAsBoolean.withDefault(DEFAULT_OUTSTANDING_REPORT_FILTERS.overdueOnly),
  riskLevel: parseAsStringEnum([...OUTSTANDING_REPORT_RISK_LEVEL_VALUES]),
  fromDate: parseAsString,
  toDate: parseAsString,
  page: parseAsInteger.withDefault(DEFAULT_OUTSTANDING_REPORT_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_OUTSTANDING_REPORT_FILTERS.pageSize),
};

/**
 * Outstanding Report filter/tab/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10) - the active tab is part of the URL too, so a
 * shared link or a refresh lands back on the same tab.
 */
export function useOutstandingReportFilters() {
  return useQueryStates(outstandingReportFilterParsers, { history: "push" });
}
