"use client";

import { Pencil, Trash2 } from "lucide-react";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { PurchaseOrderItem } from "@/features/purchase-orders/types/purchase-order-item";

/**
 * Row-actions builder for the Purchase Order Items table. Edit/Delete are
 * only ever meaningful while the parent purchase order is `draft` - the
 * backend rejects both with 409 `PURCHASE_ORDER_NOT_DRAFT` otherwise
 * (app/modules/purchase_orders/service.py's `_ensure_draft`) - so
 * `PurchaseOrderItemTable` only invokes this builder at all when the order
 * is draft, mirroring `usePurchaseBillItemRowActions`. RBAC-filtered via
 * `hidden` against the backend's actual `purchase_order:edit`/
 * `purchase_order:delete` codes - there is no separate item-scoped
 * permission set (the router reuses the order-level permissions for its
 * item endpoints too) - cosmetic only, the real gate is the backend's own
 * permission check on each route.
 */
export function usePurchaseOrderItemRowActions(
  onEditRequest: (item: PurchaseOrderItem) => void,
  onDeleteRequest: (item: PurchaseOrderItem) => void
): (item: PurchaseOrderItem) => DataTableAction<PurchaseOrderItem>[] {
  const { hasPermission } = usePermissions();

  return useCallback(
    (item: PurchaseOrderItem) => [
      {
        label: "Edit",
        icon: Pencil,
        onClick: () => onEditRequest(item),
        hidden: () => !hasPermission("purchase_order:edit"),
      },
      {
        label: "Delete",
        icon: Trash2,
        variant: "destructive",
        separatorBefore: true,
        onClick: () => onDeleteRequest(item),
        hidden: () => !hasPermission("purchase_order:delete"),
      },
    ],
    [hasPermission, onEditRequest, onDeleteRequest]
  );
}
