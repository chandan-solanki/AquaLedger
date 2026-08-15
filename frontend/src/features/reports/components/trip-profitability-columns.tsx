"use client";

import { DataTableColumnHeader } from "@/components/data-table";
import type { DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import type { TripProfitabilityRow } from "@/features/reports/types/trip-profitability";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";

/**
 * Local copy of a Trip Status label/badge map - Reports does not import
 * another feature's internals (mirrors `getSalesReportColumns`'s own stated
 * rule). Only "returned" is ever actually produced by this report (a hard
 * backend invariant - see TripProfitabilityRow's own docstring), but the
 * full vocabulary is mapped for type-safety.
 */
const TRIP_PROFITABILITY_STATUS_LABELS: Record<TripProfitabilityRow["status"], string> = {
  planned: "Planned",
  departed: "Departed",
  returned: "Returned",
  cancelled: "Cancelled",
};

/**
 * The Trip Profitability table's column set: Trip Number, Boat, Departure
 * Date, Return Date, Revenue, Expenses, Profit, Profit Margin %, Trip
 * Status (TASKS.md Sprint 11 Session 4 Phase A). No sorting - the backend
 * always orders `return date DESC, trip number DESC`, a fixed order. Row
 * click navigates to the existing Trip Detail page (wired by the page
 * component via `onRowClick`).
 */
export function getTripProfitabilityColumns(): DataTableColumn<TripProfitabilityRow>[] {
  return [
    {
      accessorKey: "tripNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Trip Number" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{row.original.tripNumber}</span>,
    },
    {
      accessorKey: "boatName",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Boat" />,
      enableSorting: false,
    },
    {
      accessorKey: "departureDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Departure Date" />,
      enableSorting: false,
      cell: ({ row }) => formatDate(row.original.departureDate),
    },
    {
      accessorKey: "returnDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Return Date" />,
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
      header: ({ column }) => <DataTableColumnHeader column={column} title="Profit Margin %" />,
      enableSorting: false,
      cell: ({ row }) => `${row.original.profitMarginPercent}%`,
      meta: { align: "right" },
    },
    {
      accessorKey: "status",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Trip Status" />,
      enableSorting: false,
      cell: ({ row }) => (
        <Badge variant="secondary">{TRIP_PROFITABILITY_STATUS_LABELS[row.original.status]}</Badge>
      ),
    },
  ];
}
