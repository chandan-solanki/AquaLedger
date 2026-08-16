"use client";

import { useQuery } from "@tanstack/react-query";

import { purchaseOrderItemKeys } from "@/features/purchase-orders/constants/query-keys";
import { purchaseOrderItemService } from "@/features/purchase-orders/services/purchase-order-item-service";

/**
 * A single line item, derived from the same list query `usePurchaseOrderItems`
 * reads (`GET /purchase-orders/{purchase_order_id}/items`) - the backend
 * exposes no single-item GET endpoint (only list/create/update/delete), so
 * this shares that hook's exact queryKey/queryFn (TanStack Query dedupes
 * the request rather than issuing a second one) and selects one row by id,
 * mirroring `usePurchaseBillItem`. Used by `PurchaseOrderItemTable` to
 * populate the Edit dialog from the freshest cached list data for the row
 * the user clicked.
 */
export function usePurchaseOrderItem(purchaseOrderId: string | undefined, itemId: string | undefined) {
  return useQuery({
    queryKey: purchaseOrderItemKeys.byOrder(purchaseOrderId ?? ""),
    queryFn: () => purchaseOrderItemService.listPurchaseOrderItems(purchaseOrderId as string),
    enabled: Boolean(purchaseOrderId),
    select: (items) => items.find((item) => item.id === itemId),
  });
}
