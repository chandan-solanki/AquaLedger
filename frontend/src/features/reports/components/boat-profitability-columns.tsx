"use client";

import { DataTableColumnHeader } from "@/components/data-table";
import type { DataTableColumn } from "@/components/data-table";
import type { BoatProfitabilityRow } from "@/features/reports/types/boat-profitability";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";

/**
 * The Boat Profitability table's column set: Boat, Registration Number,
 * Total Trips, Revenue, Expenses, Profit, Profit Margin %, Average Profit
 * Per Trip, Average Revenue Per Trip, Best Trip Profit, Worst Trip Profit,
 * Last Trip Date (TASKS.md Sprint 11 Session 4 Phase A). No sorting - the
 * backend always orders `profit DESC, boat name ASC`, a fixed order. Row
 * click navigates to the existing Boat Detail page (wired by the page
 * component via `onRowClick`).
 */
export function getBoatProfitabilityColumns(): DataTableColumn<BoatProfitabilityRow>[] {
  return [
    {
      accessorKey: "boatName",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Boat" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{row.original.boatName}</span>,
    },
    {
      accessorKey: "registrationNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Registration Number" />,
      enableSorting: false,
    },
    {
      accessorKey: "totalTrips",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Total Trips" />,
      enableSorting: false,
      meta: { align: "right" },
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
      accessorKey: "averageProfitPerTrip",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Avg Profit / Trip" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.averageProfitPerTrip),
      meta: { align: "right" },
    },
    {
      accessorKey: "averageRevenuePerTrip",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Avg Revenue / Trip" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.averageRevenuePerTrip),
      meta: { align: "right" },
    },
    {
      accessorKey: "bestTripProfit",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Best Trip Profit" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.bestTripProfit),
      meta: { align: "right" },
    },
    {
      accessorKey: "worstTripProfit",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Worst Trip Profit" />,
      enableSorting: false,
      cell: ({ row }) => (
        <span className={Number(row.original.worstTripProfit) < 0 ? "text-destructive" : undefined}>
          {formatCurrency(row.original.worstTripProfit)}
        </span>
      ),
      meta: { align: "right" },
    },
    {
      accessorKey: "lastTripDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Last Trip Date" />,
      enableSorting: false,
      cell: ({ row }) => (row.original.lastTripDate ? formatDate(row.original.lastTripDate) : "—"),
    },
  ];
}
