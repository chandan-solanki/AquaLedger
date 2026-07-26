import type { CompanyListParams, CompanyStatus } from "@/features/companies/types/company";

/** Matches the backend's `_SORTABLE_FIELDS` (app/modules/companies/schemas.py) exactly. */
export const COMPANY_SORT_FIELDS = ["name", "code", "created_at", "updated_at"] as const;
export type CompanySortField = (typeof COMPANY_SORT_FIELDS)[number];

export const COMPANY_SORT_DIRECTIONS = ["asc", "desc"] as const;
export type CompanySortDirection = (typeof COMPANY_SORT_DIRECTIONS)[number];

/**
 * `sort`/`direction` are kept separate here (rather than the backend's
 * combined `-field` string) since each is its own URL search param
 * (Sprint 3 Session 4) — `toCompanyListParams` is what recombines them into
 * the wire format the backend actually expects.
 */
export interface CompanyFilters {
  search: string;
  status: CompanyStatus | null;
  city: string;
  page: number;
  pageSize: number;
  sort: CompanySortField;
  direction: CompanySortDirection;
}

export const DEFAULT_COMPANY_FILTERS: CompanyFilters = {
  search: "",
  status: null,
  city: "",
  page: 1,
  pageSize: 20,
  sort: "created_at",
  direction: "desc",
};

/** Maps the client's filter state onto the backend's CompanyListParams query shape. */
export function toCompanyListParams(filters: CompanyFilters): CompanyListParams {
  return {
    q: filters.search.trim() || undefined,
    status: filters.status ?? undefined,
    city: filters.city.trim() || undefined,
    sort: filters.direction === "desc" ? `-${filters.sort}` : filters.sort,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
