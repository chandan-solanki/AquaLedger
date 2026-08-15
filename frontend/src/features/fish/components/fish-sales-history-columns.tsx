"use client";

import { DataTableColumnHeader } from "@/components/data-table";
import type { DataTableColumn } from "@/components/data-table";
import type { FishSalesHistoryRow } from "@/features/reports";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";

/**
 * The Fish Detail page's own Sales History column set: Invoice Number,
 * Invoice Date, Customer, Boat, Trip, Quantity, Unit Price, Revenue
 * (TASKS.md Sprint 11 Session 4 Phase B "SALES HISTORY"). Row click
 * navigates to the existing Invoice Detail page.
 */
export function getFishSalesHistoryColumns(): DataTableColumn<FishSalesHistoryRow>[] {
  return [
    {
      accessorKey: "invoiceNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Invoice Number" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{row.original.invoiceNumber}</span>,
    },
    {
      accessorKey: "invoiceDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Invoice Date" />,
      enableSorting: false,
      cell: ({ row }) => formatDate(row.original.invoiceDate),
    },
    {
      accessorKey: "customerName",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Customer" />,
      enableSorting: false,
    },
    {
      accessorKey: "boatName",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Boat" />,
      enableSorting: false,
      cell: ({ row }) => row.original.boatName ?? "—",
    },
    {
      accessorKey: "tripNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Trip" />,
      enableSorting: false,
      cell: ({ row }) => row.original.tripNumber ?? "—",
    },
    {
      accessorKey: "quantity",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Quantity" />,
      enableSorting: false,
      meta: { align: "right" },
    },
    {
      accessorKey: "unitPrice",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Unit Price" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.unitPrice),
      meta: { align: "right" },
    },
    {
      accessorKey: "revenue",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Revenue" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.revenue),
      meta: { align: "right" },
    },
  ];
}
