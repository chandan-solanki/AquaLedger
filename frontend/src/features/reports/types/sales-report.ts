import type { PaidStatus } from "@/features/reports/constants/paid-status";

/** Mirrors the backend's InvoiceStatus enum (app/modules/invoices/constants.py). */
export type SalesReportInvoiceStatus = "draft" | "issued" | "partially_paid" | "paid" | "cancelled";

/**
 * Raw backend shape (snake_case), matching SalesReportResponse
 * (app/modules/reports/schemas.py) exactly. Every money field is a string -
 * the backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1).
 */
export interface BackendSalesReportRow {
  invoice_id: string;
  invoice_number: string;
  invoice_date: string;
  due_date: string | null;
  customer_name: string;
  invoice_amount: string;
  paid_amount: string;
  outstanding_amount: string;
  status: SalesReportInvoiceStatus;
}

export interface BackendSalesReportSummary {
  total_sales: string;
  total_paid: string;
  outstanding: string;
  invoice_count: number;
  average_invoice: string;
  largest_invoice: string;
}

export interface BackendPaginationMeta {
  total_records: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface BackendSalesReportResponse {
  summary: BackendSalesReportSummary;
  rows: BackendSalesReportRow[];
  pagination: BackendPaginationMeta;
}

/** The client-facing, camelCase shape reportsService.getSalesReport returns. */
export interface SalesReportRow {
  invoiceId: string;
  invoiceNumber: string;
  invoiceDate: string;
  dueDate: string | null;
  customerName: string;
  invoiceAmount: string;
  paidAmount: string;
  outstandingAmount: string;
  status: SalesReportInvoiceStatus;
}

export interface SalesReportSummary {
  totalSales: string;
  totalPaid: string;
  outstanding: string;
  invoiceCount: number;
  averageInvoice: string;
  largestInvoice: string;
}

export interface PaginationMeta {
  totalRecords: number;
  totalPages: number;
  currentPage: number;
  pageSize: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface SalesReportData {
  summary: SalesReportSummary;
  rows: SalesReportRow[];
  pagination: PaginationMeta;
}

export function mapBackendSalesReport(response: BackendSalesReportResponse): SalesReportData {
  return {
    summary: {
      totalSales: response.summary.total_sales,
      totalPaid: response.summary.total_paid,
      outstanding: response.summary.outstanding,
      invoiceCount: response.summary.invoice_count,
      averageInvoice: response.summary.average_invoice,
      largestInvoice: response.summary.largest_invoice,
    },
    rows: response.rows.map((row) => ({
      invoiceId: row.invoice_id,
      invoiceNumber: row.invoice_number,
      invoiceDate: row.invoice_date,
      dueDate: row.due_date,
      customerName: row.customer_name,
      invoiceAmount: row.invoice_amount,
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
 * Query params for GET /reports/sales (app/modules/reports/schemas.py's
 * SalesReportParams) - snake_case to match the wire format exactly. There
 * is deliberately no `sort` field - the backend's order is fixed
 * (`invoice_date DESC, invoice_number DESC`), not client-configurable.
 */
export interface SalesReportParams {
  customer_id?: string;
  from_date?: string;
  to_date?: string;
  status?: SalesReportInvoiceStatus;
  paid_status?: PaidStatus;
  q?: string;
  page: number;
  page_size: number;
}
