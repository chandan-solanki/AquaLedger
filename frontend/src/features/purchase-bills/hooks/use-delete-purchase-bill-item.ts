"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { purchaseBillItemKeys, purchaseBillKeys } from "@/features/purchase-bills/constants/query-keys";
import { purchaseBillItemService } from "@/features/purchase-bills/services/purchase-bill-item-service";

export interface DeletePurchaseBillItemVariables {
  purchaseBillId: string;
  itemId: string;
}

/** Same invalidation shape as `useCreatePurchaseBillItem` - deleting an item also recalculates the parent bill's totals from the remaining items. */
export function useDeletePurchaseBillItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ purchaseBillId, itemId }: DeletePurchaseBillItemVariables) =>
      purchaseBillItemService.deletePurchaseBillItem(purchaseBillId, itemId),
    onSuccess: (_data, { purchaseBillId }) => {
      queryClient.invalidateQueries({ queryKey: purchaseBillItemKeys.byBill(purchaseBillId) });
      queryClient.invalidateQueries({ queryKey: purchaseBillKeys.detail(purchaseBillId) });
      queryClient.invalidateQueries({ queryKey: purchaseBillKeys.lists() });
    },
  });
}
