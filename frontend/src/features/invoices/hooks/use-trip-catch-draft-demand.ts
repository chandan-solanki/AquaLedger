"use client";

import { useQuery } from "@tanstack/react-query";

import { invoiceService } from "@/features/invoices/services/invoice-service";

/**
 * Sprint 15 Session 5: "how much of this trip catch do OTHER draft invoices
 * currently want" - purely informational, never a stock reservation (see
 * `invoiceService.getTripCatchDraftDemand`). `excludeInvoiceId` should
 * always be the invoice currently being created/edited, so its own items
 * are never counted as "other" demand (TASKS.md §8's "current invoice
 * exclusion"). Disabled while `tripCatchId` is empty - there's nothing to
 * ask about before a catch is selected.
 */
export function useTripCatchDraftDemand(tripCatchId: string, excludeInvoiceId: string | undefined) {
  return useQuery({
    queryKey: ["trip-catches", "draft-demand", tripCatchId, excludeInvoiceId ?? null],
    queryFn: () => invoiceService.getTripCatchDraftDemand(tripCatchId, { excludeInvoiceId }),
    enabled: Boolean(tripCatchId),
  });
}
