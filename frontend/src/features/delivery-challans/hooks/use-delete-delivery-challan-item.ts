"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { deliveryChallanItemKeys } from "@/features/delivery-challans/constants/query-keys";
import { deliveryChallanItemService } from "@/features/delivery-challans/services/delivery-challan-item-service";

export interface DeleteDeliveryChallanItemVariables {
  deliveryChallanId: string;
  itemId: string;
}

/** Same invalidation shape as `useCreateDeliveryChallanItem` - deleting an item immediately frees its reserved quantity for other delivery challans against the same invoice item. */
export function useDeleteDeliveryChallanItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ deliveryChallanId, itemId }: DeleteDeliveryChallanItemVariables) =>
      deliveryChallanItemService.deleteDeliveryChallanItem(deliveryChallanId, itemId),
    onSuccess: (_data, { deliveryChallanId }) => {
      queryClient.invalidateQueries({ queryKey: deliveryChallanItemKeys.byChallan(deliveryChallanId) });
    },
  });
}
