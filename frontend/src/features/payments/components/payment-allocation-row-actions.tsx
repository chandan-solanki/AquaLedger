"use client";

import { Pencil, Trash2 } from "lucide-react";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { PaymentAllocation } from "@/features/payments/types/payment-allocation";

/**
 * Row-actions builder for the Payment Allocations table. Edit/Delete are
 * only ever meaningful while the parent payment is `draft` - the backend
 * rejects both with 409 `PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT` otherwise
 * (app/modules/payments/service.py's `_ensure_draft_for_allocation`) - so
 * `PaymentAllocationTable` only invokes this builder at all when the
 * payment is draft, matching `03_INFORMATION_ARCHITECTURE.md` §13's "render
 * only the currently valid action" rule, mirroring
 * `useInvoiceItemRowActions`. RBAC-filtered via `hidden` against the
 * backend's actual `payment:edit`/`payment:delete` codes - there is no
 * separate `payment_allocation:*` permission set
 * (app/modules/payments/router.py reuses the payment permissions for its
 * allocation endpoints too) - cosmetic only, the real gate is the backend's
 * own permission check on each route.
 */
export function usePaymentAllocationRowActions(
  onEditRequest: (allocation: PaymentAllocation) => void,
  onDeleteRequest: (allocation: PaymentAllocation) => void
): (allocation: PaymentAllocation) => DataTableAction<PaymentAllocation>[] {
  const { hasPermission } = usePermissions();

  return useCallback(
    (allocation: PaymentAllocation) => [
      {
        label: "Edit",
        icon: Pencil,
        onClick: () => onEditRequest(allocation),
        hidden: () => !hasPermission("payment:edit"),
      },
      {
        label: "Delete",
        icon: Trash2,
        variant: "destructive",
        separatorBefore: true,
        onClick: () => onDeleteRequest(allocation),
        hidden: () => !hasPermission("payment:delete"),
      },
    ],
    [hasPermission, onEditRequest, onDeleteRequest]
  );
}
