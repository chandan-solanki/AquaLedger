"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { supplierPaymentAllocationKeys, supplierPaymentKeys } from "@/features/supplier-payments/constants/query-keys";
import { purchaseBillKeys } from "@/features/purchase-bills";
import { supplierPaymentAllocationService } from "@/features/supplier-payments/services/supplier-payment-allocation-service";

export interface DeleteSupplierPaymentAllocationVariables {
  supplierPaymentId: string;
  allocationId: string;
  /** The purchase bill the deleted allocation targeted - the DELETE response has no body, so this comes from the row being deleted. */
  purchaseBillId: string;
}

/**
 * Same cascade as `useCreateSupplierPaymentAllocation` - removing an
 * allocation restores its amount to the payment's unallocated_amount and
 * recalculates the target purchase bill's paid_amount/balance_amount/status
 * (and its supplier's outstanding_amount) from the remaining allocations
 * (SupplierPaymentService.delete_allocation, app/modules/supplier_payments/
 * service.py), mirroring `useDeletePaymentAllocation`.
 */
export function useDeleteSupplierPaymentAllocation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ supplierPaymentId, allocationId }: DeleteSupplierPaymentAllocationVariables) =>
      supplierPaymentAllocationService.deleteSupplierPaymentAllocation(
        supplierPaymentId,
        allocationId
      ),
    onSuccess: (_data, { supplierPaymentId, purchaseBillId }) => {
      queryClient.invalidateQueries({
        queryKey: supplierPaymentAllocationKeys.byPayment(supplierPaymentId),
      });
      queryClient.invalidateQueries({ queryKey: supplierPaymentKeys.detail(supplierPaymentId) });
      queryClient.invalidateQueries({ queryKey: purchaseBillKeys.detail(purchaseBillId) });
    },
  });
}
