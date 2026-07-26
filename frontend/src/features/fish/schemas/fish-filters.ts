import type { FishStatus } from "@/features/fish/constants/fish-status";
import type { FishListParams, FishUnit } from "@/features/fish/types/fish";

/** Matches the backend's `_SORTABLE_FIELDS` (app/modules/fish/schemas.py) exactly. */
export const FISH_SORT_FIELDS = ["name", "code", "created_at", "updated_at"] as const;
export type FishSortField = (typeof FISH_SORT_FIELDS)[number];

export const FISH_SORT_DIRECTIONS = ["asc", "desc"] as const;
export type FishSortDirection = (typeof FISH_SORT_DIRECTIONS)[number];

/**
 * `sort`/`direction` are kept separate here (rather than the backend's
 * combined `-field` string) since each is its own URL search param, mirroring
 * `CompanyFilters` - `toFishListParams` recombines them into the wire format
 * the backend actually expects.
 */
export interface FishFilters {
  search: string;
  status: FishStatus | null;
  category: string;
  unit: FishUnit | null;
  page: number;
  pageSize: number;
  sort: FishSortField;
  direction: FishSortDirection;
}

export const DEFAULT_FISH_FILTERS: FishFilters = {
  search: "",
  status: null,
  category: "",
  unit: null,
  page: 1,
  pageSize: 20,
  sort: "created_at",
  direction: "desc",
};

/** Maps the client's filter state onto the backend's FishListParams query shape. */
export function toFishListParams(filters: FishFilters): FishListParams {
  return {
    q: filters.search.trim() || undefined,
    category: filters.category.trim() || undefined,
    unit: filters.unit ?? undefined,
    is_active: filters.status === "active" ? true : filters.status === "inactive" ? false : undefined,
    sort: filters.direction === "desc" ? `-${filters.sort}` : filters.sort,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
