"use client";

import { DataTableColumnHeader } from "@/components/data-table";
import type { DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import type { SupplierLedgerEntry } from "@/features/reports/types/supplier-ledger";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";

const TRANSACTION_TYPE_LABELS: Record<SupplierLedgerEntry["transactionType"], string> = {
  purchase_bill: "Purchase Bill",
  supplier_payment: "Supplier Payment",
};

/** Zero renders as an em dash rather than "₹0.00" - standard ledger presentation: a row is either a debit or a credit, never both. */
function formatLedgerAmount(value: string): string {
  return Number(value) === 0 ? "—" : formatCurrency(value);
}

/**
 * The Supplier Ledger table's column set: Date, Reference, Transaction
 * Type, Description, Debit, Credit, Running Balance - mirrors
 * `getCustomerLedgerColumns` exactly, on the buy side. No sorting (the
 * backend always returns entries chronologically) and no row actions
 * (this is a read-only report, not a navigable list).
 */
export function getSupplierLedgerColumns(): DataTableColumn<SupplierLedgerEntry>[] {
  return [
    {
      id: "transaction_date",
      accessorKey: "transactionDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Date" />,
      enableSorting: false,
      cell: ({ row }) => formatDate(row.original.transactionDate),
    },
    {
      accessorKey: "referenceNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Reference" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{row.original.referenceNumber}</span>,
    },
    {
      accessorKey: "transactionType",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Transaction Type" />,
      enableSorting: false,
      cell: ({ row }) => (
        <Badge variant={row.original.transactionType === "purchase_bill" ? "default" : "secondary"}>
          {TRANSACTION_TYPE_LABELS[row.original.transactionType]}
        </Badge>
      ),
    },
    {
      accessorKey: "description",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Description" />,
      enableSorting: false,
    },
    {
      accessorKey: "debit",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Debit" />,
      enableSorting: false,
      cell: ({ row }) => formatLedgerAmount(row.original.debit),
      meta: { align: "right" },
    },
    {
      accessorKey: "credit",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Credit" />,
      enableSorting: false,
      cell: ({ row }) => formatLedgerAmount(row.original.credit),
      meta: { align: "right" },
    },
    {
      accessorKey: "runningBalance",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Running Balance" />,
      enableSorting: false,
      cell: ({ row }) => (
        <span className="font-medium tabular-nums">
          {formatCurrency(row.original.runningBalance)}
        </span>
      ),
      meta: { align: "right" },
    },
  ];
}
