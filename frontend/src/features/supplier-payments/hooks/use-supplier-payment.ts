"use client";

import { useQuery } from "@tanstack/react-query";

import { supplierPaymentKeys } from "@/features/supplier-payments/constants/query-keys";
import { supplierPaymentService } from "@/features/supplier-payments/services/supplier-payment-service";

/**
 * A single supplier payment by id (`GET /api/supplier-payments/{id}`) -
 * foundation for the Detail page a later session adds, mirroring
 * `usePayment` exactly.
 */
export function useSupplierPayment(id: string) {
  return useQuery({
    queryKey: supplierPaymentKeys.detail(id),
    queryFn: () => supplierPaymentService.getSupplierPayment(id),
    enabled: Boolean(id),
  });
}
