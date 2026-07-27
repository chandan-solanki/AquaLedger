"use client";

import { useQuery } from "@tanstack/react-query";

import { invoiceKeys } from "@/features/invoices/constants/query-keys";
import { invoiceService } from "@/features/invoices/services/invoice-service";

/**
 * A single invoice by id, for a future Detail page — not yet consumed by any
 * page this session (see TASKS.md), but part of the foundation's BFF/service
 * contract (`GET /api/invoices/{id}`) alongside the List page's `useInvoices`.
 */
export function useInvoice(id: string) {
  return useQuery({
    queryKey: invoiceKeys.detail(id),
    queryFn: () => invoiceService.getInvoice(id),
    enabled: Boolean(id),
  });
}
