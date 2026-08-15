/** Mirrors the backend's FishUnit enum (app/modules/fish/constants.py). */
export type FishSalesUnit = "kg" | "box" | "piece" | "ton";

/**
 * Raw backend shape (snake_case), matching FishSalesResponse
 * (app/modules/reports/schemas.py) exactly. Every money/quantity field is a
 * string - the backend serializes `Decimal` as a JSON string, never a
 * float (ARCHITECTURE.md §5.1).
 */
export interface BackendFishSalesRow {
  fish_id: string;
  fish_name: string;
  scientific_name: string | null;
  unit: FishSalesUnit;
  quantity_sold: string;
  revenue: string;
  average_selling_price: string;
  invoice_count: number;
  trip_count: number;
  customer_count: number;
  last_sold_date: string | null;
}

export interface BackendFishSalesSummary {
  total_fish_sold: string;
  total_revenue: string;
  average_selling_price: string;
  best_selling_fish_name: string | null;
  best_selling_fish_quantity: string | null;
  highest_revenue_fish_name: string | null;
  highest_revenue_fish_revenue: string | null;
  total_fish_types_sold: number;
}

export interface BackendPaginationMeta {
  total_records: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface BackendFishSalesResponse {
  summary: BackendFishSalesSummary;
  rows: BackendFishSalesRow[];
  pagination: BackendPaginationMeta;
}

/** The client-facing, camelCase shape reportsService.getFishSales returns. */
export interface FishSalesRow {
  fishId: string;
  fishName: string;
  scientificName: string | null;
  unit: FishSalesUnit;
  quantitySold: string;
  revenue: string;
  averageSellingPrice: string;
  invoiceCount: number;
  tripCount: number;
  customerCount: number;
  lastSoldDate: string | null;
}

export interface FishSalesSummary {
  totalFishSold: string;
  totalRevenue: string;
  averageSellingPrice: string;
  bestSellingFishName: string | null;
  bestSellingFishQuantity: string | null;
  highestRevenueFishName: string | null;
  highestRevenueFishRevenue: string | null;
  totalFishTypesSold: number;
}

export interface PaginationMeta {
  totalRecords: number;
  totalPages: number;
  currentPage: number;
  pageSize: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface FishSalesData {
  summary: FishSalesSummary;
  rows: FishSalesRow[];
  pagination: PaginationMeta;
}

export function mapBackendFishSales(response: BackendFishSalesResponse): FishSalesData {
  return {
    summary: {
      totalFishSold: response.summary.total_fish_sold,
      totalRevenue: response.summary.total_revenue,
      averageSellingPrice: response.summary.average_selling_price,
      bestSellingFishName: response.summary.best_selling_fish_name,
      bestSellingFishQuantity: response.summary.best_selling_fish_quantity,
      highestRevenueFishName: response.summary.highest_revenue_fish_name,
      highestRevenueFishRevenue: response.summary.highest_revenue_fish_revenue,
      totalFishTypesSold: response.summary.total_fish_types_sold,
    },
    rows: response.rows.map((row) => ({
      fishId: row.fish_id,
      fishName: row.fish_name,
      scientificName: row.scientific_name,
      unit: row.unit,
      quantitySold: row.quantity_sold,
      revenue: row.revenue,
      averageSellingPrice: row.average_selling_price,
      invoiceCount: row.invoice_count,
      tripCount: row.trip_count,
      customerCount: row.customer_count,
      lastSoldDate: row.last_sold_date,
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
 * Query params for GET /reports/fish-sales (app/modules/reports/schemas.py's
 * FishSalesParams) - snake_case to match the wire format exactly. No
 * `sort` field - the backend's order is fixed (`revenue DESC, fish name
 * ASC`), not client-configurable.
 */
export interface FishSalesParams {
  fish_id?: string;
  from_date?: string;
  to_date?: string;
  customer_id?: string;
  boat_id?: string;
  trip_id?: string;
  min_quantity?: string;
  min_revenue?: string;
  q?: string;
  page: number;
  page_size: number;
}
