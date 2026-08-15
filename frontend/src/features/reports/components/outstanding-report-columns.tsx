"use client";

import { DataTableColumnHeader } from "@/components/data-table";
import type { DataTableColumn } from "@/components/data-table";
import type { EntityType } from "@/features/reports/constants/entity-type";
import { RiskBadge } from "@/features/reports/components/risk-badge";
import type { OutstandingReportRow } from "@/features/reports/types/outstanding-report";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";

/**
 * The Outstanding Report table's column set (TASKS.md Sprint 11 Session 3
 * Phase B). One column-definition function serves both tabs - the backend
 * already returns a single generic row shape (`entity_name`/
 * `last_transaction_date`/`pending_count`, never `customer_name`/
 * `last_invoice_date`/`pending_invoice_count`), so only the column
 * *labels* differ by `entityType`, never the data access. No sorting - the
 * backend always orders `Outstanding DESC, Then Name ASC`, a fixed order.
 */
export function getOutstandingReportColumns(
  entityType: EntityType
): DataTableColumn<OutstandingReportRow>[] {
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
      accessorKey: "outstandingAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Outstanding Amount" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.outstandingAmount),
      meta: { align: "right" },
    },
    {
      accessorKey: "overdueAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Overdue Amount" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.overdueAmount),
      meta: { align: "right" },
    },
    {
      accessorKey: "currentAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Current Amount" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.currentAmount),
      meta: { align: "right" },
    },
    {
      accessorKey: "lastTransactionDate",
      header: ({ column }) => (
        <DataTableColumnHeader
          column={column}
          title={isCustomer ? "Last Invoice Date" : "Last Purchase Date"}
        />
      ),
      enableSorting: false,
      cell: ({ row }) =>
        row.original.lastTransactionDate ? formatDate(row.original.lastTransactionDate) : "—",
    },
    {
      accessorKey: "lastPaymentDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Last Payment Date" />,
      enableSorting: false,
      cell: ({ row }) =>
        row.original.lastPaymentDate ? formatDate(row.original.lastPaymentDate) : "—",
    },
    {
      accessorKey: "pendingCount",
      header: ({ column }) => (
        <DataTableColumnHeader
          column={column}
          title={isCustomer ? "Pending Invoice Count" : "Pending Bill Count"}
        />
      ),
      enableSorting: false,
      cell: ({ row }) => row.original.pendingCount,
      meta: { align: "right" },
    },
    {
      accessorKey: "riskLevel",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Risk Indicator" />,
      enableSorting: false,
      cell: ({ row }) => <RiskBadge level={row.original.riskLevel} />,
    },
  ];
}
