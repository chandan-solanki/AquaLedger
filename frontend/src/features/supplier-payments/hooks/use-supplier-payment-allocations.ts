"use client";

import { useQuery } from "@tanstack/react-query";

import { supplierPaymentAllocationKeys } from "@/features/supplier-payments/constants/query-keys";
import { supplierPaymentAllocationService } from "@/features/supplier-payments/services/supplier-payment-allocation-service";

/**
 * Every allocation on one supplier payment - disabled until a supplier
 * payment id is available. No pagination (`GET /supplier-payments/{id}/
 * allocations` returns a plain array - see
 * `supplier-payment-allocation-service.ts`), so the Detail page's
 * Allocations section fetches and renders the whole set at once, mirroring
 * `usePaymentAllocations`.
 */
export function useSupplierPaymentAllocations(supplierPaymentId: string | undefined) {
  return useQuery({
    queryKey: supplierPaymentAllocationKeys.byPayment(supplierPaymentId ?? ""),
    queryFn: () =>
      supplierPaymentAllocationService.listSupplierPaymentAllocations(supplierPaymentId as string),
    enabled: Boolean(supplierPaymentId),
  });
}
