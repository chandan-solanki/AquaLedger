"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { deliveryChallanItemKeys } from "@/features/delivery-challans/constants/query-keys";
import { deliveryChallanItemService } from "@/features/delivery-challans/services/delivery-challan-item-service";
import type { DeliveryChallanItemUpdateRequest } from "@/features/delivery-challans/types/delivery-challan-item";

export interface UpdateDeliveryChallanItemVariables {
  deliveryChallanId: string;
  itemId: string;
  payload: DeliveryChallanItemUpdateRequest;
}

/** Same invalidation shape as `useCreateDeliveryChallanItem`. */
export function useUpdateDeliveryChallanItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ deliveryChallanId, itemId, payload }: UpdateDeliveryChallanItemVariables) =>
      deliveryChallanItemService.updateDeliveryChallanItem(deliveryChallanId, itemId, payload),
    onSuccess: (_item, { deliveryChallanId }) => {
      queryClient.invalidateQueries({ queryKey: deliveryChallanItemKeys.byChallan(deliveryChallanId) });
    },
  });
}
