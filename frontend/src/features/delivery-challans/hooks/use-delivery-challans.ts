"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { deliveryChallanKeys } from "@/features/delivery-challans/constants/query-keys";
import type { DeliveryChallanFilters } from "@/features/delivery-challans/schemas/delivery-challan-filters";
import { toDeliveryChallanListParams } from "@/features/delivery-challans/schemas/delivery-challan-filters";
import { deliveryChallanService } from "@/features/delivery-challans/services/delivery-challan-service";

/**
 * Server-side, paginated delivery challans list - every filter/sort/page
 * change refetches from the backend rather than filtering an already-loaded
 * page client-side, mirroring `usePurchaseOrders`. `keepPreviousData` keeps
 * the current rows on screen (instead of flashing to a loading state) while
 * a filter/page change is in flight.
 */
export function useDeliveryChallans(filters: DeliveryChallanFilters) {
  const params = toDeliveryChallanListParams(filters);

  return useQuery({
    queryKey: deliveryChallanKeys.list(params),
    queryFn: () => deliveryChallanService.listDeliveryChallans(params),
    placeholderData: keepPreviousData,
  });
}
