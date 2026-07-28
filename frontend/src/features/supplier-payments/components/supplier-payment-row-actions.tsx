"use client";

import { Eye, Pencil, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { SupplierPayment } from "@/features/supplier-payments/types/supplier-payment";

/**
 * Row-actions builder for the Supplier Payment list table. Sprint 9 Session
 * 4 adds Delete alongside Session 3's View/Edit (see TASKS.md); there is no
 * Post action here - posting is a significant, irreversible transaction
 * offered only from the Supplier Payment Detail page
 * (`SupplierPaymentDetailPage`), mirroring how Payment's own Post action is
 * Detail-page-only, never a row action.
 *
 * Edit/Delete are only ever meaningful while the payment is `draft` - the
 * backend rejects both with 409 `SUPPLIER_PAYMENT_NOT_DRAFT` otherwise
 * (app/modules/supplier_payments/service.py's `_ensure_draft`), so both are
 * hidden for any other status; View has no such restriction, mirroring
 * `usePaymentRowActions`. RBAC-filtered via `hidden` against the backend's
 * actual `supplier_payment:view`/`supplier_payment:edit`/
 * `supplier_payment:delete` codes - cosmetic only, the real gate is the
 * backend's own permission check on each route.
 *
 * The returned function is `useCallback`-stabilized (stable as long as
 * `router`, `hasPermission` and `onDeleteRequest` are themselves stable) so
 * the List page's `columns` memoization actually holds.
 */
export function useSupplierPaymentRowActions(
  onDeleteRequest: (payment: SupplierPayment) => void
): (payment: SupplierPayment) => DataTableAction<SupplierPayment>[] {
  const router = useRouter();
  const { hasPermission } = usePermissions();

  return useCallback(
    (payment: SupplierPayment) => {
      const isDraft = payment.status === "draft";
      return [
        {
          label: "View",
          icon: Eye,
          onClick: () => router.push(`/supplier-payments/${payment.id}`),
          hidden: () => !hasPermission("supplier_payment:view"),
        },
        {
          label: "Edit",
          icon: Pencil,
          onClick: () => router.push(`/supplier-payments/${payment.id}/edit`),
          hidden: () => !isDraft || !hasPermission("supplier_payment:edit"),
        },
        {
          label: "Delete",
          icon: Trash2,
          variant: "destructive",
          separatorBefore: true,
          onClick: () => onDeleteRequest(payment),
          hidden: () => !isDraft || !hasPermission("supplier_payment:delete"),
        },
      ];
    },
    [router, hasPermission, onDeleteRequest]
  );
}
