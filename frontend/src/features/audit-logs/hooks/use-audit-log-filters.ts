"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import {
  AUDIT_LOG_SORT_DIRECTIONS,
  AUDIT_LOG_SORT_FIELDS,
  DEFAULT_AUDIT_LOG_FILTERS,
} from "@/features/audit-logs/schemas/audit-log-filters";

const auditLogFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_AUDIT_LOG_FILTERS.search),
  action: parseAsString,
  entityType: parseAsString,
  userId: parseAsString,
  fromDate: parseAsString,
  toDate: parseAsString,
  page: parseAsInteger.withDefault(DEFAULT_AUDIT_LOG_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_AUDIT_LOG_FILTERS.pageSize),
  sort: parseAsStringEnum([...AUDIT_LOG_SORT_FIELDS]).withDefault(DEFAULT_AUDIT_LOG_FILTERS.sort),
  direction: parseAsStringEnum([...AUDIT_LOG_SORT_DIRECTIONS]).withDefault(
    DEFAULT_AUDIT_LOG_FILTERS.direction
  ),
};

/**
 * Audit Logs filter/sort/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10), mirroring `useDocumentFilters` exactly.
 */
export function useAuditLogFilters() {
  return useQueryStates(auditLogFilterParsers, { history: "push" });
}
