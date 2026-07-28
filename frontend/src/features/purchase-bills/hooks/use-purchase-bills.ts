"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { purchaseBillKeys } from "@/features/purchase-bills/constants/query-keys";
import type { PurchaseBillFilters } from "@/features/purchase-bills/schemas/purchase-bill-filters";
import { toPurchaseBillListParams } from "@/features/purchase-bills/schemas/purchase-bill-filters";
import { purchaseBillService } from "@/features/purchase-bills/services/purchase-bill-service";

/**
 * Server-side, paginated purchase bills list - every filter/sort/page
 * change refetches from the backend rather than filtering an already-loaded
 * page client-side, mirroring `useInvoices`. `keepPreviousData` keeps the
 * current rows on screen (instead of flashing to a loading state) while a
 * filter/page change is in flight.
 */
export function usePurchaseBills(filters: PurchaseBillFilters) {
  const params = toPurchaseBillListParams(filters);

  return useQuery({
    queryKey: purchaseBillKeys.list(params),
    queryFn: () => purchaseBillService.listPurchaseBills(params),
    placeholderData: keepPreviousData,
  });
}
