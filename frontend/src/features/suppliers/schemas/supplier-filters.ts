import type { SupplierListParams, SupplierStatus } from "@/features/suppliers/types/supplier";

/** Matches the backend's `_SORTABLE_FIELDS` (app/modules/suppliers/schemas.py) exactly. */
export const SUPPLIER_SORT_FIELDS = ["name", "code", "created_at"] as const;
export type SupplierSortField = (typeof SUPPLIER_SORT_FIELDS)[number];

export const SUPPLIER_SORT_DIRECTIONS = ["asc", "desc"] as const;
export type SupplierSortDirection = (typeof SUPPLIER_SORT_DIRECTIONS)[number];

/**
 * `sort`/`direction` are kept separate here (rather than the backend's
 * combined `-field` string) since each is its own URL search param -
 * `toSupplierListParams` recombines them into the wire format the backend
 * actually expects, mirroring `CompanyFilters`. `state` is a real, backend-
 * supported filter (`SupplierListParams.state`) but deliberately not wired
 * to a filter control yet, the same deferral `CompanyFilters` made for its
 * own `state` field.
 */
export interface SupplierFilters {
  search: string;
  status: SupplierStatus | null;
  city: string;
  page: number;
  pageSize: number;
  sort: SupplierSortField;
  direction: SupplierSortDirection;
}

export const DEFAULT_SUPPLIER_FILTERS: SupplierFilters = {
  search: "",
  status: null,
  city: "",
  page: 1,
  pageSize: 20,
  sort: "created_at",
  direction: "desc",
};

/** Maps the client's filter state onto the backend's SupplierListParams query shape. */
export function toSupplierListParams(filters: SupplierFilters): SupplierListParams {
  return {
    q: filters.search.trim() || undefined,
    status: filters.status ?? undefined,
    city: filters.city.trim() || undefined,
    sort: filters.direction === "desc" ? `-${filters.sort}` : filters.sort,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
