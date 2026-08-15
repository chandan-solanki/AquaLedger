import { PAID_STATUS_VALUES, type PaidStatus } from "@/features/reports/constants/paid-status";
import type {
  PurchaseReportBillStatus,
  PurchaseReportParams,
} from "@/features/reports/types/purchase-report";

export const PURCHASE_REPORT_STATUS_VALUES = [
  "draft",
  "posted",
  "partially_paid",
  "paid",
  "cancelled",
] as const satisfies readonly PurchaseReportBillStatus[];

export { PAID_STATUS_VALUES as PURCHASE_REPORT_PAID_STATUS_VALUES };

/** Mirrors SalesReportFilters exactly, on the buy side. */
export interface PurchaseReportFilters {
  search: string;
  supplierId: string | null;
  fromDate: string | null;
  toDate: string | null;
  status: PurchaseReportBillStatus | null;
  paidStatus: PaidStatus | null;
  page: number;
  pageSize: number;
}

export const DEFAULT_PURCHASE_REPORT_FILTERS: PurchaseReportFilters = {
  search: "",
  supplierId: null,
  fromDate: null,
  toDate: null,
  status: null,
  paidStatus: null,
  page: 1,
  pageSize: 20,
};

/** Maps the client's filter state onto the backend's PurchaseReportParams query shape. */
export function toPurchaseReportParams(filters: PurchaseReportFilters): PurchaseReportParams {
  return {
    supplier_id: filters.supplierId ?? undefined,
    from_date: filters.fromDate ?? undefined,
    to_date: filters.toDate ?? undefined,
    status: filters.status ?? undefined,
    paid_status: filters.paidStatus ?? undefined,
    q: filters.search.trim() || undefined,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
