"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { purchaseOrderKeys } from "@/features/purchase-orders/constants/query-keys";
import { purchaseOrderService } from "@/features/purchase-orders/services/purchase-order-service";
import type { PurchaseOrderUpdateRequest } from "@/features/purchase-orders/types/purchase-order";

export interface UpdatePurchaseOrderVariables {
  id: string;
  payload: PurchaseOrderUpdateRequest;
}

export function useUpdatePurchaseOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: UpdatePurchaseOrderVariables) =>
      purchaseOrderService.updatePurchaseOrder(id, payload),
    onSuccess: (order) => {
      queryClient.invalidateQueries({ queryKey: purchaseOrderKeys.lists() });
      queryClient.invalidateQueries({ queryKey: purchaseOrderKeys.detail(order.id) });
    },
  });
}
