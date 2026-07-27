"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { invoiceItemKeys, invoiceKeys } from "@/features/invoices/constants/query-keys";
import { invoiceItemService } from "@/features/invoices/services/invoice-item-service";

export interface DeleteInvoiceItemVariables {
  invoiceId: string;
  itemId: string;
}

/** Same invalidation shape as `useCreateInvoiceItem` - deleting an item also recalculates the parent invoice's totals from the remaining items. */
export function useDeleteInvoiceItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ invoiceId, itemId }: DeleteInvoiceItemVariables) =>
      invoiceItemService.deleteInvoiceItem(invoiceId, itemId),
    onSuccess: (_data, { invoiceId }) => {
      queryClient.invalidateQueries({ queryKey: invoiceItemKeys.byInvoice(invoiceId) });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(invoiceId) });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() });
    },
  });
}
