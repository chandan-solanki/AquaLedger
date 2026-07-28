"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { paymentKeys } from "@/features/payments/constants/query-keys";
import type { PaymentFilters } from "@/features/payments/schemas/payment-filters";
import { toPaymentListParams } from "@/features/payments/schemas/payment-filters";
import { paymentService } from "@/features/payments/services/payment-service";

/**
 * Server-side, paginated payment list - every filter/sort/page change
 * refetches from the backend rather than filtering an already-loaded page
 * client-side, mirroring `useInvoices`. `keepPreviousData` keeps the current
 * rows on screen (instead of flashing to a loading state) while a
 * filter/page change is in flight.
 */
export function usePayments(filters: PaymentFilters) {
  const params = toPaymentListParams(filters);

  return useQuery({
    queryKey: paymentKeys.list(params),
    queryFn: () => paymentService.listPayments(params),
    placeholderData: keepPreviousData,
  });
}
