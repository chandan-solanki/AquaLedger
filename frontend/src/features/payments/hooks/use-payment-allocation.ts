"use client";

import { useQuery } from "@tanstack/react-query";

import { paymentAllocationKeys } from "@/features/payments/constants/query-keys";
import { paymentAllocationService } from "@/features/payments/services/payment-allocation-service";

/**
 * A single allocation, derived from the same list query
 * `usePaymentAllocations` reads (`GET /payments/{payment_id}/allocations`) -
 * the backend exposes no single-allocation GET endpoint (only list/create/
 * update/delete, see app/modules/payments/router.py), so this shares
 * `usePaymentAllocations`'s exact queryKey/queryFn (TanStack Query dedupes
 * the request rather than issuing a second one) and selects one row by id,
 * rather than inventing an endpoint that doesn't exist, mirroring
 * `useInvoiceItem`. Used by `PaymentAllocationTable` to populate the Edit
 * dialog from the freshest cached list data for the row the user clicked.
 */
export function usePaymentAllocation(paymentId: string | undefined, allocationId: string | undefined) {
  return useQuery({
    queryKey: paymentAllocationKeys.byPayment(paymentId ?? ""),
    queryFn: () => paymentAllocationService.listPaymentAllocations(paymentId as string),
    enabled: Boolean(paymentId),
    select: (allocations) => allocations.find((allocation) => allocation.id === allocationId),
  });
}
