"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { supplierPaymentKeys } from "@/features/supplier-payments/constants/query-keys";
import { supplierPaymentService } from "@/features/supplier-payments/services/supplier-payment-service";
import type { SupplierPaymentCreateRequest } from "@/features/supplier-payments/types/supplier-payment";

export function useCreateSupplierPayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: SupplierPaymentCreateRequest) =>
      supplierPaymentService.createSupplierPayment(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: supplierPaymentKeys.lists() });
    },
  });
}
