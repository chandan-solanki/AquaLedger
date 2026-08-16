"use client";

import { useQuery } from "@tanstack/react-query";

import { deliveryChallanItemKeys } from "@/features/delivery-challans/constants/query-keys";
import { deliveryChallanItemService } from "@/features/delivery-challans/services/delivery-challan-item-service";

/**
 * Every line item on one delivery challan - disabled until a delivery
 * challan id is available. No pagination (`GET /delivery-challans/{id}/items`
 * returns a plain array), so the Detail page's Items section fetches and
 * renders the whole set at once, mirroring `usePurchaseOrderItems`.
 */
export function useDeliveryChallanItems(deliveryChallanId: string | undefined) {
  return useQuery({
    queryKey: deliveryChallanItemKeys.byChallan(deliveryChallanId ?? ""),
    queryFn: () => deliveryChallanItemService.listDeliveryChallanItems(deliveryChallanId as string),
    enabled: Boolean(deliveryChallanId),
  });
}
