"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { supplierPaymentAllocationKeys, supplierPaymentKeys } from "@/features/supplier-payments/constants/query-keys";
import { supplierPaymentService } from "@/features/supplier-payments/services/supplier-payment-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Owns the full delete outcome (cache invalidation, toast, navigation) so
 * every call site - the Detail page's Delete action and the List page's row
 * action - gets identical behavior, mirroring `useDeletePayment` exactly.
 * Only `draft` supplier payments may be deleted (409
 * `SUPPLIER_PAYMENT_NOT_DRAFT` otherwise,
 * app/modules/supplier_payments/service.py's `_ensure_draft`) - a draft
 * payment has never been posted, so it has never touched a payment_number
 * sequence. The backend's `delete()` only sets `deleted_at`/`deleted_by` on
 * the payment row itself - it does not touch, recalculate, or cascade into
 * this payment's own allocations, any purchase bill, or any supplier (no
 * such call appears in `SupplierPaymentService.delete`), so nothing beyond
 * this payment's own queries needs invalidating.
 */
export function useDeleteSupplierPayment() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (id: string) => supplierPaymentService.deleteSupplierPayment(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: supplierPaymentKeys.lists() });
      queryClient.removeQueries({ queryKey: supplierPaymentKeys.detail(id) });
      queryClient.removeQueries({ queryKey: supplierPaymentAllocationKeys.byPayment(id) });
      toastSuccess("Supplier payment deleted.");
      router.push("/supplier-payments");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
