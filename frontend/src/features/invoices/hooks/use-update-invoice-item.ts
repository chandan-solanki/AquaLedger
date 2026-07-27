"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { invoiceItemKeys, invoiceKeys } from "@/features/invoices/constants/query-keys";
import { invoiceItemService } from "@/features/invoices/services/invoice-item-service";
import type { InvoiceItemUpdateRequest } from "@/features/invoices/types/invoice-item";

export interface UpdateInvoiceItemVariables {
  invoiceId: string;
  itemId: string;
  payload: InvoiceItemUpdateRequest;
}

/** Same invalidation shape as `useCreateInvoiceItem` - updating an item also recalculates the parent invoice's totals. */
export function useUpdateInvoiceItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ invoiceId, itemId, payload }: UpdateInvoiceItemVariables) =>
      invoiceItemService.updateInvoiceItem(invoiceId, itemId, payload),
    onSuccess: (_item, { invoiceId }) => {
      queryClient.invalidateQueries({ queryKey: invoiceItemKeys.byInvoice(invoiceId) });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(invoiceId) });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() });
    },
  });
}
