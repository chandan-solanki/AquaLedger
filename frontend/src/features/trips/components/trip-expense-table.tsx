"use client";

import { useMemo, useState } from "react";

import { DataTable, DataTableEmpty, useDataTable } from "@/components/data-table";
import { InfoCard } from "@/components/data-display/info-card";
import { DeleteConfirmationDialog } from "@/components/feedback/dialogs/delete-confirmation-dialog";
import { EXPENSE_TYPE_LABELS } from "@/features/trips/constants/expense-type";
import { getTripExpenseColumns } from "@/features/trips/components/trip-expense-columns";
import { useTripExpenseRowActions } from "@/features/trips/components/trip-expense-row-actions";
import { useDeleteTripExpense } from "@/features/trips/hooks/use-delete-trip-expense";
import { useTripExpenses } from "@/features/trips/hooks/use-trip-expenses";
import type { TripExpense } from "@/features/trips/types/trip-expense";
import { normalizeApiError } from "@/utils/api-error";

export interface TripExpenseTableProps {
  tripId: string;
}

/**
 * The Trip Detail page's Expenses section - a bounded sub-table of every
 * `trip_expenses` row for this one trip (fetched via `trip_id`, since
 * `trip-expenses` is its own top-level backend resource, not nested under
 * `/trips/{id}` or embedded in `TripResponse` - see `trip-expense-service.ts`).
 * No search/filter/sort/pagination UI: the whole set is fetched in one page
 * (`useTripExpenses`'s own max page_size) and rendered as-is, since a single
 * trip's expense count is small and bounded. No total/sum row - that is
 * trip profitability, out of scope this session.
 *
 * Owns its own row-level Delete flow (`useDeleteTripExpense` + the shared
 * `DeleteConfirmationDialog`) - View/Edit are row-action navigation
 * (`useTripExpenseRowActions`) to `/trips/{tripId}/expenses/{expenseId}/edit`.
 * Create ("Add Expense") is a page-level action rendered by the Trip Detail
 * page itself, not this table.
 */
export function TripExpenseTable({ tripId }: TripExpenseTableProps) {
  const [pendingDelete, setPendingDelete] = useState<TripExpense | null>(null);

  const expensesQuery = useTripExpenses(tripId);
  const deleteTripExpense = useDeleteTripExpense();
  const expenses = useMemo(() => expensesQuery.data?.data ?? [], [expensesQuery.data]);
  const apiError = expensesQuery.isError ? normalizeApiError(expensesQuery.error) : null;

  const rowActionsFor = useTripExpenseRowActions(tripId, setPendingDelete);
  const columns = useMemo(() => getTripExpenseColumns(rowActionsFor), [rowActionsFor]);
  const table = useDataTable({ data: expenses, columns });

  return (
    <InfoCard>
      <DataTable
        table={table}
        isLoading={expensesQuery.isLoading}
        error={
          apiError
            ? {
                title: "Failed to load trip expense records",
                description: apiError.message,
                onRetry: () => expensesQuery.refetch(),
              }
            : null
        }
        isEmpty={!expensesQuery.isLoading && !apiError && expenses.length === 0}
        emptyState={
          <DataTableEmpty
            title="No expenses recorded"
            description="Expense records for this trip will appear here."
          />
        }
        stickyActionColumn
        aria-label="Trip expenses"
      />

      {pendingDelete && (
        <DeleteConfirmationDialog
          open={Boolean(pendingDelete)}
          onOpenChange={(open) => !open && setPendingDelete(null)}
          entityName={`${EXPENSE_TYPE_LABELS[pendingDelete.expenseType]} expense`}
          entityLabel="trip expense"
          isLoading={deleteTripExpense.isPending}
          onConfirm={() =>
            deleteTripExpense.mutate(
              { id: pendingDelete.id, tripId },
              { onSuccess: () => setPendingDelete(null) }
            )
          }
        />
      )}
    </InfoCard>
  );
}
