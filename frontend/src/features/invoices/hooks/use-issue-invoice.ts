"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { companyKeys } from "@/features/companies";
import { invoiceItemKeys, invoiceKeys } from "@/features/invoices/constants/query-keys";
import { invoiceService } from "@/features/invoices/services/invoice-service";
import { tripCatchKeys } from "@/features/trips";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Issue is the invoice module's one true business transaction
 * (app/modules/invoices/service.py's `InvoiceService.issue`,
 * ARCHITECTURE.md §13.3): `draft` -> `issued`, irreversible. The backend
 * assigns `invoice_number`, deducts every referenced trip catch's
 * `available_quantity` (crediting `sold_quantity`), and increases the
 * billed company's `outstanding_amount`, all inside one transaction -
 * nothing is computed here, only invalidated, so the next read shows the
 * server's own numbers (the "server as source of truth" principle -
 * financial mutations are never optimistic).
 *
 * Invalidation reaches beyond this invoice: `companyKeys.detail` for the
 * exact billed company (known from the mutation's own return value), and
 * `tripCatchKeys.all()` broadly - which specific trip catches were
 * deducted is only knowable by re-fetching this invoice's items (the
 * `InvoiceResponse` doesn't include them), so every trip catch query is
 * invalidated rather than guessed at.
 */
export function useIssueInvoice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => invoiceService.issueInvoice(id),
    onSuccess: (invoice) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(invoice.id) });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() });
      queryClient.invalidateQueries({ queryKey: invoiceItemKeys.byInvoice(invoice.id) });
      queryClient.invalidateQueries({ queryKey: companyKeys.detail(invoice.companyId) });
      queryClient.invalidateQueries({ queryKey: tripCatchKeys.all() });
      toastSuccess(invoice.invoiceNumber ? `${invoice.invoiceNumber} issued.` : "Invoice issued.");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
