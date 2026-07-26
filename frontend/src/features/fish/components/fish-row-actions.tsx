"use client";

import { Eye, Pencil, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { Fish } from "@/features/fish/types/fish";

/**
 * Row-actions builder for the Fish list table, mirroring
 * `useCompanyRowActions`. View/Edit navigate; Delete hands the row's fish
 * record to `onDeleteRequest` rather than mutating directly - the owning
 * list page renders the one shared `DeleteConfirmationDialog` and decides
 * when the row's record becomes the pending-delete target.
 *
 * The backend's fish permissions are a coarse `fish:view` / `fish:manage`
 * split (app/modules/fish/permissions.py), not separate create/edit/delete
 * codes like Companies - Edit and Delete are both gated on `fish:manage`
 * here for that reason.
 *
 * The returned function is `useCallback`-stabilized (stable as long as
 * `router`, `hasPermission` and `onDeleteRequest` are themselves stable) so
 * the List page's `columns` memoization actually holds.
 */
export function useFishRowActions(
  onDeleteRequest: (fish: Fish) => void
): (fish: Fish) => DataTableAction<Fish>[] {
  const router = useRouter();
  const { hasPermission } = usePermissions();

  return useCallback(
    (fish: Fish) => [
      {
        label: "View",
        icon: Eye,
        onClick: () => router.push(`/fish/${fish.id}`),
        hidden: () => !hasPermission("fish:view"),
      },
      {
        label: "Edit",
        icon: Pencil,
        onClick: () => router.push(`/fish/${fish.id}/edit`),
        hidden: () => !hasPermission("fish:manage"),
      },
      {
        label: "Delete",
        icon: Trash2,
        variant: "destructive",
        separatorBefore: true,
        onClick: () => onDeleteRequest(fish),
        hidden: () => !hasPermission("fish:manage"),
      },
    ],
    [router, hasPermission, onDeleteRequest]
  );
}
