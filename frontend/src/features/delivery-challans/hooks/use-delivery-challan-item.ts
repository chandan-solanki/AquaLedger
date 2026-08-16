"use client";

import { useQuery } from "@tanstack/react-query";

import { deliveryChallanItemKeys } from "@/features/delivery-challans/constants/query-keys";
import { deliveryChallanItemService } from "@/features/delivery-challans/services/delivery-challan-item-service";

/**
 * A single line item, derived from the same list query
 * `useDeliveryChallanItems` reads (`GET /delivery-challans/{id}/items`) -
 * the backend exposes no single-item GET endpoint (only list/create/update/
 * delete), so this shares that hook's exact queryKey/queryFn (TanStack
 * Query dedupes the request rather than issuing a second one) and selects
 * one row by id, mirroring `usePurchaseOrderItem`.
 */
export function useDeliveryChallanItem(deliveryChallanId: string | undefined, itemId: string | undefined) {
  return useQuery({
    queryKey: deliveryChallanItemKeys.byChallan(deliveryChallanId ?? ""),
    queryFn: () => deliveryChallanItemService.listDeliveryChallanItems(deliveryChallanId as string),
    enabled: Boolean(deliveryChallanId),
    select: (items) => items.find((item) => item.id === itemId),
  });
}
