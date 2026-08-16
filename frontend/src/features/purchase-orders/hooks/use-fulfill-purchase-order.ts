"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { purchaseOrderKeys } from "@/features/purchase-orders/constants/query-keys";
import { purchaseOrderService } from "@/features/purchase-orders/services/purchase-order-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * `confirmed` -> `fulfilled`, terminal. This is simply the PO lifecycle
 * foundation - it does not create Purchase Bills, does not create payment
 * records, and does not modify supplier outstanding.
 */
export function useFulfillPurchaseOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => purchaseOrderService.fulfillPurchaseOrder(id),
    onSuccess: (order) => {
      queryClient.invalidateQueries({ queryKey: purchaseOrderKeys.detail(order.id) });
      queryClient.invalidateQueries({ queryKey: purchaseOrderKeys.lists() });
      toastSuccess("Purchase order marked as fulfilled.");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
