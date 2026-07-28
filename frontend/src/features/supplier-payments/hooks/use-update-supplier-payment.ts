"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { supplierPaymentKeys } from "@/features/supplier-payments/constants/query-keys";
import { supplierPaymentService } from "@/features/supplier-payments/services/supplier-payment-service";
import type { SupplierPaymentUpdateRequest } from "@/features/supplier-payments/types/supplier-payment";

export interface UpdateSupplierPaymentVariables {
  id: string;
  payload: SupplierPaymentUpdateRequest;
}

export function useUpdateSupplierPayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: UpdateSupplierPaymentVariables) =>
      supplierPaymentService.updateSupplierPayment(id, payload),
    onSuccess: (payment) => {
      queryClient.invalidateQueries({ queryKey: supplierPaymentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: supplierPaymentKeys.detail(payment.id) });
    },
  });
}
