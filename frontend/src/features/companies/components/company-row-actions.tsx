"use client";

import { Eye, Pencil, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { Company } from "@/features/companies/types/company";

/**
 * Row-actions builder for the Companies list table. View/Edit navigate;
 * Delete hands the row's company to `onDeleteRequest` rather than mutating
 * directly - the owning list page renders the one shared
 * `DeleteConfirmationDialog` and decides when the row's company becomes the
 * pending-delete target. RBAC-filtered via `hidden`, per
 * `07_FRONTEND_ARCHITECTURE.md` §11 — cosmetic only, the real gate is the
 * backend's own permission check on each route.
 *
 * The returned function is `useCallback`-stabilized (stable as long as
 * `router`, `hasPermission` and `onDeleteRequest` are themselves stable) so
 * the List page's `columns` memoization actually holds — otherwise every
 * render would rebuild the table's column defs for no reason.
 */
export function useCompanyRowActions(
  onDeleteRequest: (company: Company) => void
): (company: Company) => DataTableAction<Company>[] {
  const router = useRouter();
  const { hasPermission } = usePermissions();

  return useCallback(
    (company: Company) => [
      {
        label: "View",
        icon: Eye,
        onClick: () => router.push(`/companies/${company.id}`),
        hidden: () => !hasPermission("company:view"),
      },
      {
        label: "Edit",
        icon: Pencil,
        onClick: () => router.push(`/companies/${company.id}/edit`),
        hidden: () => !hasPermission("company:edit"),
      },
      {
        label: "Delete",
        icon: Trash2,
        variant: "destructive",
        separatorBefore: true,
        onClick: () => onDeleteRequest(company),
        hidden: () => !hasPermission("company:delete"),
      },
    ],
    [router, hasPermission, onDeleteRequest]
  );
}
