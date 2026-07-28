"use client";

import { useQuery } from "@tanstack/react-query";

import { paymentKeys } from "@/features/payments/constants/query-keys";
import { paymentService } from "@/features/payments/services/payment-service";

/**
 * A single payment by id (`GET /api/payments/{id}`) - consumed by
 * `PaymentEditPage` and `PaymentDetailPage`, mirroring `useInvoice` exactly.
 */
export function usePayment(id: string) {
  return useQuery({
    queryKey: paymentKeys.detail(id),
    queryFn: () => paymentService.getPayment(id),
    enabled: Boolean(id),
  });
}
