"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { paymentAllocationKeys, paymentKeys } from "@/features/payments/constants/query-keys";
import { paymentService } from "@/features/payments/services/payment-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Owns the full delete outcome (cache invalidation, toast, navigation) so
 * every call site - the Detail page's Delete action and the List page's row
 * action - gets identical behavior, mirroring `useDeleteInvoice` exactly.
 * Only `draft` payments may be deleted (409 `PAYMENT_NOT_DRAFT` otherwise,
 * app/modules/payments/service.py's `_ensure_draft`) - a draft payment has
 * never been posted, so it has never touched a payment_number sequence;
 * whatever allocations it had are left as-is by the backend's own
 * `delete()` (only `deleted_at`/`deleted_by` are set - see that method's
 * docstring), so nothing beyond this payment's own queries needs
 * invalidating.
 */
export function useDeletePayment() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (id: string) => paymentService.deletePayment(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: paymentKeys.lists() });
      queryClient.removeQueries({ queryKey: paymentKeys.detail(id) });
      queryClient.removeQueries({ queryKey: paymentAllocationKeys.byPayment(id) });
      toastSuccess("Payment deleted.");
      router.push("/payments");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
