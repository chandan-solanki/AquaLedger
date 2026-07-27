"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { invoiceItemKeys, invoiceKeys } from "@/features/invoices/constants/query-keys";
import { invoiceService } from "@/features/invoices/services/invoice-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Owns the full delete outcome (cache invalidation, toast, navigation) so
 * every call site - the Detail page's Delete action and the List page's row
 * action - gets identical behavior, mirroring `useDeleteBoat`/`useDeleteTrip`
 * exactly. Only `draft` invoices may be deleted (409 `INVOICE_NOT_DRAFT`
 * otherwise, app/modules/invoices/service.py's `_ensure_draft`) - a draft
 * has never been issued, so it has never touched trip catch inventory or a
 * company's `outstanding_amount` (only Issue does that), meaning deleting
 * one has no side effects to invalidate beyond the invoice's own queries.
 */
export function useDeleteInvoice() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (id: string) => invoiceService.deleteInvoice(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() });
      queryClient.removeQueries({ queryKey: invoiceKeys.detail(id) });
      queryClient.removeQueries({ queryKey: invoiceItemKeys.byInvoice(id) });
      toastSuccess("Invoice deleted.");
      router.push("/invoices");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
