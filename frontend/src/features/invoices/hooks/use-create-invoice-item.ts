"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { invoiceItemKeys, invoiceKeys } from "@/features/invoices/constants/query-keys";
import { invoiceItemService } from "@/features/invoices/services/invoice-item-service";
import type { InvoiceItemCreateRequest } from "@/features/invoices/types/invoice-item";

export interface CreateInvoiceItemVariables {
  invoiceId: string;
  payload: InvoiceItemCreateRequest;
}

/**
 * Adding an item recalculates the parent invoice's own totals server-side
 * (InvoiceService.add_item -> _recalculate_invoice, app/modules/invoices/service.py),
 * so both this invoice's item list AND its detail query are invalidated -
 * the invoice List page's Total/Balance Amount columns are invalidated too,
 * since they'd otherwise go stale. Never patched optimistically, per the
 * "server as source of truth" principle for financial figures.
 */
export function useCreateInvoiceItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ invoiceId, payload }: CreateInvoiceItemVariables) =>
      invoiceItemService.createInvoiceItem(invoiceId, payload),
    onSuccess: (_item, { invoiceId }) => {
      queryClient.invalidateQueries({ queryKey: invoiceItemKeys.byInvoice(invoiceId) });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(invoiceId) });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() });
    },
  });
}
