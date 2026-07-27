"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { invoiceKeys } from "@/features/invoices/constants/query-keys";
import { invoiceService } from "@/features/invoices/services/invoice-service";
import type { InvoiceCreateRequest } from "@/features/invoices/types/invoice";

export function useCreateInvoice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: InvoiceCreateRequest) => invoiceService.createInvoice(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() });
    },
  });
}
