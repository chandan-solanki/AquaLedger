"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { paymentKeys } from "@/features/payments/constants/query-keys";
import { paymentService } from "@/features/payments/services/payment-service";
import type { PaymentCreateRequest } from "@/features/payments/types/payment";

export function useCreatePayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: PaymentCreateRequest) => paymentService.createPayment(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: paymentKeys.lists() });
    },
  });
}
