"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { purchaseOrderItemKeys, purchaseOrderKeys } from "@/features/purchase-orders/constants/query-keys";
import { purchaseOrderItemService } from "@/features/purchase-orders/services/purchase-order-item-service";
import type { PurchaseOrderItemUpdateRequest } from "@/features/purchase-orders/types/purchase-order-item";

export interface UpdatePurchaseOrderItemVariables {
  purchaseOrderId: string;
  itemId: string;
  payload: PurchaseOrderItemUpdateRequest;
}

/** Same invalidation shape as `useCreatePurchaseOrderItem` - updating an item also recalculates the parent order's totals. */
export function useUpdatePurchaseOrderItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ purchaseOrderId, itemId, payload }: UpdatePurchaseOrderItemVariables) =>
      purchaseOrderItemService.updatePurchaseOrderItem(purchaseOrderId, itemId, payload),
    onSuccess: (_item, { purchaseOrderId }) => {
      queryClient.invalidateQueries({ queryKey: purchaseOrderItemKeys.byOrder(purchaseOrderId) });
      queryClient.invalidateQueries({ queryKey: purchaseOrderKeys.detail(purchaseOrderId) });
      queryClient.invalidateQueries({ queryKey: purchaseOrderKeys.lists() });
    },
  });
}
