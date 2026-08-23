import type { TenantListParams, TenantStatus } from "@/features/platform/types/tenant";

export interface TenantFilters {
  search: string;
  status: TenantStatus | null;
  page: number;
  pageSize: number;
}

export const DEFAULT_TENANT_FILTERS: TenantFilters = {
  search: "",
  status: null,
  page: 1,
  pageSize: 20,
};

/** Maps the client's filter state onto the backend's TenantListParams query shape. */
export function toTenantListParams(filters: TenantFilters): TenantListParams {
  return {
    q: filters.search.trim() || undefined,
    status: filters.status ?? undefined,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
