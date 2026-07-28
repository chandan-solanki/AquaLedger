"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { paymentKeys } from "@/features/payments/constants/query-keys";
import { paymentService } from "@/features/payments/services/payment-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Post is the payment module's one true business transaction
 * (app/modules/payments/service.py's `PaymentService.post`): `draft` ->
 * `posted`, irreversible. The backend assigns `payment_number` and
 * recomputes `allocated_amount`/`unallocated_amount` from the payment's
 * current allocations, all inside one transaction - nothing is computed
 * here, only invalidated, so the next read shows the server's own numbers.
 *
 * Unlike Invoice's `issue` (which increases a company's `outstanding_amount`
 * and deducts trip catch inventory), posting a payment does NOT touch any
 * Invoice or Company field - the Session 4 outstanding engine already kept
 * those correct as of every allocation create/update/delete made while this
 * payment was draft (see the service method's own docstring) - so
 * invalidation stays scoped to this payment's own queries, unlike
 * `useIssueInvoice`'s wider reach into `companyKeys`/`tripCatchKeys`.
 */
export function usePostPayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => paymentService.postPayment(id),
    onSuccess: (payment) => {
      queryClient.invalidateQueries({ queryKey: paymentKeys.detail(payment.id) });
      queryClient.invalidateQueries({ queryKey: paymentKeys.lists() });
      toastSuccess(payment.paymentNumber ? `${payment.paymentNumber} posted.` : "Payment posted.");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
