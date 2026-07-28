"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { companyKeys } from "@/features/companies";
import { invoiceKeys } from "@/features/invoices";
import type { Invoice } from "@/features/invoices";
import { paymentAllocationKeys, paymentKeys } from "@/features/payments/constants/query-keys";
import { paymentAllocationService } from "@/features/payments/services/payment-allocation-service";
import type { PaymentAllocationCreateRequest } from "@/features/payments/types/payment-allocation";

export interface CreatePaymentAllocationVariables {
  paymentId: string;
  payload: PaymentAllocationCreateRequest;
}

/**
 * Creating an allocation recalculates the parent payment's own
 * allocated_amount/unallocated_amount, and the target invoice's
 * paid_amount/balance_amount/status, server-side in one transaction
 * (PaymentService.create_allocation -> _recalculate_payment_allocation_totals
 * + _recalculate_invoice_and_company, app/modules/payments/service.py) - so
 * this payment's allocation list, its own detail query, and the target
 * invoice's detail query are all invalidated. The cascade doesn't stop at
 * the invoice: `_recalculate_invoice_and_company` also recalculates the
 * invoice's billed company's `outstanding_amount`
 * (InvoiceService.recalculate_payment_totals -> CompanyService.recalculate_outstanding)
 * - resolved here from the already-cached `invoiceKeys.detail(invoice_id)`
 * entry (populated by `PaymentAllocationTable`'s own invoice lookup) rather
 * than an extra fetch, so that company's detail is invalidated too whenever
 * it's known. Never patched optimistically, per the "server as source of
 * truth" principle for financial figures.
 */
export function useCreatePaymentAllocation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ paymentId, payload }: CreatePaymentAllocationVariables) =>
      paymentAllocationService.createPaymentAllocation(paymentId, payload),
    onSuccess: (allocation, { paymentId }) => {
      queryClient.invalidateQueries({ queryKey: paymentAllocationKeys.byPayment(paymentId) });
      queryClient.invalidateQueries({ queryKey: paymentKeys.detail(paymentId) });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(allocation.invoiceId) });

      const invoice = queryClient.getQueryData<Invoice>(invoiceKeys.detail(allocation.invoiceId));
      if (invoice) {
        queryClient.invalidateQueries({ queryKey: companyKeys.detail(invoice.companyId) });
      }
    },
  });
}
