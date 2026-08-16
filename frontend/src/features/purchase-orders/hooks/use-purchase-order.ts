"use client";

import { useQuery } from "@tanstack/react-query";

import { purchaseOrderKeys } from "@/features/purchase-orders/constants/query-keys";
import { purchaseOrderService } from "@/features/purchase-orders/services/purchase-order-service";

/** A single purchase order by id - disabled until an id is available. */
export function usePurchaseOrder(id: string | undefined) {
  return useQuery({
    queryKey: purchaseOrderKeys.detail(id ?? ""),
    queryFn: () => purchaseOrderService.getPurchaseOrder(id as string),
    enabled: Boolean(id),
  });
}
