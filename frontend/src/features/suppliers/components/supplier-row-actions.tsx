"use client";

import { Eye, Pencil, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { Supplier } from "@/features/suppliers/types/supplier";

/**
 * Row-actions builder for the Suppliers list table. View/Edit navigate;
 * Delete hands the row's supplier to `onDeleteRequest` rather than mutating
 * directly - the owning list page renders the one shared
 * `DeleteConfirmationDialog` and decides when the row's supplier becomes the
 * pending-delete target. RBAC-filtered via `hidden`, mirroring
 * `useCompanyRowActions` exactly.
 *
 * The returned function is `useCallback`-stabilized (stable as long as
 * `router`, `hasPermission` and `onDeleteRequest` are themselves stable) so
 * the List page's `columns` memoization actually holds.
 */
export function useSupplierRowActions(
  onDeleteRequest: (supplier: Supplier) => void
): (supplier: Supplier) => DataTableAction<Supplier>[] {
  const router = useRouter();
  const { hasPermission } = usePermissions();

  return useCallback(
    (supplier: Supplier) => [
      {
        label: "View",
        icon: Eye,
        onClick: () => router.push(`/suppliers/${supplier.id}`),
        hidden: () => !hasPermission("supplier:view"),
      },
      {
        label: "Edit",
        icon: Pencil,
        onClick: () => router.push(`/suppliers/${supplier.id}/edit`),
        hidden: () => !hasPermission("supplier:edit"),
      },
      {
        label: "Delete",
        icon: Trash2,
        variant: "destructive",
        separatorBefore: true,
        onClick: () => onDeleteRequest(supplier),
        hidden: () => !hasPermission("supplier:delete"),
      },
    ],
    [router, hasPermission, onDeleteRequest]
  );
}
