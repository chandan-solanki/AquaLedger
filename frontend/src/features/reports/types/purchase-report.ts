import type { PaidStatus } from "@/features/reports/constants/paid-status";

/** Mirrors the backend's PurchaseStatus enum (app/modules/purchase/constants.py). */
export type PurchaseReportBillStatus = "draft" | "posted" | "partially_paid" | "paid" | "cancelled";

/**
 * Raw backend shape (snake_case), matching PurchaseReportResponse
 * (app/modules/reports/schemas.py) exactly. Mirrors sales-report.ts's
 * shapes exactly, on the buy side.
 */
export interface BackendPurchaseReportRow {
  bill_id: string;
  bill_number: string;
  bill_date: string;
  due_date: string | null;
  supplier_name: string;
  bill_amount: string;
  paid_amount: string;
  outstanding_amount: string;
  status: PurchaseReportBillStatus;
}

export interface BackendPurchaseReportSummary {
  total_purchases: string;
  total_paid: string;
  outstanding: string;
  bill_count: number;
  average_bill: string;
  largest_bill: string;
}

export interface BackendPaginationMeta {
  total_records: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface BackendPurchaseReportResponse {
  summary: BackendPurchaseReportSummary;
  rows: BackendPurchaseReportRow[];
  pagination: BackendPaginationMeta;
}

/** The client-facing, camelCase shape reportsService.getPurchaseReport returns. */
export interface PurchaseReportRow {
  billId: string;
  billNumber: string;
  billDate: string;
  dueDate: string | null;
  supplierName: string;
  billAmount: string;
  paidAmount: string;
  outstandingAmount: string;
  status: PurchaseReportBillStatus;
}

export interface PurchaseReportSummary {
  totalPurchases: string;
  totalPaid: string;
  outstanding: string;
  billCount: number;
  averageBill: string;
  largestBill: string;
}

export interface PaginationMeta {
  totalRecords: number;
  totalPages: number;
  currentPage: number;
  pageSize: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface PurchaseReportData {
  summary: PurchaseReportSummary;
  rows: PurchaseReportRow[];
  pagination: PaginationMeta;
}

export function mapBackendPurchaseReport(
  response: BackendPurchaseReportResponse
): PurchaseReportData {
  return {
    summary: {
      totalPurchases: response.summary.total_purchases,
      totalPaid: response.summary.total_paid,
      outstanding: response.summary.outstanding,
      billCount: response.summary.bill_count,
      averageBill: response.summary.average_bill,
      largestBill: response.summary.largest_bill,
    },
    rows: response.rows.map((row) => ({
      billId: row.bill_id,
      billNumber: row.bill_number,
      billDate: row.bill_date,
      dueDate: row.due_date,
      supplierName: row.supplier_name,
      billAmount: row.bill_amount,
      paidAmount: row.paid_amount,
      outstandingAmount: row.outstanding_amount,
      status: row.status,
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
 * Query params for GET /reports/purchases (app/modules/reports/schemas.py's
 * PurchaseReportParams) - mirrors sales-report.ts's SalesReportParams
 * exactly, on the buy side. No `sort` field, for the same reason.
 */
export interface PurchaseReportParams {
  supplier_id?: string;
  from_date?: string;
  to_date?: string;
  status?: PurchaseReportBillStatus;
  paid_status?: PaidStatus;
  q?: string;
  page: number;
  page_size: number;
}
