"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { invoiceKeys } from "@/features/invoices/constants/query-keys";
import { invoiceService } from "@/features/invoices/services/invoice-service";
import type { InvoiceUpdateRequest } from "@/features/invoices/types/invoice";

export interface UpdateInvoiceVariables {
  id: string;
  payload: InvoiceUpdateRequest;
}

export function useUpdateInvoice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: UpdateInvoiceVariables) => invoiceService.updateInvoice(id, payload),
    onSuccess: (invoice) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(invoice.id) });
    },
  });
}
