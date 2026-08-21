"use client";

import { useQuery } from "@tanstack/react-query";

import { invoiceService } from "@/features/invoices/services/invoice-service";

/**
 * Sprint 15 Session 6: fetches "which other invoices may explain this
 * shortage" for the conflict-resolution dialog shown after a failed issue.
 * Disabled while `tripCatchId` is empty - nothing to ask about until an
 * INVOICE_INSUFFICIENT_INVENTORY error hands the caller a real one (see
 * `InvoiceIssueConflictDialog`). `excludeInvoiceId` should always be the
 * invoice that just failed to issue, so it never appears as its own
 * conflict.
 */
export function useTripCatchConflicts(
  tripCatchId: string,
  excludeInvoiceId: string | undefined,
  requiredQuantity: string | undefined
) {
  return useQuery({
    queryKey: ["trip-catches", "conflicts", tripCatchId, excludeInvoiceId ?? null, requiredQuantity ?? null],
    queryFn: () =>
      invoiceService.getTripCatchConflicts(tripCatchId, { excludeInvoiceId, requiredQuantity }),
    enabled: Boolean(tripCatchId),
  });
}
