"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { paymentKeys } from "@/features/payments/constants/query-keys";
import { paymentService } from "@/features/payments/services/payment-service";
import type { PaymentUpdateRequest } from "@/features/payments/types/payment";

export interface UpdatePaymentVariables {
  id: string;
  payload: PaymentUpdateRequest;
}

export function useUpdatePayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: UpdatePaymentVariables) => paymentService.updatePayment(id, payload),
    onSuccess: (payment) => {
      queryClient.invalidateQueries({ queryKey: paymentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: paymentKeys.detail(payment.id) });
    },
  });
}
