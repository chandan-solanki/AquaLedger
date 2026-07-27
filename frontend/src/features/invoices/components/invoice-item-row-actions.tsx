"use client";

import { Pencil, Trash2 } from "lucide-react";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { InvoiceItem } from "@/features/invoices/types/invoice-item";

/**
 * Row-actions builder for the Invoice Items table. Edit/Delete are only
 * ever meaningful while the parent invoice is `draft` - the backend rejects
 * both with 409 `INVOICE_NOT_DRAFT` otherwise
 * (app/modules/invoices/service.py's `_ensure_draft`) - so `InvoiceItemTable`
 * only invokes this builder at all when the invoice is draft, matching
 * `03_INFORMATION_ARCHITECTURE.md` §13's "render only the currently valid
 * action" rule. RBAC-filtered via `hidden` against the backend's actual
 * `invoice:edit`/`invoice:delete` codes - there is no separate
 * `invoice_item:*` permission set (app/modules/invoices/router.py reuses
 * the invoice permissions for its item endpoints too) - cosmetic only, the
 * real gate is the backend's own permission check on each route.
 */
export function useInvoiceItemRowActions(
  onEditRequest: (item: InvoiceItem) => void,
  onDeleteRequest: (item: InvoiceItem) => void
): (item: InvoiceItem) => DataTableAction<InvoiceItem>[] {
  const { hasPermission } = usePermissions();

  return useCallback(
    (item: InvoiceItem) => [
      {
        label: "Edit",
        icon: Pencil,
        onClick: () => onEditRequest(item),
        hidden: () => !hasPermission("invoice:edit"),
      },
      {
        label: "Delete",
        icon: Trash2,
        variant: "destructive",
        separatorBefore: true,
        onClick: () => onDeleteRequest(item),
        hidden: () => !hasPermission("invoice:delete"),
      },
    ],
    [hasPermission, onEditRequest, onDeleteRequest]
  );
}
