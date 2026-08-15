"use client";

import { DataTableColumnHeader } from "@/components/data-table";
import type { DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import type { TripProfitabilityRow } from "@/features/reports";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";

/**
 * Local copy of a Trip Status label - Boats does not import another
 * feature's internals (mirrors `getSalesReportColumns`'s own stated rule
 * in the Reports feature). Only "returned" is ever actually produced here
 * (a hard backend invariant).
 */
const TRIP_STATUS_LABELS: Record<TripProfitabilityRow["status"], string> = {
  planned: "Planned",
  departed: "Departed",
  returned: "Returned",
  cancelled: "Cancelled",
};

/**
 * The Boat Detail page's own Trip History column set: Trip Number,
 * Departure, Return, Revenue, Expenses, Profit, Margin, Status (TASKS.md
 * Sprint 11 Session 4 Phase A "TRIP HISTORY") - no Boat column, since every
 * row already belongs to the one boat this page is showing. Row click
 * navigates to the existing Trip Detail page.
 */
export function getBoatTripHistoryColumns(): DataTableColumn<TripProfitabilityRow>[] {
  return [
    {
      accessorKey: "tripNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Trip Number" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{row.original.tripNumber}</span>,
    },
    {
      accessorKey: "departureDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Departure" />,
      enableSorting: false,
      cell: ({ row }) => formatDate(row.original.departureDate),
    },
    {
      accessorKey: "returnDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Return" />,
      enableSorting: false,
      cell: ({ row }) => (row.original.returnDate ? formatDate(row.original.returnDate) : "—"),
    },
    {
      accessorKey: "revenue",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Revenue" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.revenue),
      meta: { align: "right" },
    },
    {
      accessorKey: "expenses",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Expenses" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.expenses),
      meta: { align: "right" },
    },
    {
      accessorKey: "profit",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Profit" />,
      enableSorting: false,
      cell: ({ row }) => (
        <span className={Number(row.original.profit) < 0 ? "text-destructive" : undefined}>
          {formatCurrency(row.original.profit)}
        </span>
      ),
      meta: { align: "right" },
    },
    {
      accessorKey: "profitMarginPercent",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Margin" />,
      enableSorting: false,
      cell: ({ row }) => `${row.original.profitMarginPercent}%`,
      meta: { align: "right" },
    },
    {
      accessorKey: "status",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
      enableSorting: false,
      cell: ({ row }) => <Badge variant="secondary">{TRIP_STATUS_LABELS[row.original.status]}</Badge>,
    },
  ];
}
