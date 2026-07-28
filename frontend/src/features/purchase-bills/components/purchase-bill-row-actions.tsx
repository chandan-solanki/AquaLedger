"use client";

import { Eye, Pencil } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { PurchaseBill } from "@/features/purchase-bills/types/purchase-bill";

/**
 * Row-actions builder for the Purchase Bills list table - View and Edit.
 * Edit is only ever meaningful while the bill is `draft` - the backend
 * rejects it with 409 `PURCHASE_BILL_NOT_DRAFT` otherwise
 * (app/modules/purchase/service.py's `_ensure_draft`), so it's hidden for
 * any other status; View has no such restriction, mirroring
 * `useInvoiceRowActions`. There is no Delete/Post action here - this
 * module's scope is List/Create/Edit/Detail (plus item CRUD on the Detail
 * page); Delete and Post are separate, later work. RBAC-filtered via
 * `hidden` against the backend's actual `purchase:view`/`purchase:edit`
 * codes - cosmetic only, the real gate is the backend's own permission
 * check on the route.
 */
export function usePurchaseBillRowActions(): (
  bill: PurchaseBill
) => DataTableAction<PurchaseBill>[] {
  const router = useRouter();
  const { hasPermission } = usePermissions();

  return useCallback(
    (bill: PurchaseBill) => {
      const isDraft = bill.status === "draft";
      return [
        {
          label: "View",
          icon: Eye,
          onClick: () => router.push(`/purchase-bills/${bill.id}`),
          hidden: () => !hasPermission("purchase:view"),
        },
        {
          label: "Edit",
          icon: Pencil,
          onClick: () => router.push(`/purchase-bills/${bill.id}/edit`),
          hidden: () => !isDraft || !hasPermission("purchase:edit"),
        },
      ];
    },
    [router, hasPermission]
  );
}
