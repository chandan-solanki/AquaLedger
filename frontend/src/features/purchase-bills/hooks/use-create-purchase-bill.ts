"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { purchaseBillKeys } from "@/features/purchase-bills/constants/query-keys";
import { purchaseBillService } from "@/features/purchase-bills/services/purchase-bill-service";
import type { PurchaseBillCreateRequest } from "@/features/purchase-bills/types/purchase-bill";

export function useCreatePurchaseBill() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: PurchaseBillCreateRequest) => purchaseBillService.createPurchaseBill(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: purchaseBillKeys.lists() });
    },
  });
}
