"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { companyKeys } from "@/features/companies";
import { invoiceKeys } from "@/features/invoices";
import type { Invoice } from "@/features/invoices";
import { paymentAllocationKeys, paymentKeys } from "@/features/payments/constants/query-keys";
import { paymentAllocationService } from "@/features/payments/services/payment-allocation-service";

export interface DeletePaymentAllocationVariables {
  paymentId: string;
  allocationId: string;
  /** The invoice the deleted allocation targeted - the DELETE response has no body, so this comes from the row being deleted. */
  invoiceId: string;
}

/**
 * Same cascade as `useCreatePaymentAllocation` - removing an allocation
 * restores its amount to the payment's unallocated_amount and recalculates
 * the target invoice's paid_amount/balance_amount/status (and its billed
 * company's outstanding_amount) from the remaining allocations
 * (PaymentService.delete_allocation, app/modules/payments/service.py).
 */
export function useDeletePaymentAllocation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ paymentId, allocationId }: DeletePaymentAllocationVariables) =>
      paymentAllocationService.deletePaymentAllocation(paymentId, allocationId),
    onSuccess: (_data, { paymentId, invoiceId }) => {
      queryClient.invalidateQueries({ queryKey: paymentAllocationKeys.byPayment(paymentId) });
      queryClient.invalidateQueries({ queryKey: paymentKeys.detail(paymentId) });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(invoiceId) });

      const invoice = queryClient.getQueryData<Invoice>(invoiceKeys.detail(invoiceId));
      if (invoice) {
        queryClient.invalidateQueries({ queryKey: companyKeys.detail(invoice.companyId) });
      }
    },
  });
}
