"use client";

import { DataTableColumnHeader } from "@/components/data-table";
import type { DataTableColumn } from "@/components/data-table";
import type { FishSalesRow } from "@/features/reports/types/fish-sales";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";

/**
 * Local copy of a Fish Unit label map - Reports does not import another
 * feature's internals (mirrors `getSalesReportColumns`'s own stated rule).
 */
const FISH_SALES_UNIT_LABELS: Record<FishSalesRow["unit"], string> = {
  kg: "Kg",
  box: "Box",
  piece: "Piece",
  ton: "Ton",
};

/**
 * The Fish Sales Analytics table's column set: Fish, Scientific Name,
 * Total Quantity Sold, Unit, Revenue, Average Selling Price, Invoice
 * Count, Trip Count, Customer Count, Last Sold Date (TASKS.md Sprint 11
 * Session 4 Phase B). No sorting - the backend always orders `revenue
 * DESC, fish name ASC`, a fixed order. Row click navigates to the
 * existing Fish Detail page (wired by the page component via
 * `onRowClick`).
 */
export function getFishSalesColumns(): DataTableColumn<FishSalesRow>[] {
  return [
    {
      accessorKey: "fishName",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Fish" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{row.original.fishName}</span>,
    },
    {
      accessorKey: "scientificName",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Scientific Name" />,
      enableSorting: false,
      cell: ({ row }) => row.original.scientificName ?? "—",
    },
    {
      accessorKey: "quantitySold",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Total Quantity Sold" />,
      enableSorting: false,
      meta: { align: "right" },
    },
    {
      accessorKey: "unit",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Unit" />,
      enableSorting: false,
      cell: ({ row }) => FISH_SALES_UNIT_LABELS[row.original.unit],
    },
    {
      accessorKey: "revenue",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Revenue" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.revenue),
      meta: { align: "right" },
    },
    {
      accessorKey: "averageSellingPrice",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Average Selling Price" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.averageSellingPrice),
      meta: { align: "right" },
    },
    {
      accessorKey: "invoiceCount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Invoice Count" />,
      enableSorting: false,
      meta: { align: "right" },
    },
    {
      accessorKey: "tripCount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Trip Count" />,
      enableSorting: false,
      meta: { align: "right" },
    },
    {
      accessorKey: "customerCount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Customer Count" />,
      enableSorting: false,
      meta: { align: "right" },
    },
    {
      accessorKey: "lastSoldDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Last Sold Date" />,
      enableSorting: false,
      cell: ({ row }) => (row.original.lastSoldDate ? formatDate(row.original.lastSoldDate) : "—"),
    },
  ];
}
