"use client";

import { useMutation } from "@tanstack/react-query";

import { invoiceService } from "@/features/invoices/services/invoice-service";

/**
 * Sprint 15 Session 10: run once, imperatively, right when the user clicks
 * "Issue Invoice" - a `useMutation` rather than a `useQuery` since there is
 * nothing to fetch until that click happens, and a stale cached result would
 * defeat the entire point of a fresh preflight check. Advisory only: never
 * treat a resolved value here as a guarantee the real issue will succeed,
 * and never let a failure here block the user from attempting the real,
 * authoritative issue action (see `InvoiceDetailPage`'s own onError).
 */
export function useInvoiceIssuePreflight() {
  return useMutation({
    mutationFn: (invoiceId: string) => invoiceService.getInvoiceIssuePreflight(invoiceId),
  });
}
