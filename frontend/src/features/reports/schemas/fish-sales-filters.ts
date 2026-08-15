import type { FishSalesParams } from "@/features/reports/types/fish-sales";

/**
 * Fish Sales Analytics filter/page state. Every entity filter (`fishId`/
 * `customerId`/`boatId`/`tripId`) is an optional narrowing filter, not a
 * required backend param - the report loads with every sold fish by
 * default (mirrors `SalesReportFilters`' own posture). `minQuantity`/
 * `minRevenue` are plain numeric strings (not a min/max range) - "Minimum
 * Quantity"/"Minimum Revenue" are the report's own literal filter names.
 * No `sort` field - the backend's order is fixed (`revenue DESC, fish name
 * ASC`), not client-configurable.
 */
export interface FishSalesFilters {
  search: string;
  fishId: string | null;
  fromDate: string | null;
  toDate: string | null;
  customerId: string | null;
  boatId: string | null;
  tripId: string | null;
  minQuantity: string | null;
  minRevenue: string | null;
  page: number;
  pageSize: number;
}

export const DEFAULT_FISH_SALES_FILTERS: FishSalesFilters = {
  search: "",
  fishId: null,
  fromDate: null,
  toDate: null,
  customerId: null,
  boatId: null,
  tripId: null,
  minQuantity: null,
  minRevenue: null,
  page: 1,
  pageSize: 20,
};

/** Maps the client's filter state onto the backend's FishSalesParams query shape. */
export function toFishSalesParams(filters: FishSalesFilters): FishSalesParams {
  return {
    fish_id: filters.fishId ?? undefined,
    from_date: filters.fromDate ?? undefined,
    to_date: filters.toDate ?? undefined,
    customer_id: filters.customerId ?? undefined,
    boat_id: filters.boatId ?? undefined,
    trip_id: filters.tripId ?? undefined,
    min_quantity: filters.minQuantity ?? undefined,
    min_revenue: filters.minRevenue ?? undefined,
    q: filters.search.trim() || undefined,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
