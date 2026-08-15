"use client";

import { DataTableColumnHeader } from "@/components/data-table";
import type { DataTableColumn } from "@/components/data-table";
import type { EntityType } from "@/features/reports/constants/entity-type";
import type { AgingReportRow } from "@/features/reports/types/aging-report";
import { formatCurrency } from "@/utils/format-currency";

/**
 * The Aging Report table's column set: Customer/Supplier, Current, 1-30,
 * 31-60, 61-90, 90+, Total (TASKS.md Sprint 11 Session 3 Phase B). Only
 * the entity name column's label differs by `entityType` - the bucket
 * columns are generic. `risk_level` is not one of this report's listed
 * "Columns" (see AgingReportRow's own docstring on the backend), so it is
 * deliberately not rendered here - it only exists server-side to power the
 * `risk` filter.
 */
export function getAgingReportColumns(entityType: EntityType): DataTableColumn<AgingReportRow>[] {
  const isCustomer = entityType === "customer";
  return [
    {
      accessorKey: "entityName",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={isCustomer ? "Customer" : "Supplier"} />
      ),
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{row.original.entityName}</span>,
    },
    {
      accessorKey: "currentAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Current" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.currentAmount),
      meta: { align: "right" },
    },
    {
      accessorKey: "days1To30",
      header: ({ column }) => <DataTableColumnHeader column={column} title="1-30 Days" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.days1To30),
      meta: { align: "right" },
    },
    {
      accessorKey: "days31To60",
      header: ({ column }) => <DataTableColumnHeader column={column} title="31-60 Days" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.days31To60),
      meta: { align: "right" },
    },
    {
      accessorKey: "days61To90",
      header: ({ column }) => <DataTableColumnHeader column={column} title="61-90 Days" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.days61To90),
      meta: { align: "right" },
    },
    {
      accessorKey: "days90Plus",
      header: ({ column }) => <DataTableColumnHeader column={column} title="90+ Days" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.days90Plus),
      meta: { align: "right" },
    },
    {
      accessorKey: "total",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Total" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{formatCurrency(row.original.total)}</span>,
      meta: { align: "right" },
    },
  ];
}
