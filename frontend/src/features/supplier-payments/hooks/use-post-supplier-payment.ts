"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { supplierPaymentKeys } from "@/features/supplier-payments/constants/query-keys";
import { supplierPaymentService } from "@/features/supplier-payments/services/supplier-payment-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Post is the supplier payment module's one true business transaction
 * (app/modules/supplier_payments/service.py's `SupplierPaymentService.post`):
 * `draft` -> `posted`, irreversible. Inside one transaction, the backend
 * locks the payment row, recalculates `allocated_amount`/`unallocated_amount`
 * from its current allocations (defensive - already correct from every prior
 * allocation mutation), verifies the totals are internally consistent, then
 * assigns a sequential `payment_number` and stamps `posted_at` - nothing is
 * computed here, only invalidated, so the next read shows the server's own
 * numbers.
 *
 * Unlike Purchase Bill's `post` (which increases the billing supplier's
 * `outstanding_amount`), posting a supplier payment does NOT touch any
 * PurchaseBill or Supplier field - the docstring on
 * `SupplierPaymentService.post` is explicit that Session 4's outstanding
 * engine already kept those correct as of every allocation create/update/
 * delete made while this payment was draft - so invalidation stays scoped to
 * this payment's own queries, mirroring `usePostPayment` exactly. The
 * allocation rows themselves are not created/changed/removed by posting
 * either, so `supplierPaymentAllocationKeys` is not invalidated - the
 * Allocation table's own CRUD gating reacts to the payment's `status`, which
 * `supplierPaymentKeys.detail` invalidation already refreshes.
 */
export function usePostSupplierPayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => supplierPaymentService.postSupplierPayment(id),
    onSuccess: (payment) => {
      queryClient.invalidateQueries({ queryKey: supplierPaymentKeys.detail(payment.id) });
      queryClient.invalidateQueries({ queryKey: supplierPaymentKeys.lists() });
      toastSuccess(payment.paymentNumber ? `${payment.paymentNumber} posted.` : "Supplier payment posted.");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
