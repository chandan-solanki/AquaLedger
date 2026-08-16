"use client";

import { useQuery } from "@tanstack/react-query";

import { deliveryChallanKeys } from "@/features/delivery-challans/constants/query-keys";
import { deliveryChallanService } from "@/features/delivery-challans/services/delivery-challan-service";

/** A single delivery challan by id - disabled until an id is available. */
export function useDeliveryChallan(id: string | undefined) {
  return useQuery({
    queryKey: deliveryChallanKeys.detail(id ?? ""),
    queryFn: () => deliveryChallanService.getDeliveryChallan(id as string),
    enabled: Boolean(id),
  });
}
