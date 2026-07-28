"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import type { PurchaseBillItem } from "@/features/purchase-bills/types/purchase-bill-item";
import { formatCurrency } from "@/utils/format-currency";
import { formatQuantity, formatRate } from "@/utils/format-number";

/**
 * The Purchase Bill Items sub-table's column set: Description, Quantity,
 * Rate, Discount %, Taxable Amount, Tax %, Tax Amount, Line Total, Actions -
 * every field `PurchaseBillItemResponse` carries (app/modules/purchase/
 * schemas.py) except id/tenant_id/purchase_bill_id/line_number (implicit -
 * line_number is purely a server-assigned ordering key, not a viewing
 * concern) and created_at/updated_at, mirroring `getInvoiceItemColumns`.
 * There is no Fish column - a purchase line has no fish_id (unlike
 * `InvoiceItem`). The Actions column renders whatever
 * `purchase-bill-item-row-actions.tsx` supplies - Edit/Delete, draft-only.
 * No sorting - this table has no sort UI, mirroring `getInvoiceItemColumns`.
 */
export function getPurchaseBillItemColumns(
  rowActions: (item: PurchaseBillItem) => DataTableAction<PurchaseBillItem>[]
): DataTableColumn<PurchaseBillItem>[] {
  return [
    {
      accessorKey: "description",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Description" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{row.original.description ?? "—"}</span>,
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
    createRowActionsColumn<PurchaseBillItem>(rowActions),
  ];
}
