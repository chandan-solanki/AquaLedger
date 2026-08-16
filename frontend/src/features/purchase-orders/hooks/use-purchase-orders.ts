"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { purchaseOrderKeys } from "@/features/purchase-orders/constants/query-keys";
import type { PurchaseOrderFilters } from "@/features/purchase-orders/schemas/purchase-order-filters";
import { toPurchaseOrderListParams } from "@/features/purchase-orders/schemas/purchase-order-filters";
import { purchaseOrderService } from "@/features/purchase-orders/services/purchase-order-service";

/**
 * Server-side, paginated purchase orders list - every filter/sort/page
 * change refetches from the backend rather than filtering an already-loaded
 * page client-side, mirroring `usePurchaseBills`. `keepPreviousData` keeps
 * the current rows on screen (instead of flashing to a loading state) while
 * a filter/page change is in flight.
 */
export function usePurchaseOrders(filters: PurchaseOrderFilters) {
  const params = toPurchaseOrderListParams(filters);

  return useQuery({
    queryKey: purchaseOrderKeys.list(params),
    queryFn: () => purchaseOrderService.listPurchaseOrders(params),
    placeholderData: keepPreviousData,
  });
}
