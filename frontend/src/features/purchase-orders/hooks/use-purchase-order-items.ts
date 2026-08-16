"use client";

import { useQuery } from "@tanstack/react-query";

import { purchaseOrderItemKeys } from "@/features/purchase-orders/constants/query-keys";
import { purchaseOrderItemService } from "@/features/purchase-orders/services/purchase-order-item-service";

/**
 * Every line item on one purchase order - disabled until a purchase order
 * id is available. No pagination (`GET /purchase-orders/{id}/items` returns
 * a plain array), so the Detail page's Items section fetches and renders
 * the whole set at once, mirroring `usePurchaseBillItems`.
 */
export function usePurchaseOrderItems(purchaseOrderId: string | undefined) {
  return useQuery({
    queryKey: purchaseOrderItemKeys.byOrder(purchaseOrderId ?? ""),
    queryFn: () => purchaseOrderItemService.listPurchaseOrderItems(purchaseOrderId as string),
    enabled: Boolean(purchaseOrderId),
  });
}
