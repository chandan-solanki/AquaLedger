"use client";

import { Eye, Pencil, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import type { DataTableAction } from "@/components/data-table";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { TripExpense } from "@/features/trips/types/trip-expense";

/**
 * Row-actions builder for the Trip Expenses table, mirroring
 * `useTripCatchRowActions`. There is no separate Trip Expense detail page,
 * so "View" and "Edit" both route to the same
 * `/trips/{tripId}/expenses/{expenseId}/edit` page — that page renders the
 * shared `TripExpenseForm` read-only for a caller with `trip_expense:view`
 * but not `trip_expense:edit`, and editable otherwise. Delete hands the
 * row's trip expense to `onDeleteRequest` — the owning Trip Detail page
 * renders the one shared `DeleteConfirmationDialog`.
 */
export function useTripExpenseRowActions(
  tripId: string,
  onDeleteRequest: (tripExpense: TripExpense) => void
): (tripExpense: TripExpense) => DataTableAction<TripExpense>[] {
  const router = useRouter();
  const { hasPermission } = usePermissions();

  return useCallback(
    (tripExpense: TripExpense) => {
      const canEdit = hasPermission("trip_expense:edit");
      return [
        {
          label: canEdit ? "Edit" : "View",
          icon: canEdit ? Pencil : Eye,
          onClick: () => router.push(`/trips/${tripId}/expenses/${tripExpense.id}/edit`),
          hidden: () => !hasPermission("trip_expense:view"),
        },
        {
          label: "Delete",
          icon: Trash2,
          variant: "destructive",
          separatorBefore: true,
          onClick: () => onDeleteRequest(tripExpense),
          hidden: () => !hasPermission("trip_expense:delete"),
        },
      ];
    },
    [router, hasPermission, onDeleteRequest, tripId]
  );
}
