"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { purchaseOrderItemKeys, purchaseOrderKeys } from "@/features/purchase-orders/constants/query-keys";
import { purchaseOrderService } from "@/features/purchase-orders/services/purchase-order-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Owns the full delete outcome (cache invalidation, toast, navigation) so
 * every call site gets identical behavior, mirroring `useDeleteInvoice`
 * exactly. Only `draft` purchase orders may be deleted (409
 * `PURCHASE_ORDER_NOT_DRAFT` otherwise, app/modules/purchase_orders/
 * service.py's `_ensure_draft`) - a draft has never been confirmed, so it
 * has never touched anything outside its own record, meaning deleting one
 * has no side effects to invalidate beyond its own queries.
 */
export function useDeletePurchaseOrder() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (id: string) => purchaseOrderService.deletePurchaseOrder(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: purchaseOrderKeys.lists() });
      queryClient.removeQueries({ queryKey: purchaseOrderKeys.detail(id) });
      queryClient.removeQueries({ queryKey: purchaseOrderItemKeys.byOrder(id) });
      toastSuccess("Purchase order deleted.");
      router.push("/purchase-orders");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
