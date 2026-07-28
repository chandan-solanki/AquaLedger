"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { supplierPaymentAllocationKeys, supplierPaymentKeys } from "@/features/supplier-payments/constants/query-keys";
import { purchaseBillKeys } from "@/features/purchase-bills";
import { supplierPaymentAllocationService } from "@/features/supplier-payments/services/supplier-payment-allocation-service";
import type { SupplierPaymentAllocationUpdateRequest } from "@/features/supplier-payments/types/supplier-payment-allocation";

export interface UpdateSupplierPaymentAllocationVariables {
  supplierPaymentId: string;
  allocationId: string;
  payload: SupplierPaymentAllocationUpdateRequest;
  /** The purchase bill this allocation targeted before the update - needed for invalidation even when `payload.purchase_bill_id` is absent (unchanged). */
  previousPurchaseBillId: string;
}

/**
 * Same cascade as `useCreateSupplierPaymentAllocation` - updating an
 * allocation recalculates the parent supplier payment's totals and the
 * target purchase bill's paid_amount/balance_amount/status (and its
 * supplier's outstanding_amount) from source, every time, even when the
 * allocation's `purchase_bill_id` is left unchanged (only `allocated_amount`
 * moved) - so `previousPurchaseBillId` is always invalidated. If the
 * allocation was retargeted onto a different bill,
 * `SupplierPaymentService.update_allocation` recalculates *both* bills (the
 * old one loses the allocation, the new one gains it), so the new bill
 * (from the response) is invalidated too when it differs, mirroring
 * `useUpdatePaymentAllocation`.
 */
export function useUpdateSupplierPaymentAllocation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      supplierPaymentId,
      allocationId,
      payload,
    }: UpdateSupplierPaymentAllocationVariables) =>
      supplierPaymentAllocationService.updateSupplierPaymentAllocation(
        supplierPaymentId,
        allocationId,
        payload
      ),
    onSuccess: (allocation, { supplierPaymentId, previousPurchaseBillId }) => {
      queryClient.invalidateQueries({
        queryKey: supplierPaymentAllocationKeys.byPayment(supplierPaymentId),
      });
      queryClient.invalidateQueries({ queryKey: supplierPaymentKeys.detail(supplierPaymentId) });

      queryClient.invalidateQueries({ queryKey: purchaseBillKeys.detail(previousPurchaseBillId) });
      if (allocation.purchaseBillId !== previousPurchaseBillId) {
        queryClient.invalidateQueries({ queryKey: purchaseBillKeys.detail(allocation.purchaseBillId) });
      }
    },
  });
}
