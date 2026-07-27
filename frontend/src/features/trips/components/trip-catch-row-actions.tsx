"use client";

import { Eye, Pencil, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { TripCatch } from "@/features/trips/types/trip-catch";

/**
 * Row-actions builder for the Trip Catch table, mirroring `useTripRowActions`.
 * There is no separate Trip Catch detail page (Sprint 6 Session 6's scope
 * is Create/Edit/Delete/View-via-existing-table, not a new detail surface),
 * so "View" and "Edit" both route to the same
 * `/trips/{tripId}/catches/{catchId}/edit` page — that page renders the
 * shared `TripCatchForm` read-only for a caller with `trip_catch:view` but
 * not `trip_catch:edit`, and editable otherwise, so one action covers both
 * without a redundant duplicate menu item pointing at the same place.
 * Delete hands the row's trip catch to `onDeleteRequest` — the owning Trip
 * Detail page renders the one shared `DeleteConfirmationDialog`.
 */
export function useTripCatchRowActions(
  tripId: string,
  onDeleteRequest: (tripCatch: TripCatch) => void
): (tripCatch: TripCatch) => DataTableAction<TripCatch>[] {
  const router = useRouter();
  const { hasPermission } = usePermissions();

  return useCallback(
    (tripCatch: TripCatch) => {
      const canEdit = hasPermission("trip_catch:edit");
      return [
        {
          label: canEdit ? "Edit" : "View",
          icon: canEdit ? Pencil : Eye,
          onClick: () => router.push(`/trips/${tripId}/catches/${tripCatch.id}/edit`),
          hidden: () => !hasPermission("trip_catch:view"),
        },
        {
          label: "Delete",
          icon: Trash2,
          variant: "destructive",
          separatorBefore: true,
          onClick: () => onDeleteRequest(tripCatch),
          hidden: () => !hasPermission("trip_catch:delete"),
        },
      ];
    },
    [router, hasPermission, onDeleteRequest, tripId]
  );
}
