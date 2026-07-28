"use client";

import { Pencil, Trash2 } from "lucide-react";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { PurchaseBillItem } from "@/features/purchase-bills/types/purchase-bill-item";

/**
 * Row-actions builder for the Purchase Bill Items table. Edit/Delete are
 * only ever meaningful while the parent purchase bill is `draft` - the
 * backend rejects both with 409 `PURCHASE_BILL_NOT_DRAFT` otherwise
 * (app/modules/purchase/service.py's `_ensure_draft`) - so
 * `PurchaseBillItemTable` only invokes this builder at all when the bill is
 * draft, matching `03_INFORMATION_ARCHITECTURE.md` §13's "render only the
 * currently valid action" rule, mirroring `useInvoiceItemRowActions`.
 * RBAC-filtered via `hidden` against the backend's actual `purchase:edit`/
 * `purchase:delete` codes - there is no separate `purchase_item:*`
 * permission set (app/modules/purchase/router.py reuses the purchase
 * permissions for its item endpoints too) - cosmetic only, the real gate is
 * the backend's own permission check on each route.
 */
export function usePurchaseBillItemRowActions(
  onEditRequest: (item: PurchaseBillItem) => void,
  onDeleteRequest: (item: PurchaseBillItem) => void
): (item: PurchaseBillItem) => DataTableAction<PurchaseBillItem>[] {
  const { hasPermission } = usePermissions();

  return useCallback(
    (item: PurchaseBillItem) => [
      {
        label: "Edit",
        icon: Pencil,
        onClick: () => onEditRequest(item),
        hidden: () => !hasPermission("purchase:edit"),
      },
      {
        label: "Delete",
        icon: Trash2,
        variant: "destructive",
        separatorBefore: true,
        onClick: () => onDeleteRequest(item),
        hidden: () => !hasPermission("purchase:delete"),
      },
    ],
    [hasPermission, onEditRequest, onDeleteRequest]
  );
}
