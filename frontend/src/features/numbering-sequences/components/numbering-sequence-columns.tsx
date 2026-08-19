"use client";

import { DataTableColumnHeader } from "@/components/data-table";
import type { DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import type { NumberingSequence } from "@/features/numbering-sequences/types/numbering-sequence";

const STATUS_LABELS: Record<NumberingSequence["status"], string> = {
  active: "Active",
  not_started: "Not started",
};

/**
 * Settings > Numbering Sequences column set (Sprint 14 Session 2): Document,
 * Prefix, Fiscal Year, Current, Next Number, Format, Status. Read-only - no
 * Actions column, since the audit backing this page found prefix/fiscal
 * year are hardcoded per module today (not stored anywhere per-tenant), so
 * there is nothing safe to edit yet without inventing unrequested
 * configuration.
 */
export function getNumberingSequenceColumns(): DataTableColumn<NumberingSequence>[] {
  return [
    {
      accessorKey: "documentLabel",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Document" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{row.original.documentLabel}</span>,
    },
    {
      accessorKey: "prefix",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Prefix" />,
      enableSorting: false,
      cell: ({ row }) => row.original.prefix,
    },
    {
      accessorKey: "fiscalYear",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Fiscal Year" />,
      enableSorting: false,
      cell: ({ row }) => row.original.fiscalYear,
    },
    {
      accessorKey: "currentNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Current" />,
      enableSorting: false,
      cell: ({ row }) => String(row.original.currentNumber).padStart(5, "0"),
      meta: { align: "right" },
    },
    {
      accessorKey: "nextNumberFormatted",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Next Number" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{row.original.nextNumberFormatted}</span>,
    },
    {
      accessorKey: "numberFormat",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Format" />,
      enableSorting: false,
      cell: ({ row }) => (
        <span className="text-muted-foreground">{row.original.numberFormat}</span>
      ),
    },
    {
      accessorKey: "status",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
      enableSorting: false,
      cell: ({ row }) => (
        <Badge variant={row.original.status === "active" ? "default" : "outline"}>
          {STATUS_LABELS[row.original.status]}
        </Badge>
      ),
    },
  ];
}
