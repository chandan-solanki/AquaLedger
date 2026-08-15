import type {
  SupplierLedgerParams,
  SupplierTransactionType,
} from "@/features/reports/types/supplier-ledger";

export const SUPPLIER_TRANSACTION_TYPE_VALUES = ["purchase_bill", "supplier_payment"] as const;

/**
 * Supplier Ledger filter/sort/page state. `supplierId` is `null` until the
 * user picks one (the backend's `supplier_id` is a required param, so
 * `useSupplierLedger` stays disabled until this is set - see that hook).
 * Mirrors `CustomerLedgerFilters` exactly, on the buy side.
 */
export interface SupplierLedgerFilters {
  supplierId: string | null;
  fromDate: string | null;
  toDate: string | null;
  transactionType: SupplierTransactionType | null;
  page: number;
  pageSize: number;
}

export const DEFAULT_SUPPLIER_LEDGER_FILTERS: SupplierLedgerFilters = {
  supplierId: null,
  fromDate: null,
  toDate: null,
  transactionType: null,
  page: 1,
  pageSize: 20,
};

/** Maps the client's filter state onto the backend's SupplierLedgerParams query shape. */
export function toSupplierLedgerParams(
  filters: SupplierLedgerFilters
): SupplierLedgerParams | null {
  if (!filters.supplierId) return null;

  return {
    supplier_id: filters.supplierId,
    from_date: filters.fromDate ?? undefined,
    to_date: filters.toDate ?? undefined,
    transaction_type: filters.transactionType ?? undefined,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
