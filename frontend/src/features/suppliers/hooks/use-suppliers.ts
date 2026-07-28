"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { supplierKeys } from "@/features/suppliers/constants/query-keys";
import type { SupplierFilters } from "@/features/suppliers/schemas/supplier-filters";
import { toSupplierListParams } from "@/features/suppliers/schemas/supplier-filters";
import { supplierService } from "@/features/suppliers/services/supplier-service";

/**
 * Server-side, paginated suppliers list - every filter/sort/page change
 * refetches from the backend rather than filtering an already-loaded page
 * client-side, mirroring `useCompanies`. `keepPreviousData` keeps the
 * current rows on screen (instead of flashing to a loading state) while a
 * filter/page change is in flight.
 */
export function useSuppliers(filters: SupplierFilters) {
  const params = toSupplierListParams(filters);

  return useQuery({
    queryKey: supplierKeys.list(params),
    queryFn: () => supplierService.listSuppliers(params),
    placeholderData: keepPreviousData,
  });
}
