"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { deliveryChallanItemKeys } from "@/features/delivery-challans/constants/query-keys";
import { deliveryChallanItemService } from "@/features/delivery-challans/services/delivery-challan-item-service";
import type { DeliveryChallanItemCreateRequest } from "@/features/delivery-challans/types/delivery-challan-item";

export interface CreateDeliveryChallanItemVariables {
  deliveryChallanId: string;
  payload: DeliveryChallanItemCreateRequest;
}

/**
 * Adding an item never recalculates anything on the parent delivery
 * challan's own header - unlike `useCreatePurchaseOrderItem`, there are no
 * totals to keep in sync (a delivery challan carries no financial fields at
 * all) - so only this challan's own items query is invalidated. That same
 * query backs `useInvoiceDeliverySummary`'s per-invoice-item delivered/
 * remaining computation for this challan's linked invoice, so the Item Add
 * dialog's own "remaining" hints refresh automatically on the next read.
 */
export function useCreateDeliveryChallanItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ deliveryChallanId, payload }: CreateDeliveryChallanItemVariables) =>
      deliveryChallanItemService.createDeliveryChallanItem(deliveryChallanId, payload),
    onSuccess: (_item, { deliveryChallanId }) => {
      queryClient.invalidateQueries({ queryKey: deliveryChallanItemKeys.byChallan(deliveryChallanId) });
    },
  });
}
