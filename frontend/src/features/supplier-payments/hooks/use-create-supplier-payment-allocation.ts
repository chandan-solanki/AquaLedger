"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { supplierPaymentAllocationKeys, supplierPaymentKeys } from "@/features/supplier-payments/constants/query-keys";
import { purchaseBillKeys } from "@/features/purchase-bills";
import { supplierPaymentAllocationService } from "@/features/supplier-payments/services/supplier-payment-allocation-service";
import type { SupplierPaymentAllocationCreateRequest } from "@/features/supplier-payments/types/supplier-payment-allocation";

export interface CreateSupplierPaymentAllocationVariables {
  supplierPaymentId: string;
  payload: SupplierPaymentAllocationCreateRequest;
}

/**
 * Creating an allocation recalculates the parent supplier payment's own
 * allocated_amount/unallocated_amount, and the target purchase bill's
 * paid_amount/balance_amount/status (and that bill's supplier's
 * outstanding_amount), server-side in one transaction
 * (SupplierPaymentService.create_allocation ->
 * _recalculate_supplier_payment_allocation_totals +
 * _recalculate_purchase_bill_and_supplier, app/modules/supplier_payments/
 * service.py) - so this payment's allocation list, its own detail query,
 * and the target purchase bill's detail query are all invalidated, mirroring
 * `useCreatePaymentAllocation`. There is no cached supplier-detail query to
 * invalidate here (unlike `useCreatePaymentAllocation`'s `companyKeys.detail`)
 * - this feature only ever caches supplier id/name pairs
 * (`useSupplierOptions`), never a supplier's `outstanding_amount`. Never
 * patched optimistically, per the "server as source of truth" principle for
 * financial figures.
 */
export function useCreateSupplierPaymentAllocation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ supplierPaymentId, payload }: CreateSupplierPaymentAllocationVariables) =>
      supplierPaymentAllocationService.createSupplierPaymentAllocation(supplierPaymentId, payload),
    onSuccess: (allocation, { supplierPaymentId }) => {
      queryClient.invalidateQueries({
        queryKey: supplierPaymentAllocationKeys.byPayment(supplierPaymentId),
      });
      queryClient.invalidateQueries({ queryKey: supplierPaymentKeys.detail(supplierPaymentId) });
      queryClient.invalidateQueries({ queryKey: purchaseBillKeys.detail(allocation.purchaseBillId) });
    },
  });
}
