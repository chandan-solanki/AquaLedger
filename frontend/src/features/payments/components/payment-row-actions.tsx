"use client";

import { Eye, Pencil, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { Payment } from "@/features/payments/types/payment";

/**
 * Row-actions builder for the Payment list table. Sprint 8 Session 4 adds
 * Delete alongside Session 3's View/Edit (see TASKS.md); there is no Post
 * action here - posting is a significant, irreversible transaction offered
 * only from the Payment Detail page (`PaymentDetailPage`), mirroring how
 * Invoice's Issue action is Detail-page-only, never a row action. There is
 * also no Allocate action - allocation management lives inline on the
 * Detail page (`PaymentAllocationTable`), not the List page.
 *
 * Edit/Delete are only ever meaningful while the payment is `draft` - the
 * backend rejects both with 409 `PAYMENT_NOT_DRAFT` otherwise
 * (app/modules/payments/service.py's `_ensure_draft`), so both are hidden
 * for any other status, matching `03_INFORMATION_ARCHITECTURE.md` §13's
 * "render only the currently valid action" rule; View has no such
 * restriction, mirroring `useInvoiceRowActions`. RBAC-filtered via `hidden`
 * against the backend's actual `payment:view`/`payment:edit`/`payment:delete`
 * codes - cosmetic only, the real gate is the backend's own permission
 * check on each route.
 *
 * The returned function is `useCallback`-stabilized (stable as long as
 * `router`, `hasPermission` and `onDeleteRequest` are themselves stable) so
 * the List page's `columns` memoization actually holds.
 */
export function usePaymentRowActions(
  onDeleteRequest: (payment: Payment) => void
): (payment: Payment) => DataTableAction<Payment>[] {
  const router = useRouter();
  const { hasPermission } = usePermissions();

  return useCallback(
    (payment: Payment) => {
      const isDraft = payment.status === "draft";
      return [
        {
          label: "View",
          icon: Eye,
          onClick: () => router.push(`/payments/${payment.id}`),
          hidden: () => !hasPermission("payment:view"),
        },
        {
          label: "Edit",
          icon: Pencil,
          onClick: () => router.push(`/payments/${payment.id}/edit`),
          hidden: () => !isDraft || !hasPermission("payment:edit"),
        },
        {
          label: "Delete",
          icon: Trash2,
          variant: "destructive",
          separatorBefore: true,
          onClick: () => onDeleteRequest(payment),
          hidden: () => !isDraft || !hasPermission("payment:delete"),
        },
      ];
    },
    [router, hasPermission, onDeleteRequest]
  );
}
