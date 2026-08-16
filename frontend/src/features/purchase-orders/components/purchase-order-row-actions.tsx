"use client";

import { Eye, Pencil } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { PurchaseOrder } from "@/features/purchase-orders/types/purchase-order";

/**
 * Row-actions builder for the Purchase Orders list table - View and Edit.
 * Edit is only ever meaningful while the order is `draft` - the backend
 * rejects it with 409 `PURCHASE_ORDER_NOT_DRAFT` otherwise
 * (app/modules/purchase_orders/service.py's `_ensure_draft`), so it's
 * hidden for any other status; View has no such restriction, mirroring
 * `usePurchaseBillRowActions`. RBAC-filtered via `hidden` against the
 * backend's actual `purchase_order:view`/`purchase_order:edit` codes -
 * cosmetic only, the real gate is the backend's own permission check on
 * the route.
 */
export function usePurchaseOrderRowActions(): (
  order: PurchaseOrder
) => DataTableAction<PurchaseOrder>[] {
  const router = useRouter();
  const { hasPermission } = usePermissions();

  return useCallback(
    (order: PurchaseOrder) => {
      const isDraft = order.status === "draft";
      return [
        {
          label: "View",
          icon: Eye,
          onClick: () => router.push(`/purchase-orders/${order.id}`),
          hidden: () => !hasPermission("purchase_order:view"),
        },
        {
          label: "Edit",
          icon: Pencil,
          onClick: () => router.push(`/purchase-orders/${order.id}/edit`),
          hidden: () => !isDraft || !hasPermission("purchase_order:edit"),
        },
      ];
    },
    [router, hasPermission]
  );
}
