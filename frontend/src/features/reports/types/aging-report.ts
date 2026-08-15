import type { EntityType } from "@/features/reports/constants/entity-type";
import type { RiskLevel } from "@/features/reports/constants/risk-level";

/**
 * Raw backend shape (snake_case), matching AgingReportResponse
 * (app/modules/reports/schemas.py) exactly. Mirrors outstanding-report.ts's
 * shapes, but bucketed by due_date instead of a single outstanding/overdue
 * split.
 */
export interface BackendAgingReportRow {
  entity_id: string;
  entity_name: string;
  entity_code: string;
  current_amount: string;
  days_1_30: string;
  days_31_60: string;
  days_61_90: string;
  days_90_plus: string;
  total: string;
  risk_level: RiskLevel;
}

export interface BackendAgingReportSummary {
  current_total: string;
  days_1_30_total: string;
  days_31_60_total: string;
  days_61_90_total: string;
  days_90_plus_total: string;
  grand_total: string;
}

export interface BackendPaginationMeta {
  total_records: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface BackendAgingReportResponse {
  entity_type: EntityType;
  summary: BackendAgingReportSummary;
  rows: BackendAgingReportRow[];
  pagination: BackendPaginationMeta;
}

/** The client-facing, camelCase shape reportsService.getAgingReport returns. */
export interface AgingReportRow {
  entityId: string;
  entityName: string;
  entityCode: string;
  currentAmount: string;
  days1To30: string;
  days31To60: string;
  days61To90: string;
  days90Plus: string;
  total: string;
  riskLevel: RiskLevel;
}

export interface AgingReportSummary {
  currentTotal: string;
  days1To30Total: string;
  days31To60Total: string;
  days61To90Total: string;
  days90PlusTotal: string;
  grandTotal: string;
}

export interface PaginationMeta {
  totalRecords: number;
  totalPages: number;
  currentPage: number;
  pageSize: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface AgingReportData {
  entityType: EntityType;
  summary: AgingReportSummary;
  rows: AgingReportRow[];
  pagination: PaginationMeta;
}

export function mapBackendAgingReport(response: BackendAgingReportResponse): AgingReportData {
  return {
    entityType: response.entity_type,
    summary: {
      currentTotal: response.summary.current_total,
      days1To30Total: response.summary.days_1_30_total,
      days31To60Total: response.summary.days_31_60_total,
      days61To90Total: response.summary.days_61_90_total,
      days90PlusTotal: response.summary.days_90_plus_total,
      grandTotal: response.summary.grand_total,
    },
    rows: response.rows.map((row) => ({
      entityId: row.entity_id,
      entityName: row.entity_name,
      entityCode: row.entity_code,
      currentAmount: row.current_amount,
      days1To30: row.days_1_30,
      days31To60: row.days_31_60,
      days61To90: row.days_61_90,
      days90Plus: row.days_90_plus,
      total: row.total,
      riskLevel: row.risk_level,
    })),
    pagination: {
      totalRecords: response.pagination.total_records,
      totalPages: response.pagination.total_pages,
      currentPage: response.pagination.current_page,
      pageSize: response.pagination.page_size,
      hasNext: response.pagination.has_next,
      hasPrevious: response.pagination.has_previous,
    },
  };
}

/**
 * Query params for GET /reports/aging (app/modules/reports/schemas.py's
 * AgingReportParams) - a smaller filter set than Outstanding's: no
 * `overdue_only`, no date range (aging is always "as of today").
 */
export interface AgingReportParams {
  entity_type: EntityType;
  outstanding_only?: boolean;
  risk_level?: RiskLevel;
  q?: string;
  page: number;
  page_size: number;
}
