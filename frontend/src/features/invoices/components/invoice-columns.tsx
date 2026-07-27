"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import {
  INVOICE_STATUS_BADGE_VARIANT,
  INVOICE_STATUS_LABELS,
} from "@/features/invoices/constants/invoice-status";
import type { Invoice } from "@/features/invoices/types/invoice";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";

/**
 * The Invoices table's column set: Invoice Number, Company, Invoice Date,
 * Due Date, Status, Total Amount, Balance Amount, Created At, Actions,
 * mirroring `getTripColumns`. Only invoice_number/invoice_date/created_at
 * are sortable — matching the backend's `_SORTABLE_FIELDS`
 * (app/modules/invoices/schemas.py) exactly, since sorting is server-side.
 * `companyNameById` resolves each row's `company_id` to a display name —
 * `InvoiceResponse` carries no nested company object (see
 * `use-company-options.ts`).
 */
export function getInvoiceColumns(
  rowActions: (invoice: Invoice) => DataTableAction<Invoice>[],
  companyNameById: Map<string, string>
): DataTableColumn<Invoice>[] {
  return [
    {
      // Explicit `id` (not left to default to the camelCase `accessorKey`)
      // because sorting state uses this column's `id` as the sort field,
      // and the backend's sortable fields are snake_case — without this,
      // clicking the header would send `sort=invoiceNumber` and the backend
      // would 422 it as an unrecognized field.
      id: "invoice_number",
      accessorKey: "invoiceNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Invoice Number" />,
      cell: ({ row }) => <span className="font-medium">{row.original.invoiceNumber ?? "—"}</span>,
    },
    {
      id: "company",
      accessorKey: "companyId",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Company" />,
      enableSorting: false,
      cell: ({ row }) => companyNameById.get(row.original.companyId) ?? "—",
    },
    {
      id: "invoice_date",
      accessorKey: "invoiceDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Invoice Date" />,
      cell: ({ row }) => formatDate(row.original.invoiceDate),
    },
    {
      accessorKey: "dueDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Due Date" />,
      enableSorting: false,
      cell: ({ row }) => (row.original.dueDate ? formatDate(row.original.dueDate) : "—"),
    },
    {
      accessorKey: "status",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
      enableSorting: false,
      cell: ({ row }) => (
        <Badge variant={INVOICE_STATUS_BADGE_VARIANT[row.original.status]}>
          {INVOICE_STATUS_LABELS[row.original.status]}
        </Badge>
      ),
    },
    {
      accessorKey: "totalAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Total Amount" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.totalAmount),
      meta: { align: "right" },
    },
    {
      accessorKey: "balanceAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Balance Amount" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.balanceAmount),
      meta: { align: "right" },
    },
    {
      id: "created_at",
      accessorKey: "createdAt",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Created At" />,
      cell: ({ row }) => formatDate(row.original.createdAt),
    },
    createRowActionsColumn<Invoice>(rowActions),
  ];
}
