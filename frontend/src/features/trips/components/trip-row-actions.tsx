"use client";

import { Eye, Pencil, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { Trip } from "@/features/trips/types/trip";

/**
 * Row-actions builder for the Trip list table, mirroring `useBoatRowActions`
 * exactly. View/Edit navigate; Delete hands the row's trip to
 * `onDeleteRequest` rather than mutating directly - the owning list page
 * renders the one shared `DeleteConfirmationDialog` and decides when the
 * row's trip becomes the pending-delete target. RBAC-filtered via `hidden`
 * against the backend's actual `trip:view`/`trip:edit`/`trip:delete` codes
 * (app/modules/trips/permissions.py) - cosmetic only, the real gate is the
 * backend's own permission check on each route.
 *
 * The returned function is `useCallback`-stabilized (stable as long as
 * `router`, `hasPermission` and `onDeleteRequest` are themselves stable) so
 * the List page's `columns` memoization actually holds.
 */
export function useTripRowActions(
  onDeleteRequest: (trip: Trip) => void
): (trip: Trip) => DataTableAction<Trip>[] {
  const router = useRouter();
  const { hasPermission } = usePermissions();

  return useCallback(
    (trip: Trip) => [
      {
        label: "View",
        icon: Eye,
        onClick: () => router.push(`/trips/${trip.id}`),
        hidden: () => !hasPermission("trip:view"),
      },
      {
        label: "Edit",
        icon: Pencil,
        onClick: () => router.push(`/trips/${trip.id}/edit`),
        hidden: () => !hasPermission("trip:edit"),
      },
      {
        label: "Delete",
        icon: Trash2,
        variant: "destructive",
        separatorBefore: true,
        onClick: () => onDeleteRequest(trip),
        hidden: () => !hasPermission("trip:delete"),
      },
    ],
    [router, hasPermission, onDeleteRequest]
  );
}
