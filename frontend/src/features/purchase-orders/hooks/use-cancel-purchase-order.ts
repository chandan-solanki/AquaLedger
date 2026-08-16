"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { purchaseOrderKeys } from "@/features/purchase-orders/constants/query-keys";
import { purchaseOrderService } from "@/features/purchase-orders/services/purchase-order-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * `draft`|`confirmed` -> `cancelled`. No side effects on any other module -
 * a cancelled purchase order never affected supplier outstanding/ledger in
 * the first place, so there is nothing to reverse and nothing to invalidate
 * beyond this order's own queries.
 */
export function useCancelPurchaseOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => purchaseOrderService.cancelPurchaseOrder(id),
    onSuccess: (order) => {
      queryClient.invalidateQueries({ queryKey: purchaseOrderKeys.detail(order.id) });
      queryClient.invalidateQueries({ queryKey: purchaseOrderKeys.lists() });
      toastSuccess("Purchase order cancelled.");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
