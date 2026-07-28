"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { purchaseBillItemKeys, purchaseBillKeys } from "@/features/purchase-bills/constants/query-keys";
import { purchaseBillItemService } from "@/features/purchase-bills/services/purchase-bill-item-service";
import type { PurchaseBillItemCreateRequest } from "@/features/purchase-bills/types/purchase-bill-item";

export interface CreatePurchaseBillItemVariables {
  purchaseBillId: string;
  payload: PurchaseBillItemCreateRequest;
}

/**
 * Adding an item recalculates the parent purchase bill's own totals
 * server-side (PurchaseService.add_item -> the financial engine in
 * app.modules.purchase.domain.totals), so both this bill's item list AND
 * its detail query are invalidated - the List page's Total/Balance Amount
 * columns are invalidated too, since they'd otherwise go stale, mirroring
 * `useCreateInvoiceItem`. Never patched optimistically, per the "server as
 * source of truth" principle for financial figures.
 */
export function useCreatePurchaseBillItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ purchaseBillId, payload }: CreatePurchaseBillItemVariables) =>
      purchaseBillItemService.createPurchaseBillItem(purchaseBillId, payload),
    onSuccess: (_item, { purchaseBillId }) => {
      queryClient.invalidateQueries({ queryKey: purchaseBillItemKeys.byBill(purchaseBillId) });
      queryClient.invalidateQueries({ queryKey: purchaseBillKeys.detail(purchaseBillId) });
      queryClient.invalidateQueries({ queryKey: purchaseBillKeys.lists() });
    },
  });
}
