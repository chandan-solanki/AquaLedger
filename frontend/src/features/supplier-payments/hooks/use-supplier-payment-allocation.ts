"use client";

import { useQuery } from "@tanstack/react-query";

import { supplierPaymentAllocationKeys } from "@/features/supplier-payments/constants/query-keys";
import { supplierPaymentAllocationService } from "@/features/supplier-payments/services/supplier-payment-allocation-service";

/**
 * A single allocation, derived from the same list query
 * `useSupplierPaymentAllocations` reads (`GET /supplier-payments/
 * {supplier_payment_id}/allocations`) - the backend exposes no single-
 * allocation GET endpoint (only list/create/update/delete, see
 * app/modules/supplier_payments/router.py), so this shares that hook's
 * exact queryKey/queryFn (TanStack Query dedupes the request rather than
 * issuing a second one) and selects one row by id, rather than inventing an
 * endpoint that doesn't exist, mirroring `usePaymentAllocation`. Used by
 * `SupplierPaymentAllocationTable` to populate the Edit dialog from the
 * freshest cached list data for the row the user clicked.
 */
export function useSupplierPaymentAllocation(
  supplierPaymentId: string | undefined,
  allocationId: string | undefined
) {
  return useQuery({
    queryKey: supplierPaymentAllocationKeys.byPayment(supplierPaymentId ?? ""),
    queryFn: () =>
      supplierPaymentAllocationService.listSupplierPaymentAllocations(supplierPaymentId as string),
    enabled: Boolean(supplierPaymentId),
    select: (allocations) => allocations.find((allocation) => allocation.id === allocationId),
  });
}
