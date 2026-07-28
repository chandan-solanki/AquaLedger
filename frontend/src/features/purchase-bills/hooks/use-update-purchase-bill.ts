"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { purchaseBillKeys } from "@/features/purchase-bills/constants/query-keys";
import { purchaseBillService } from "@/features/purchase-bills/services/purchase-bill-service";
import type { PurchaseBillUpdateRequest } from "@/features/purchase-bills/types/purchase-bill";

export interface UpdatePurchaseBillVariables {
  id: string;
  payload: PurchaseBillUpdateRequest;
}

export function useUpdatePurchaseBill() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: UpdatePurchaseBillVariables) =>
      purchaseBillService.updatePurchaseBill(id, payload),
    onSuccess: (bill) => {
      queryClient.invalidateQueries({ queryKey: purchaseBillKeys.lists() });
      queryClient.invalidateQueries({ queryKey: purchaseBillKeys.detail(bill.id) });
    },
  });
}
