import { PAID_STATUS_VALUES, type PaidStatus } from "@/features/reports/constants/paid-status";
import type {
  SalesReportInvoiceStatus,
  SalesReportParams,
} from "@/features/reports/types/sales-report";

export const SALES_REPORT_STATUS_VALUES = [
  "draft",
  "issued",
  "partially_paid",
  "paid",
  "cancelled",
] as const satisfies readonly SalesReportInvoiceStatus[];

export { PAID_STATUS_VALUES as SALES_REPORT_PAID_STATUS_VALUES };

/**
 * Sales Report filter/page state. Unlike the Ledgers' `CustomerLedgerFilters`,
 * `customerId` is an optional narrowing filter, not a required resource key
 * - the report loads with all invoices by default (mirrors
 * `InvoiceFilters`' own posture). There is no `sort` field - the backend's
 * order is fixed, not client-configurable (TASKS.md Sprint 11 Session 3).
 */
export interface SalesReportFilters {
  search: string;
  customerId: string | null;
  fromDate: string | null;
  toDate: string | null;
  status: SalesReportInvoiceStatus | null;
  paidStatus: PaidStatus | null;
  page: number;
  pageSize: number;
}

export const DEFAULT_SALES_REPORT_FILTERS: SalesReportFilters = {
  search: "",
  customerId: null,
  fromDate: null,
  toDate: null,
  status: null,
  paidStatus: null,
  page: 1,
  pageSize: 20,
};

/** Maps the client's filter state onto the backend's SalesReportParams query shape. */
export function toSalesReportParams(filters: SalesReportFilters): SalesReportParams {
  return {
    customer_id: filters.customerId ?? undefined,
    from_date: filters.fromDate ?? undefined,
    to_date: filters.toDate ?? undefined,
    status: filters.status ?? undefined,
    paid_status: filters.paidStatus ?? undefined,
    q: filters.search.trim() || undefined,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
