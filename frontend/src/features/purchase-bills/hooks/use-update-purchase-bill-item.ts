"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { purchaseBillItemKeys, purchaseBillKeys } from "@/features/purchase-bills/constants/query-keys";
import { purchaseBillItemService } from "@/features/purchase-bills/services/purchase-bill-item-service";
import type { PurchaseBillItemUpdateRequest } from "@/features/purchase-bills/types/purchase-bill-item";

export interface UpdatePurchaseBillItemVariables {
  purchaseBillId: string;
  itemId: string;
  payload: PurchaseBillItemUpdateRequest;
}

/** Same invalidation shape as `useCreatePurchaseBillItem` - updating an item also recalculates the parent bill's totals. */
export function useUpdatePurchaseBillItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ purchaseBillId, itemId, payload }: UpdatePurchaseBillItemVariables) =>
      purchaseBillItemService.updatePurchaseBillItem(purchaseBillId, itemId, payload),
    onSuccess: (_item, { purchaseBillId }) => {
      queryClient.invalidateQueries({ queryKey: purchaseBillItemKeys.byBill(purchaseBillId) });
      queryClient.invalidateQueries({ queryKey: purchaseBillKeys.detail(purchaseBillId) });
      queryClient.invalidateQueries({ queryKey: purchaseBillKeys.lists() });
    },
  });
}
