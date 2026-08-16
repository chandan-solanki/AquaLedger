"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { deliveryChallanItemKeys, deliveryChallanKeys } from "@/features/delivery-challans/constants/query-keys";
import { deliveryChallanService } from "@/features/delivery-challans/services/delivery-challan-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Owns the full delete outcome (cache invalidation, toast, navigation) so
 * every call site gets identical behavior, mirroring `useDeletePurchaseOrder`.
 * Only `draft` delivery challans may be deleted (409
 * `DELIVERY_CHALLAN_NOT_DRAFT` otherwise) - a draft has never been
 * dispatched, so it has never touched anything outside its own record,
 * meaning deleting one has no side effects to invalidate beyond its own
 * queries.
 */
export function useDeleteDeliveryChallan() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (id: string) => deliveryChallanService.deleteDeliveryChallan(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: deliveryChallanKeys.lists() });
      queryClient.removeQueries({ queryKey: deliveryChallanKeys.detail(id) });
      queryClient.removeQueries({ queryKey: deliveryChallanItemKeys.byChallan(id) });
      toastSuccess("Delivery challan deleted.");
      router.push("/delivery-challans");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
