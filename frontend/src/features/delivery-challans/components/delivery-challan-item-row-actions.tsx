"use client";

import { Pencil, Trash2 } from "lucide-react";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { DeliveryChallanItemRow } from "@/features/delivery-challans/components/delivery-challan-item-columns";

/**
 * Row-actions builder for the Delivery Challan Items table. Edit/Delete are
 * only ever meaningful while the parent delivery challan is `draft` - the
 * backend rejects both with 409 `DELIVERY_CHALLAN_NOT_DRAFT` otherwise - so
 * `DeliveryChallanItemTable` only invokes this builder at all when the
 * challan is draft, mirroring `usePurchaseOrderItemRowActions`.
 */
export function useDeliveryChallanItemRowActions(
  onEditRequest: (row: DeliveryChallanItemRow) => void,
  onDeleteRequest: (row: DeliveryChallanItemRow) => void
): (row: DeliveryChallanItemRow) => DataTableAction<DeliveryChallanItemRow>[] {
  const { hasPermission } = usePermissions();

  return useCallback(
    (row: DeliveryChallanItemRow) => [
      {
        label: "Edit",
        icon: Pencil,
        onClick: () => onEditRequest(row),
        hidden: () => !hasPermission("delivery_challan:edit"),
      },
      {
        label: "Delete",
        icon: Trash2,
        variant: "destructive",
        separatorBefore: true,
        onClick: () => onDeleteRequest(row),
        hidden: () => !hasPermission("delivery_challan:delete"),
      },
    ],
    [hasPermission, onEditRequest, onDeleteRequest]
  );
}
