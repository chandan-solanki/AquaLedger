import type {
  CustomerLedgerParams,
  TransactionType,
} from "@/features/reports/types/customer-ledger";

export const TRANSACTION_TYPE_VALUES = ["invoice", "payment"] as const;

/**
 * Customer Ledger filter/sort/page state. `customerId` is `null` until the
 * user picks one (the backend's `customer_id` is a required param, so
 * `useCustomerLedger` stays disabled until this is set - see that hook).
 * `fromDate`/`toDate` are plain ISO date strings ("YYYY-MM-DD") rather than
 * `Date` objects so this shape round-trips cleanly through the URL (nuqs),
 * mirroring `InvoiceFilters`.
 */
export interface CustomerLedgerFilters {
  customerId: string | null;
  fromDate: string | null;
  toDate: string | null;
  transactionType: TransactionType | null;
  page: number;
  pageSize: number;
}

export const DEFAULT_CUSTOMER_LEDGER_FILTERS: CustomerLedgerFilters = {
  customerId: null,
  fromDate: null,
  toDate: null,
  transactionType: null,
  page: 1,
  pageSize: 20,
};

/** Maps the client's filter state onto the backend's CustomerLedgerParams query shape. */
export function toCustomerLedgerParams(
  filters: CustomerLedgerFilters
): CustomerLedgerParams | null {
  if (!filters.customerId) return null;

  return {
    customer_id: filters.customerId,
    from_date: filters.fromDate ?? undefined,
    to_date: filters.toDate ?? undefined,
    transaction_type: filters.transactionType ?? undefined,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
