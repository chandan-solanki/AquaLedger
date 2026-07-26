"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { companyKeys } from "@/features/companies/constants/query-keys";
import type { CompanyFilters } from "@/features/companies/schemas/company-filters";
import { toCompanyListParams } from "@/features/companies/schemas/company-filters";
import { companyService } from "@/features/companies/services/company-service";

/**
 * Server-side, paginated companies list — every filter/sort/page change
 * refetches from the backend rather than filtering an already-loaded page
 * client-side. `keepPreviousData` keeps the current rows on screen (instead
 * of flashing to a loading state) while a filter/page change is in flight.
 */
export function useCompanies(filters: CompanyFilters) {
  const params = toCompanyListParams(filters);

  return useQuery({
    queryKey: companyKeys.list(params),
    queryFn: () => companyService.listCompanies(params),
    placeholderData: keepPreviousData,
  });
}
