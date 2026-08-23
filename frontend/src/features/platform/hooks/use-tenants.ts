"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { platformTenantKeys } from "@/features/platform/constants/query-keys";
import type { TenantFilters } from "@/features/platform/schemas/tenant-filters";
import { toTenantListParams } from "@/features/platform/schemas/tenant-filters";
import { platformTenantService } from "@/features/platform/services/tenant-service";

/**
 * Server-side, paginated tenant list — mirrors useCompanies' rationale
 * exactly: every filter/page change refetches rather than filtering an
 * already-loaded page client-side, and `keepPreviousData` avoids a loading
 * flash between pages.
 */
export function useTenants(filters: TenantFilters) {
  const params = toTenantListParams(filters);

  return useQuery({
    queryKey: platformTenantKeys.list(params),
    queryFn: () => platformTenantService.listTenants(params),
    placeholderData: keepPreviousData,
  });
}
