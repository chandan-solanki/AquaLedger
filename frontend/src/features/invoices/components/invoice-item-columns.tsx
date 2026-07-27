"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import type { Fish } from "@/features/fish";
import type { InvoiceItem } from "@/features/invoices/types/invoice-item";
import { formatCurrency } from "@/utils/format-currency";
import { formatQuantity, formatRate } from "@/utils/format-number";

/**
 * The Invoice Items sub-table's column set: Fish, Description, Quantity,
 * Rate, Discount %, Taxable Amount, Tax %, Tax Amount, Line Total, Actions -
 * every field `InvoiceItemResponse` carries (app/modules/invoices/schemas.py)
 * except id/tenant_id/invoice_id/line_number (implicit - line_number is
 * purely a server-assigned ordering key, not a viewing concern),
 * trip_catch_id (the entry-time sourcing reference, not a display column),
 * and created_at/updated_at. `discountAmount`/`taxableAmount`/`taxAmount`/
 * `lineTotal` are rendered straight from the server's response - never
 * recalculated here, per "the backend owns financial calculations." No
 * sorting - this table has no sort UI (see `InvoiceItemTable`), mirroring
 * `getTripExpenseColumns`. `fishById` resolves each row's `fish_id` to a
 * display name - `InvoiceItemResponse` carries no nested fish object.
 */
export function getInvoiceItemColumns(
  rowActions: (item: InvoiceItem) => DataTableAction<InvoiceItem>[],
  fishById: Map<string, Fish>
): DataTableColumn<InvoiceItem>[] {
  return [
    {
      accessorKey: "fishId",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Fish" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{fishById.get(row.original.fishId)?.name ?? "—"}</span>,
    },
    {
      accessorKey: "description",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Description" />,
      enableSorting: false,
      cell: ({ row }) => row.original.description ?? "—",
    },
    {
      accessorKey: "quantity",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Quantity" />,
      enableSorting: false,
      cell: ({ row }) => `${formatQuantity(row.original.quantity)} ${row.original.unit}`,
      meta: { align: "right" },
    },
    {
      accessorKey: "rate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Rate" />,
      enableSorting: false,
      cell: ({ row }) => formatRate(row.original.rate),
      meta: { align: "right" },
    },
    {
      accessorKey: "discountPercent",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Discount %" />,
      enableSorting: false,
      cell: ({ row }) => `${row.original.discountPercent}%`,
      meta: { align: "right" },
    },
    {
      accessorKey: "taxableAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Taxable Amount" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.taxableAmount),
      meta: { align: "right" },
    },
    {
      accessorKey: "taxRate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Tax %" />,
      enableSorting: false,
      cell: ({ row }) => `${row.original.taxRate}%`,
      meta: { align: "right" },
    },
    {
      accessorKey: "taxAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Tax Amount" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.taxAmount),
      meta: { align: "right" },
    },
    {
      accessorKey: "lineTotal",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Line Total" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{formatCurrency(row.original.lineTotal)}</span>,
      meta: { align: "right" },
    },
    createRowActionsColumn<InvoiceItem>(rowActions),
  ];
}
