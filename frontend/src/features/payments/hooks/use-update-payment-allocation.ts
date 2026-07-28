"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { companyKeys } from "@/features/companies";
import { invoiceKeys } from "@/features/invoices";
import type { Invoice } from "@/features/invoices";
import { paymentAllocationKeys, paymentKeys } from "@/features/payments/constants/query-keys";
import { paymentAllocationService } from "@/features/payments/services/payment-allocation-service";
import type { PaymentAllocationUpdateRequest } from "@/features/payments/types/payment-allocation";

export interface UpdatePaymentAllocationVariables {
  paymentId: string;
  allocationId: string;
  payload: PaymentAllocationUpdateRequest;
  /** The invoice this allocation targeted before the update - needed for invalidation even when `payload.invoice_id` is absent (unchanged). */
  previousInvoiceId: string;
}

/**
 * Same cascade as `useCreatePaymentAllocation` - updating an allocation
 * recalculates the parent payment's totals and the target invoice's
 * paid_amount/balance_amount/status (and its billed company's
 * outstanding_amount) from source, every time, even when the allocation's
 * `invoice_id` is left unchanged (only `allocated_amount` moved) - so
 * `previousInvoiceId` is always invalidated. If the allocation was
 * retargeted onto a different invoice, `PaymentService.update_allocation`
 * recalculates *both* invoices (the old one loses the allocation, the new
 * one gains it), so the new invoice (from the response) is invalidated too
 * when it differs.
 */
export function useUpdatePaymentAllocation() {
  const queryClient = useQueryClient();

  function invalidateInvoiceAndCompany(invoiceId: string) {
    queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(invoiceId) });
    const invoice = queryClient.getQueryData<Invoice>(invoiceKeys.detail(invoiceId));
    if (invoice) {
      queryClient.invalidateQueries({ queryKey: companyKeys.detail(invoice.companyId) });
    }
  }

  return useMutation({
    mutationFn: ({ paymentId, allocationId, payload }: UpdatePaymentAllocationVariables) =>
      paymentAllocationService.updatePaymentAllocation(paymentId, allocationId, payload),
    onSuccess: (allocation, { paymentId, previousInvoiceId }) => {
      queryClient.invalidateQueries({ queryKey: paymentAllocationKeys.byPayment(paymentId) });
      queryClient.invalidateQueries({ queryKey: paymentKeys.detail(paymentId) });

      invalidateInvoiceAndCompany(previousInvoiceId);
      if (allocation.invoiceId !== previousInvoiceId) {
        invalidateInvoiceAndCompany(allocation.invoiceId);
      }
    },
  });
}
