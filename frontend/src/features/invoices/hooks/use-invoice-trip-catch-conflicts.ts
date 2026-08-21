"use client";

import { useQuery } from "@tanstack/react-query";

import { invoiceService } from "@/features/invoices/services/invoice-service";

/**
 * Sprint 15 Session 8: one page-level fetch of "Other Invoice Usage" for
 * every trip catch this invoice's own items reference - never one request
 * per item row (the N+1 this session's spec explicitly forbids). Disabled
 * while `invoiceId` is empty (mirrors `useInvoice`).
 */
export function useInvoiceTripCatchConflicts(invoiceId: string) {
  return useQuery({
    queryKey: ["invoices", invoiceId, "trip-catch-conflicts"],
    queryFn: () => invoiceService.getInvoiceTripCatchConflicts(invoiceId),
    enabled: Boolean(invoiceId),
  });
}
