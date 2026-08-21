import type { FishStockStatus } from "@/features/fish-stock/constants/fish-stock-status";
import type { FishStockListParams } from "@/features/fish-stock/types/fish-stock";

/**
 * `status` is kept as the client's active/inactive vocabulary (rather than
 * the backend's raw boolean) the same way `FishFilters.status` is, so the
 * URL and the `StatusFilter` UI both read naturally.
 */
export interface FishStockFilters {
  search: string;
  status: FishStockStatus | null;
  page: number;
  pageSize: number;
}

export const DEFAULT_FISH_STOCK_FILTERS: FishStockFilters = {
  search: "",
  status: null,
  page: 1,
  pageSize: 20,
};

/** Maps the client's filter state onto the backend's FishStockListParams query shape. */
export function toFishStockListParams(filters: FishStockFilters): FishStockListParams {
  return {
    q: filters.search.trim() || undefined,
    is_active: filters.status === "active" ? true : filters.status === "inactive" ? false : undefined,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
