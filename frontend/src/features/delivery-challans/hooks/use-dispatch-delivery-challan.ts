"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { deliveryChallanKeys } from "@/features/delivery-challans/constants/query-keys";
import { deliveryChallanService } from "@/features/delivery-challans/services/delivery-challan-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * The draft -> dispatched transition (app/modules/delivery_challans/
 * service.py's `DeliveryChallanService.dispatch`, mirroring
 * `useConfirmPurchaseOrder`'s shape): irreversible, assigns
 * `challan_number` - nothing is computed here, only invalidated, so the
 * next read shows the server's own number. Never touches customer
 * outstanding, invoice balance, or ledger.
 */
export function useDispatchDeliveryChallan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deliveryChallanService.dispatchDeliveryChallan(id),
    onSuccess: (challan) => {
      queryClient.invalidateQueries({ queryKey: deliveryChallanKeys.detail(challan.id) });
      queryClient.invalidateQueries({ queryKey: deliveryChallanKeys.lists() });
      toastSuccess(challan.challanNumber ? `${challan.challanNumber} dispatched.` : "Delivery challan dispatched.");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
