"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { purchaseOrderKeys } from "@/features/purchase-orders/constants/query-keys";
import { purchaseOrderService } from "@/features/purchase-orders/services/purchase-order-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * The draft -> confirmed transition (app/modules/purchase_orders/
 * service.py's `PurchaseOrderService.confirm`, mirroring `usePostPurchaseBill`'s
 * shape): irreversible, assigns `po_number`, recalculates all totals from
 * the order's current items - nothing is computed here, only invalidated,
 * so the next read shows the server's own numbers.
 *
 * Unlike `usePostPurchaseBill`, this invalidates only this order's own
 * queries - confirming a purchase order never touches supplier outstanding
 * or ledger (it is a procurement commitment, not a bill), so there is no
 * `supplierKeys` invalidation to make here.
 */
export function useConfirmPurchaseOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => purchaseOrderService.confirmPurchaseOrder(id),
    onSuccess: (order) => {
      queryClient.invalidateQueries({ queryKey: purchaseOrderKeys.detail(order.id) });
      queryClient.invalidateQueries({ queryKey: purchaseOrderKeys.lists() });
      toastSuccess(order.poNumber ? `${order.poNumber} confirmed.` : "Purchase order confirmed.");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
