"use client";

import { useQuery } from "@tanstack/react-query";

import { invoiceService } from "@/features/invoices/services/invoice-service";

/**
 * Sprint 15 Session 7: batched invoice-usage counts for the Fish Stock
 * detail page's Contributing Catches table - one query for every trip catch
 * shown on that page, never one request per row (N+1). Disabled while
 * `tripCatchIds` is empty (nothing to ask about yet, or the fish has no
 * contributing catches).
 */
export function useTripCatchInvoiceUsageSummary(tripCatchIds: string[]) {
  return useQuery({
    queryKey: ["trip-catches", "invoice-usage-summary", [...tripCatchIds].sort()],
    queryFn: () => invoiceService.getTripCatchInvoiceUsageSummary(tripCatchIds),
    enabled: tripCatchIds.length > 0,
  });
}
