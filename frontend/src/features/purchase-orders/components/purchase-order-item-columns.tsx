"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import type { PurchaseOrderItem } from "@/features/purchase-orders/types/purchase-order-item";
import { formatCurrency } from "@/utils/format-currency";
import { formatQuantity, formatRate } from "@/utils/format-number";

/**
 * The Purchase Order Items sub-table's column set: Description, Quantity,
 * Rate, Discount %, Taxable Amount, Tax %, Tax Amount, Line Total, Billed,
 * Remaining, Actions - every field `PurchaseOrderItemResponse` carries
 * (app/modules/purchase_orders/schemas.py) except id/tenant_id/
 * purchase_order_id/line_number (implicit) and created_at/updated_at,
 * mirroring `getPurchaseBillItemColumns`. There is no Fish column - a
 * purchase order line has no fish_id. The Actions column renders whatever
 * `purchase-order-item-row-actions.tsx` supplies - Edit/Delete, draft-only.
 * No sorting - this table has no sort UI.
 *
 * Billed/Remaining (Sprint 12 Session 12) are derived, quantity-based
 * figures from `GET /purchase-orders/{id}/items`
 * (`PurchaseOrderItemBillingResponse`) - always present in practice since
 * this table is only ever fed by that one endpoint, but the underlying
 * type keeps them optional (see `PurchaseOrderItem`'s own docstring), so
 * both columns fall back to the item's own `quantity`/`"0"` if somehow
 * absent, rather than rendering `undefined`.
 */
export function getPurchaseOrderItemColumns(
  rowActions: (item: PurchaseOrderItem) => DataTableAction<PurchaseOrderItem>[]
): DataTableColumn<PurchaseOrderItem>[] {
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
    {
      accessorKey: "billedQuantity",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Billed" />,
      enableSorting: false,
      cell: ({ row }) => `${formatQuantity(row.original.billedQuantity ?? "0")} ${row.original.unit}`,
      meta: { align: "right" },
    },
    {
      accessorKey: "remainingQuantity",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Remaining" />,
      enableSorting: false,
      cell: ({ row }) => (
        <span className="font-medium">
          {formatQuantity(row.original.remainingQuantity ?? row.original.quantity)} {row.original.unit}
        </span>
      ),
      meta: { align: "right" },
    },
    createRowActionsColumn<PurchaseOrderItem>(rowActions),
  ];
}
