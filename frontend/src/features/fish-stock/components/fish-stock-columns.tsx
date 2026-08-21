"use client";

import { DataTableColumnHeader } from "@/components/data-table";
import type { DataTableColumn } from "@/components/data-table";
import { FISH_STOCK_UNIT_LABELS } from "@/features/fish-stock/types/fish-stock";
import type { FishStockRow } from "@/features/fish-stock/types/fish-stock";
import { formatQuantity } from "@/utils/format-number";

/**
 * The Fish Stock list table's column set: Fish, Unit, Total Caught, Total
 * Sold, Total Available, Total Waste (Sprint 15 Session 3). No sorting -
 * the backend always orders by fish name ascending, a fixed order, the
 * same posture `getFishSalesColumns` takes for its own fixed backend order.
 * Total Available is the column users actually came here for ("how much can
 * I still sell"), so it's bolded and gets its own accent weight rather than
 * looking like just another number column.
 */
export function getFishStockColumns(): DataTableColumn<FishStockRow>[] {
  return [
    {
      accessorKey: "fishName",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Fish" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{row.original.fishName}</span>,
    },
    {
      accessorKey: "unit",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Unit" />,
      enableSorting: false,
      cell: ({ row }) => FISH_STOCK_UNIT_LABELS[row.original.unit],
    },
    {
      accessorKey: "totalCaught",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Total Caught" />,
      enableSorting: false,
      cell: ({ row }) => formatQuantity(row.original.totalCaught),
      meta: { align: "right" },
    },
    {
      accessorKey: "totalSold",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Total Sold" />,
      enableSorting: false,
      cell: ({ row }) => formatQuantity(row.original.totalSold),
      meta: { align: "right" },
    },
    {
      accessorKey: "totalAvailable",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Total Available" />,
      enableSorting: false,
      cell: ({ row }) => (
        <span className="font-semibold text-primary tabular-nums">
          {formatQuantity(row.original.totalAvailable)}
        </span>
      ),
      meta: { align: "right" },
    },
    {
      accessorKey: "totalWaste",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Total Waste" />,
      enableSorting: false,
      cell: ({ row }) => formatQuantity(row.original.totalWaste),
      meta: { align: "right" },
    },
  ];
}
