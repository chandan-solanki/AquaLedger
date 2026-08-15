/** Mirrors the backend's TransactionType enum (app/modules/reports/constants.py). */
export type TransactionType = "invoice" | "payment";

/**
 * Raw backend shape (snake_case), matching CustomerLedgerResponse
 * (app/modules/reports/schemas.py) exactly. Every money field is a string -
 * the backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1), and the client keeps that representation rather
 * than parsing into a JS number.
 */
export interface BackendCustomerLedgerCustomer {
  id: string;
  name: string;
  code: string;
}

export interface BackendCustomerLedgerSummary {
  opening_balance: string;
  total_debit: string;
  total_credit: string;
  closing_balance: string;
  invoice_count: number;
  payment_count: number;
}

export interface BackendCustomerLedgerEntry {
  transaction_date: string;
  reference_number: string;
  transaction_type: TransactionType;
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

export interface BackendCustomerLedgerResponse {
  customer: BackendCustomerLedgerCustomer;
  summary: BackendCustomerLedgerSummary;
  entries: BackendCustomerLedgerEntry[];
  pagination: BackendPaginationMeta;
}

/** The client-facing, camelCase shape reportsService.getCustomerLedger returns. */
export interface CustomerLedgerCustomer {
  id: string;
  name: string;
  code: string;
}

export interface CustomerLedgerSummary {
  openingBalance: string;
  totalDebit: string;
  totalCredit: string;
  closingBalance: string;
  invoiceCount: number;
  paymentCount: number;
}

export interface CustomerLedgerEntry {
  transactionDate: string;
  referenceNumber: string;
  transactionType: TransactionType;
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

export interface CustomerLedgerData {
  customer: CustomerLedgerCustomer;
  summary: CustomerLedgerSummary;
  entries: CustomerLedgerEntry[];
  pagination: PaginationMeta;
}

export function mapBackendCustomerLedger(
  response: BackendCustomerLedgerResponse
): CustomerLedgerData {
  return {
    customer: {
      id: response.customer.id,
      name: response.customer.name,
      code: response.customer.code,
    },
    summary: {
      openingBalance: response.summary.opening_balance,
      totalDebit: response.summary.total_debit,
      totalCredit: response.summary.total_credit,
      closingBalance: response.summary.closing_balance,
      invoiceCount: response.summary.invoice_count,
      paymentCount: response.summary.payment_count,
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
 * Query params for GET /reports/customer-ledger (app/modules/reports/schemas.py's
 * CustomerLedgerParams) - snake_case to match the wire format exactly, since
 * `reports-service.ts` forwards these straight through as a query string.
 */
export interface CustomerLedgerParams {
  customer_id: string;
  from_date?: string;
  to_date?: string;
  transaction_type?: TransactionType;
  page: number;
  page_size: number;
}
