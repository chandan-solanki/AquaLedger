import { ENTITY_TYPE_VALUES, type EntityType } from "@/features/reports/constants/entity-type";
import { RISK_LEVEL_VALUES, type RiskLevel } from "@/features/reports/constants/risk-level";
import type { AgingReportParams } from "@/features/reports/types/aging-report";

export { ENTITY_TYPE_VALUES as AGING_REPORT_ENTITY_TYPE_VALUES };
export { RISK_LEVEL_VALUES as AGING_REPORT_RISK_LEVEL_VALUES };

/** Mirrors OutstandingReportFilters, but with a smaller filter set - no `overdueOnly`, no date range. */
export interface AgingReportFilters {
  entityType: EntityType;
  search: string;
  outstandingOnly: boolean;
  riskLevel: RiskLevel | null;
  page: number;
  pageSize: number;
}

export const DEFAULT_AGING_REPORT_FILTERS: AgingReportFilters = {
  entityType: "customer",
  search: "",
  outstandingOnly: false,
  riskLevel: null,
  page: 1,
  pageSize: 20,
};

/** Maps the client's filter state onto the backend's AgingReportParams query shape. */
export function toAgingReportParams(filters: AgingReportFilters): AgingReportParams {
  return {
    entity_type: filters.entityType,
    outstanding_only: filters.outstandingOnly || undefined,
    risk_level: filters.riskLevel ?? undefined,
    q: filters.search.trim() || undefined,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
