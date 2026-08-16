"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { purchaseOrderItemKeys, purchaseOrderKeys } from "@/features/purchase-orders/constants/query-keys";
import { purchaseOrderItemService } from "@/features/purchase-orders/services/purchase-order-item-service";

export interface DeletePurchaseOrderItemVariables {
  purchaseOrderId: string;
  itemId: string;
}

/** Same invalidation shape as `useCreatePurchaseOrderItem` - deleting an item also recalculates the parent order's totals from the remaining items. */
export function useDeletePurchaseOrderItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ purchaseOrderId, itemId }: DeletePurchaseOrderItemVariables) =>
      purchaseOrderItemService.deletePurchaseOrderItem(purchaseOrderId, itemId),
    onSuccess: (_data, { purchaseOrderId }) => {
      queryClient.invalidateQueries({ queryKey: purchaseOrderItemKeys.byOrder(purchaseOrderId) });
      queryClient.invalidateQueries({ queryKey: purchaseOrderKeys.detail(purchaseOrderId) });
      queryClient.invalidateQueries({ queryKey: purchaseOrderKeys.lists() });
    },
  });
}
