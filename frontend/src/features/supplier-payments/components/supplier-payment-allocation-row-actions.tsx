"use client";

import { Pencil, Trash2 } from "lucide-react";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { SupplierPaymentAllocation } from "@/features/supplier-payments/types/supplier-payment-allocation";

/**
 * Row-actions builder for the Supplier Payment Allocations table. Edit/
 * Delete are only ever meaningful while the parent supplier payment is
 * `draft` - the backend rejects both with 409
 * `SUPPLIER_PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT` otherwise
 * (app/modules/supplier_payments/service.py's
 * `_ensure_draft_for_allocation`) - so
 * `SupplierPaymentAllocationTable` only invokes this builder at all when the
 * payment is draft, matching `03_INFORMATION_ARCHITECTURE.md` §13's "render
 * only the currently valid action" rule, mirroring
 * `usePaymentAllocationRowActions`. RBAC-filtered via `hidden` against the
 * backend's actual `supplier_payment:edit`/`supplier_payment:delete` codes -
 * there is no separate `supplier_payment_allocation:*` permission set
 * (app/modules/supplier_payments/router.py reuses the supplier payment
 * permissions for its allocation endpoints too) - cosmetic only, the real
 * gate is the backend's own permission check on each route.
 */
export function useSupplierPaymentAllocationRowActions(
  onEditRequest: (allocation: SupplierPaymentAllocation) => void,
  onDeleteRequest: (allocation: SupplierPaymentAllocation) => void
): (allocation: SupplierPaymentAllocation) => DataTableAction<SupplierPaymentAllocation>[] {
  const { hasPermission } = usePermissions();

  return useCallback(
    (allocation: SupplierPaymentAllocation) => [
      {
        label: "Edit",
        icon: Pencil,
        onClick: () => onEditRequest(allocation),
        hidden: () => !hasPermission("supplier_payment:edit"),
      },
      {
        label: "Delete",
        icon: Trash2,
        variant: "destructive",
        separatorBefore: true,
        onClick: () => onDeleteRequest(allocation),
        hidden: () => !hasPermission("supplier_payment:delete"),
      },
    ],
    [hasPermission, onEditRequest, onDeleteRequest]
  );
}
