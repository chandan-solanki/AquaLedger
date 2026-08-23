"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import { TENANT_STATUS_VALUES } from "@/features/platform/constants/tenant-status";
import { DEFAULT_TENANT_FILTERS } from "@/features/platform/schemas/tenant-filters";

const tenantFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_TENANT_FILTERS.search),
  status: parseAsStringEnum([...TENANT_STATUS_VALUES]),
  page: parseAsInteger.withDefault(DEFAULT_TENANT_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_TENANT_FILTERS.pageSize),
};

/**
 * Tenant list filter/page state, synced to the URL via nuqs - same
 * rationale as useCompanyFilters: a refresh, shared link, or Back/Forward
 * all restore the exact same list state.
 */
export function useTenantFilters() {
  return useQueryStates(tenantFilterParsers, { history: "push" });
}
