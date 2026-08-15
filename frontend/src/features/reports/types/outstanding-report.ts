import type { EntityType } from "@/features/reports/constants/entity-type";
import type { RiskLevel } from "@/features/reports/constants/risk-level";

/**
 * Raw backend shape (snake_case), matching OutstandingReportResponse
 * (app/modules/reports/schemas.py) exactly. Every money field is a string -
 * the backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1). `entity_id`/`entity_name`/`entity_code` are
 * generic rather than `customer_id`/`supplier_id` - one response shape
 * serves both the Customer Outstanding and Supplier Outstanding tabs.
 */
export interface BackendOutstandingReportRow {
  entity_id: string;
  entity_name: string;
  entity_code: string;
  outstanding_amount: string;
  overdue_amount: string;
  current_amount: string;
  last_transaction_date: string | null;
  last_payment_date: string | null;
  pending_count: number;
  risk_level: RiskLevel;
}

export interface BackendOutstandingReportSummary {
  accounts_receivable: string;
  accounts_payable: string;
  net_position: string;
  overdue_receivable: string;
  overdue_payable: string;
  customers_with_outstanding: number;
  suppliers_with_outstanding: number;
}

export interface BackendPaginationMeta {
  total_records: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface BackendOutstandingReportResponse {
  entity_type: EntityType;
  summary: BackendOutstandingReportSummary;
  rows: BackendOutstandingReportRow[];
  pagination: BackendPaginationMeta;
}

/** The client-facing, camelCase shape reportsService.getOutstandingReport returns. */
export interface OutstandingReportRow {
  entityId: string;
  entityName: string;
  entityCode: string;
  outstandingAmount: string;
  overdueAmount: string;
  currentAmount: string;
  lastTransactionDate: string | null;
  lastPaymentDate: string | null;
  pendingCount: number;
  riskLevel: RiskLevel;
}

export interface OutstandingReportSummary {
  accountsReceivable: string;
  accountsPayable: string;
  netPosition: string;
  overdueReceivable: string;
  overduePayable: string;
  customersWithOutstanding: number;
  suppliersWithOutstanding: number;
}

export interface PaginationMeta {
  totalRecords: number;
  totalPages: number;
  currentPage: number;
  pageSize: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface OutstandingReportData {
  entityType: EntityType;
  summary: OutstandingReportSummary;
  rows: OutstandingReportRow[];
  pagination: PaginationMeta;
}

export function mapBackendOutstandingReport(
  response: BackendOutstandingReportResponse
): OutstandingReportData {
  return {
    entityType: response.entity_type,
    summary: {
      accountsReceivable: response.summary.accounts_receivable,
      accountsPayable: response.summary.accounts_payable,
      netPosition: response.summary.net_position,
      overdueReceivable: response.summary.overdue_receivable,
      overduePayable: response.summary.overdue_payable,
      customersWithOutstanding: response.summary.customers_with_outstanding,
      suppliersWithOutstanding: response.summary.suppliers_with_outstanding,
    },
    rows: response.rows.map((row) => ({
      entityId: row.entity_id,
      entityName: row.entity_name,
      entityCode: row.entity_code,
      outstandingAmount: row.outstanding_amount,
      overdueAmount: row.overdue_amount,
      currentAmount: row.current_amount,
      lastTransactionDate: row.last_transaction_date,
      lastPaymentDate: row.last_payment_date,
      pendingCount: row.pending_count,
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
 * Query params for GET /reports/outstanding (app/modules/reports/schemas.py's
 * OutstandingReportParams) - snake_case to match the wire format exactly.
 * There is no `sort` field - the backend's order is fixed ("Outstanding
 * DESC, Then Name ASC"), not client-configurable.
 */
export interface OutstandingReportParams {
  entity_type: EntityType;
  outstanding_only?: boolean;
  overdue_only?: boolean;
  risk_level?: RiskLevel;
  from_date?: string;
  to_date?: string;
  q?: string;
  page: number;
  page_size: number;
}
