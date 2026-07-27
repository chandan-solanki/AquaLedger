"use client";

import { Eye, Pencil, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { Boat } from "@/features/boats/types/boat";

/**
 * Row-actions builder for the Boat list table, mirroring `useCompanyRowActions`
 * exactly. View/Edit navigate; Delete hands the row's boat to
 * `onDeleteRequest` rather than mutating directly - the owning list page
 * renders the one shared `DeleteConfirmationDialog` and decides when the
 * row's boat becomes the pending-delete target. RBAC-filtered via `hidden`
 * against the backend's actual `boat:view`/`boat:edit`/`boat:delete` codes
 * (app/modules/boats/permissions.py) - cosmetic only, the real gate is the
 * backend's own permission check on each route.
 *
 * The returned function is `useCallback`-stabilized (stable as long as
 * `router`, `hasPermission` and `onDeleteRequest` are themselves stable) so
 * the List page's `columns` memoization actually holds.
 */
export function useBoatRowActions(
  onDeleteRequest: (boat: Boat) => void
): (boat: Boat) => DataTableAction<Boat>[] {
  const router = useRouter();
  const { hasPermission } = usePermissions();

  return useCallback(
    (boat: Boat) => [
      {
        label: "View",
        icon: Eye,
        onClick: () => router.push(`/boats/${boat.id}`),
        hidden: () => !hasPermission("boat:view"),
      },
      {
        label: "Edit",
        icon: Pencil,
        onClick: () => router.push(`/boats/${boat.id}/edit`),
        hidden: () => !hasPermission("boat:edit"),
      },
      {
        label: "Delete",
        icon: Trash2,
        variant: "destructive",
        separatorBefore: true,
        onClick: () => onDeleteRequest(boat),
        hidden: () => !hasPermission("boat:delete"),
      },
    ],
    [router, hasPermission, onDeleteRequest]
  );
}
