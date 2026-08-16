"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { deliveryChallanKeys } from "@/features/delivery-challans/constants/query-keys";
import { deliveryChallanService } from "@/features/delivery-challans/services/delivery-challan-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * `draft`|`dispatched` -> `cancelled`. No side effects on any other module -
 * a cancelled delivery challan never affected customer outstanding/invoice
 * balance/ledger in the first place, so there is nothing to reverse. Its
 * items immediately stop counting toward any invoice item's delivered
 * quantity (app/modules/delivery_challans/repository.py's
 * `sum_delivered_by_invoice_items` excludes CANCELLED), freeing that
 * quantity for other delivery challans against the same invoice item -
 * invalidating this challan's own queries here is enough for that to show
 * up the next time an invoice's delivery summary is read, since that
 * summary is always computed fresh from each relevant challan's own items
 * query, never cached separately.
 */
export function useCancelDeliveryChallan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deliveryChallanService.cancelDeliveryChallan(id),
    onSuccess: (challan) => {
      queryClient.invalidateQueries({ queryKey: deliveryChallanKeys.detail(challan.id) });
      queryClient.invalidateQueries({ queryKey: deliveryChallanKeys.lists() });
      toastSuccess("Delivery challan cancelled.");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
