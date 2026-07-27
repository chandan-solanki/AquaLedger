"use client";

import { useQuery } from "@tanstack/react-query";

import { invoiceItemKeys } from "@/features/invoices/constants/query-keys";
import { invoiceItemService } from "@/features/invoices/services/invoice-item-service";

/**
 * A single line item, derived from the same list query `useInvoiceItems`
 * reads (`GET /invoices/{invoice_id}/items`) - the backend exposes no
 * single-item GET endpoint (only list/create/update/delete, see
 * app/modules/invoices/router.py), so this shares `useInvoiceItems`'s exact
 * queryKey/queryFn (TanStack Query dedupes the request rather than issuing
 * a second one) and selects one row by id, rather than inventing an
 * endpoint that doesn't exist. Used by `InvoiceItemTable` to populate the
 * Edit dialog from the freshest cached list data for the row the user
 * clicked.
 */
export function useInvoiceItem(invoiceId: string | undefined, itemId: string | undefined) {
  return useQuery({
    queryKey: invoiceItemKeys.byInvoice(invoiceId ?? ""),
    queryFn: () => invoiceItemService.listInvoiceItems(invoiceId as string),
    enabled: Boolean(invoiceId),
    select: (items) => items.find((item) => item.id === itemId),
  });
}
