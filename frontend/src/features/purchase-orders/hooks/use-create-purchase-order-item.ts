"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { purchaseOrderItemKeys, purchaseOrderKeys } from "@/features/purchase-orders/constants/query-keys";
import { purchaseOrderItemService } from "@/features/purchase-orders/services/purchase-order-item-service";
import type { PurchaseOrderItemCreateRequest } from "@/features/purchase-orders/types/purchase-order-item";

export interface CreatePurchaseOrderItemVariables {
  purchaseOrderId: string;
  payload: PurchaseOrderItemCreateRequest;
}

/**
 * Adding an item recalculates the parent purchase order's own totals
 * server-side, so both this order's item list AND its detail query are
 * invalidated - the List page's Total Amount column is invalidated too,
 * since it'd otherwise go stale, mirroring `useCreatePurchaseBillItem`.
 * Never patched optimistically, per the "server as source of truth"
 * principle for financial figures.
 */
export function useCreatePurchaseOrderItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ purchaseOrderId, payload }: CreatePurchaseOrderItemVariables) =>
      purchaseOrderItemService.createPurchaseOrderItem(purchaseOrderId, payload),
    onSuccess: (_item, { purchaseOrderId }) => {
      queryClient.invalidateQueries({ queryKey: purchaseOrderItemKeys.byOrder(purchaseOrderId) });
      queryClient.invalidateQueries({ queryKey: purchaseOrderKeys.detail(purchaseOrderId) });
      queryClient.invalidateQueries({ queryKey: purchaseOrderKeys.lists() });
    },
  });
}
