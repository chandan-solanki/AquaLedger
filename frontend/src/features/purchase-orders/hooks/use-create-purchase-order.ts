"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { purchaseOrderKeys } from "@/features/purchase-orders/constants/query-keys";
import { purchaseOrderService } from "@/features/purchase-orders/services/purchase-order-service";
import type { PurchaseOrderCreateRequest } from "@/features/purchase-orders/types/purchase-order";

export function useCreatePurchaseOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: PurchaseOrderCreateRequest) => purchaseOrderService.createPurchaseOrder(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: purchaseOrderKeys.lists() });
    },
  });
}
