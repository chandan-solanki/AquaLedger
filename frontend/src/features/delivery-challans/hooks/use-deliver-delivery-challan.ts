"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { deliveryChallanKeys } from "@/features/delivery-challans/constants/query-keys";
import { deliveryChallanService } from "@/features/delivery-challans/services/delivery-challan-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * `dispatched` -> `delivered` (terminal). No side effects on any other
 * module - delivery completion never touches customer outstanding, invoice
 * balance, or ledger.
 */
export function useDeliverDeliveryChallan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deliveryChallanService.deliverDeliveryChallan(id),
    onSuccess: (challan) => {
      queryClient.invalidateQueries({ queryKey: deliveryChallanKeys.detail(challan.id) });
      queryClient.invalidateQueries({ queryKey: deliveryChallanKeys.lists() });
      toastSuccess("Delivery challan marked as delivered.");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
