"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { deliveryChallanKeys } from "@/features/delivery-challans/constants/query-keys";
import { deliveryChallanService } from "@/features/delivery-challans/services/delivery-challan-service";
import type { DeliveryChallanCreateRequest } from "@/features/delivery-challans/types/delivery-challan";

export function useCreateDeliveryChallan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: DeliveryChallanCreateRequest) =>
      deliveryChallanService.createDeliveryChallan(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: deliveryChallanKeys.lists() });
    },
  });
}
