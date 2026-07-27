"use client";

import { useQuery } from "@tanstack/react-query";

import { invoiceItemKeys } from "@/features/invoices/constants/query-keys";
import { invoiceItemService } from "@/features/invoices/services/invoice-item-service";

/**
 * Every non-deleted line item on one invoice - disabled until an invoice id
 * is available. No pagination (`GET /invoices/{id}/items` returns a plain
 * array - see `invoice-item-service.ts`), so the Invoice Detail page's
 * Items section fetches and renders the whole set at once, mirroring
 * `useTripCatches`.
 */
export function useInvoiceItems(invoiceId: string | undefined) {
  return useQuery({
    queryKey: invoiceItemKeys.byInvoice(invoiceId ?? ""),
    queryFn: () => invoiceItemService.listInvoiceItems(invoiceId as string),
    enabled: Boolean(invoiceId),
  });
}
