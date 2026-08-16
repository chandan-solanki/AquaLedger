"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { deliveryChallanKeys } from "@/features/delivery-challans/constants/query-keys";
import { deliveryChallanService } from "@/features/delivery-challans/services/delivery-challan-service";
import type { DeliveryChallanUpdateRequest } from "@/features/delivery-challans/types/delivery-challan";

export interface UpdateDeliveryChallanVariables {
  id: string;
  payload: DeliveryChallanUpdateRequest;
}

export function useUpdateDeliveryChallan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: UpdateDeliveryChallanVariables) =>
      deliveryChallanService.updateDeliveryChallan(id, payload),
    onSuccess: (challan) => {
      queryClient.invalidateQueries({ queryKey: deliveryChallanKeys.lists() });
      queryClient.invalidateQueries({ queryKey: deliveryChallanKeys.detail(challan.id) });
    },
  });
}
