import { ENTITY_TYPE_VALUES, type EntityType } from "@/features/reports/constants/entity-type";
import { RISK_LEVEL_VALUES, type RiskLevel } from "@/features/reports/constants/risk-level";
import type { OutstandingReportParams } from "@/features/reports/types/outstanding-report";

export { ENTITY_TYPE_VALUES as OUTSTANDING_REPORT_ENTITY_TYPE_VALUES };
export { RISK_LEVEL_VALUES as OUTSTANDING_REPORT_RISK_LEVEL_VALUES };

/**
 * Outstanding Report filter/tab/page state. `entityType` drives the
 * "Customer Outstanding"/"Supplier Outstanding" tabs (TASKS.md Sprint 11
 * Session 3 Phase B) - switching tabs is a filter change like any other,
 * not a separate page/route.
 */
export interface OutstandingReportFilters {
  entityType: EntityType;
  search: string;
  outstandingOnly: boolean;
  overdueOnly: boolean;
  riskLevel: RiskLevel | null;
  fromDate: string | null;
  toDate: string | null;
  page: number;
  pageSize: number;
}

export const DEFAULT_OUTSTANDING_REPORT_FILTERS: OutstandingReportFilters = {
  entityType: "customer",
  search: "",
  outstandingOnly: false,
  overdueOnly: false,
  riskLevel: null,
  fromDate: null,
  toDate: null,
  page: 1,
  pageSize: 20,
};

/** Maps the client's filter state onto the backend's OutstandingReportParams query shape. */
export function toOutstandingReportParams(
  filters: OutstandingReportFilters
): OutstandingReportParams {
  return {
    entity_type: filters.entityType,
    outstanding_only: filters.outstandingOnly || undefined,
    overdue_only: filters.overdueOnly || undefined,
    risk_level: filters.riskLevel ?? undefined,
    from_date: filters.fromDate ?? undefined,
    to_date: filters.toDate ?? undefined,
    q: filters.search.trim() || undefined,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
