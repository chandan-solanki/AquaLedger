"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { supplierPaymentKeys } from "@/features/supplier-payments/constants/query-keys";
import type { SupplierPaymentFilters } from "@/features/supplier-payments/schemas/supplier-payment-filters";
import { toSupplierPaymentListParams } from "@/features/supplier-payments/schemas/supplier-payment-filters";
import { supplierPaymentService } from "@/features/supplier-payments/services/supplier-payment-service";

/**
 * Server-side, paginated supplier payment list - every filter/sort/page
 * change refetches from the backend rather than filtering an already-loaded
 * page client-side, mirroring `usePayments`. `keepPreviousData` keeps the
 * current rows on screen (instead of flashing to a loading state) while a
 * filter/page change is in flight.
 */
export function useSupplierPayments(filters: SupplierPaymentFilters) {
  const params = toSupplierPaymentListParams(filters);

  return useQuery({
    queryKey: supplierPaymentKeys.list(params),
    queryFn: () => supplierPaymentService.listSupplierPayments(params),
    placeholderData: keepPreviousData,
  });
}
