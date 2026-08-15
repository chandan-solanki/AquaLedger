/** Mirrors the backend's SupplierTransactionType enum (app/modules/reports/constants.py). */
export type SupplierTransactionType = "purchase_bill" | "supplier_payment";

/**
 * Raw backend shape (snake_case), matching SupplierLedgerResponse
 * (app/modules/reports/schemas.py) exactly. Every money field is a string -
 * the backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1), and the client keeps that representation rather
 * than parsing into a JS number. Mirrors `customer-ledger.ts` exactly, on
 * the buy side.
 */
export interface BackendSupplierLedgerSupplier {
  id: string;
  name: string;
  code: string;
}

export interface BackendSupplierLedgerSummary {
  opening_balance: string;
  total_debit: string;
  total_credit: string;
  closing_balance: string;
  purchase_bill_count: number;
  supplier_payment_count: number;
}

export interface BackendSupplierLedgerEntry {
  transaction_date: string;
  reference_number: string;
  transaction_type: SupplierTransactionType;
  description: string;
  debit: string;
  credit: string;
  running_balance: string;
}

export interface BackendPaginationMeta {
  total_records: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface BackendSupplierLedgerResponse {
  supplier: BackendSupplierLedgerSupplier;
  summary: BackendSupplierLedgerSummary;
  entries: BackendSupplierLedgerEntry[];
  pagination: BackendPaginationMeta;
}

/** The client-facing, camelCase shape reportsService.getSupplierLedger returns. */
export interface SupplierLedgerSupplier {
  id: string;
  name: string;
  code: string;
}

export interface SupplierLedgerSummary {
  openingBalance: string;
  totalDebit: string;
  totalCredit: string;
  closingBalance: string;
  purchaseBillCount: number;
  supplierPaymentCount: number;
}

export interface SupplierLedgerEntry {
  transactionDate: string;
  referenceNumber: string;
  transactionType: SupplierTransactionType;
  description: string;
  debit: string;
  credit: string;
  runningBalance: string;
}

export interface PaginationMeta {
  totalRecords: number;
  totalPages: number;
  currentPage: number;
  pageSize: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface SupplierLedgerData {
  supplier: SupplierLedgerSupplier;
  summary: SupplierLedgerSummary;
  entries: SupplierLedgerEntry[];
  pagination: PaginationMeta;
}

export function mapBackendSupplierLedger(
  response: BackendSupplierLedgerResponse
): SupplierLedgerData {
  return {
    supplier: {
      id: response.supplier.id,
      name: response.supplier.name,
      code: response.supplier.code,
    },
    summary: {
      openingBalance: response.summary.opening_balance,
      totalDebit: response.summary.total_debit,
      totalCredit: response.summary.total_credit,
      closingBalance: response.summary.closing_balance,
      purchaseBillCount: response.summary.purchase_bill_count,
      supplierPaymentCount: response.summary.supplier_payment_count,
    },
    entries: response.entries.map((entry) => ({
      transactionDate: entry.transaction_date,
      referenceNumber: entry.reference_number,
      transactionType: entry.transaction_type,
      description: entry.description,
      debit: entry.debit,
      credit: entry.credit,
      runningBalance: entry.running_balance,
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
 * Query params for GET /reports/supplier-ledger (app/modules/reports/schemas.py's
 * SupplierLedgerParams) - snake_case to match the wire format exactly, since
 * `reports-service.ts` forwards these straight through as a query string.
 */
export interface SupplierLedgerParams {
  supplier_id: string;
  from_date?: string;
  to_date?: string;
  transaction_type?: SupplierTransactionType;
  page: number;
  page_size: number;
}
