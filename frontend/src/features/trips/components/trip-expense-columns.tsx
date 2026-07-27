"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import { EXPENSE_TYPE_LABELS } from "@/features/trips/constants/expense-type";
import type { TripExpense } from "@/features/trips/types/trip-expense";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";

/**
 * The Trip Expenses sub-table's column set: Expense Type, Amount, Expense
 * Date, Description, Vendor Name, Receipt Number - every field
 * `TripExpenseResponse` carries (app/modules/trip_expenses/schemas.py)
 * except id/tenant_id/trip_id (implicit - the table is already scoped to
 * one trip) and created_at/updated_at. No total/sum row - that is trip
 * profitability, explicitly out of this session's scope. Sorting is
 * disabled on every column since this table has no sort UI (see
 * `TripExpenseTable`).
 */
export function getTripExpenseColumns(
  rowActions: (tripExpense: TripExpense) => DataTableAction<TripExpense>[]
): DataTableColumn<TripExpense>[] {
  return [
    {
      accessorKey: "expenseType",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Expense Type" />,
      enableSorting: false,
      cell: ({ row }) => EXPENSE_TYPE_LABELS[row.original.expenseType],
    },
    {
      accessorKey: "amount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Amount" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.amount),
      meta: { align: "right" },
    },
    {
      accessorKey: "expenseDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Expense Date" />,
      enableSorting: false,
      cell: ({ row }) => formatDate(row.original.expenseDate),
    },
    {
      accessorKey: "description",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Description" />,
      enableSorting: false,
      cell: ({ row }) => row.original.description ?? "—",
    },
    {
      accessorKey: "vendorName",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Vendor" />,
      enableSorting: false,
      cell: ({ row }) => row.original.vendorName ?? "—",
    },
    {
      accessorKey: "receiptNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Receipt Number" />,
      enableSorting: false,
      cell: ({ row }) => row.original.receiptNumber ?? "—",
    },
    createRowActionsColumn<TripExpense>(rowActions),
  ];
}
