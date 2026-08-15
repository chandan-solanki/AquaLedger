/**
 * Raw backend shape (snake_case), matching FishSalesHistoryResponse
 * (app/modules/reports/schemas.py) exactly. Every money/quantity field is a
 * string - the backend serializes `Decimal` as a JSON string, never a
 * float (ARCHITECTURE.md §5.1).
 */
export interface BackendFishSalesHistoryRow {
  invoice_id: string;
  invoice_number: string;
  invoice_date: string;
  customer_name: string;
  boat_name: string | null;
  trip_number: string | null;
  quantity: string;
  unit_price: string;
  revenue: string;
}

export interface BackendPaginationMeta {
  total_records: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface BackendFishSalesHistoryResponse {
  rows: BackendFishSalesHistoryRow[];
  pagination: BackendPaginationMeta;
}

/** The client-facing, camelCase shape reportsService.getFishSalesHistory returns. */
export interface FishSalesHistoryRow {
  invoiceId: string;
  invoiceNumber: string;
  invoiceDate: string;
  customerName: string;
  boatName: string | null;
  tripNumber: string | null;
  quantity: string;
  unitPrice: string;
  revenue: string;
}

export interface PaginationMeta {
  totalRecords: number;
  totalPages: number;
  currentPage: number;
  pageSize: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface FishSalesHistoryData {
  rows: FishSalesHistoryRow[];
  pagination: PaginationMeta;
}

export function mapBackendFishSalesHistory(
  response: BackendFishSalesHistoryResponse
): FishSalesHistoryData {
  return {
    rows: response.rows.map((row) => ({
      invoiceId: row.invoice_id,
      invoiceNumber: row.invoice_number,
      invoiceDate: row.invoice_date,
      customerName: row.customer_name,
      boatName: row.boat_name,
      tripNumber: row.trip_number,
      quantity: row.quantity,
      unitPrice: row.unit_price,
      revenue: row.revenue,
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
 * Query params for GET /reports/fish-sales-history
 * (app/modules/reports/schemas.py's FishSalesHistoryParams) - `fish_id` is
 * required, unlike every other entity filter in this module: this endpoint
 * only ever powers the Fish Detail page's own Sales History section.
 */
export interface FishSalesHistoryParams {
  fish_id: string;
  page: number;
  page_size: number;
}
