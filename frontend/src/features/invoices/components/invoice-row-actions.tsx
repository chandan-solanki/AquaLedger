"use client";

import { Eye, Pencil, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { Invoice } from "@/features/invoices/types/invoice";

/**
 * Row-actions builder for the Invoice list table. Sprint 7 Session 4 adds
 * Delete alongside Session 3's View/Edit (see TASKS.md); there is no Cancel
 * action because the backend exposes no cancel endpoint yet
 * (app/modules/invoices/permissions.py's own comment: "invoice:cancel" is
 * only a seeded permission reserved for a future workflow).
 *
 * Edit/Delete are only ever meaningful while the invoice is `draft` - the
 * backend rejects both with 409 `INVOICE_NOT_DRAFT` otherwise
 * (app/modules/invoices/service.py's `_ensure_draft`), so both are hidden
 * for any other status, matching `03_INFORMATION_ARCHITECTURE.md` §13's
 * "render only the currently valid action" rule; View has no such
 * restriction. RBAC-filtered via `hidden` against the backend's actual
 * `invoice:view`/`invoice:edit`/`invoice:delete` codes - cosmetic only, the
 * real gate is the backend's own permission check on each route, mirroring
 * `useBoatRowActions`/`useTripRowActions`.
 *
 * The returned function is `useCallback`-stabilized (stable as long as
 * `router`, `hasPermission` and `onDeleteRequest` are themselves stable) so
 * the List page's `columns` memoization actually holds.
 */
export function useInvoiceRowActions(
  onDeleteRequest: (invoice: Invoice) => void
): (invoice: Invoice) => DataTableAction<Invoice>[] {
  const router = useRouter();
  const { hasPermission } = usePermissions();

  return useCallback(
    (invoice: Invoice) => {
      const isDraft = invoice.status === "draft";
      return [
        {
          label: "View",
          icon: Eye,
          onClick: () => router.push(`/invoices/${invoice.id}`),
          hidden: () => !hasPermission("invoice:view"),
        },
        {
          label: "Edit",
          icon: Pencil,
          onClick: () => router.push(`/invoices/${invoice.id}/edit`),
          hidden: () => !isDraft || !hasPermission("invoice:edit"),
        },
        {
          label: "Delete",
          icon: Trash2,
          variant: "destructive",
          separatorBefore: true,
          onClick: () => onDeleteRequest(invoice),
          hidden: () => !isDraft || !hasPermission("invoice:delete"),
        },
      ];
    },
    [router, hasPermission, onDeleteRequest]
  );
}
