"use client";

import { useQuery } from "@tanstack/react-query";

import { paymentAllocationKeys } from "@/features/payments/constants/query-keys";
import { paymentAllocationService } from "@/features/payments/services/payment-allocation-service";

/**
 * Every allocation on one payment - disabled until a payment id is
 * available. No pagination (`GET /payments/{id}/allocations` returns a
 * plain array - see `payment-allocation-service.ts`), so the Payment Detail
 * page's Allocations section fetches and renders the whole set at once,
 * mirroring `useInvoiceItems`.
 */
export function usePaymentAllocations(paymentId: string | undefined) {
  return useQuery({
    queryKey: paymentAllocationKeys.byPayment(paymentId ?? ""),
    queryFn: () => paymentAllocationService.listPaymentAllocations(paymentId as string),
    enabled: Boolean(paymentId),
  });
}
