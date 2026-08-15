"use client";

import { parseAsBoolean, parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import {
  AGING_REPORT_ENTITY_TYPE_VALUES,
  AGING_REPORT_RISK_LEVEL_VALUES,
  DEFAULT_AGING_REPORT_FILTERS,
} from "@/features/reports/schemas/aging-report-filters";

const agingReportFilterParsers = {
  entityType: parseAsStringEnum([...AGING_REPORT_ENTITY_TYPE_VALUES]).withDefault(
    DEFAULT_AGING_REPORT_FILTERS.entityType
  ),
  search: parseAsString.withDefault(DEFAULT_AGING_REPORT_FILTERS.search),
  outstandingOnly: parseAsBoolean.withDefault(DEFAULT_AGING_REPORT_FILTERS.outstandingOnly),
  riskLevel: parseAsStringEnum([...AGING_REPORT_RISK_LEVEL_VALUES]),
  page: parseAsInteger.withDefault(DEFAULT_AGING_REPORT_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_AGING_REPORT_FILTERS.pageSize),
};

/**
 * Aging Report filter/tab/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10), mirroring `useOutstandingReportFilters`.
 */
export function useAgingReportFilters() {
  return useQueryStates(agingReportFilterParsers, { history: "push" });
}
