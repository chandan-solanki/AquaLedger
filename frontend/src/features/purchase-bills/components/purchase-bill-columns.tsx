"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import {
  PURCHASE_BILL_STATUS_BADGE_VARIANT,
  PURCHASE_BILL_STATUS_LABELS,
} from "@/features/purchase-bills/constants/purchase-bill-status";
import type { PurchaseBill } from "@/features/purchase-bills/types/purchase-bill";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";

/**
 * The Purchase Bills table's column set: Bill Number, Supplier, Bill Date,
 * Due Date, Status, Total Amount, Balance Amount, Created At, Actions,
 * mirroring `getInvoiceColumns`. Only bill_date/bill_number/created_at are
 * sortable - matching the backend's `_SORTABLE_FIELDS`
 * (app/modules/purchase/schemas.py) exactly, since sorting is server-side.
 * `supplierNameById` resolves each row's `supplier_id` to a display name -
 * `PurchaseBillResponse` carries no nested supplier object (see
 * `use-supplier-options.ts`). The Actions column is View-only - this module
 * is read-only List + Detail, no Create/Edit/Delete/Post.
 */
export function getPurchaseBillColumns(
  rowActions: (bill: PurchaseBill) => DataTableAction<PurchaseBill>[],
  supplierNameById: Map<string, string>
): DataTableColumn<PurchaseBill>[] {
  return [
    {
      id: "bill_number",
      accessorKey: "billNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Bill Number" />,
      cell: ({ row }) => <span className="font-medium">{row.original.billNumber ?? "—"}</span>,
    },
    {
      id: "supplier",
      accessorKey: "supplierId",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Supplier" />,
      enableSorting: false,
      cell: ({ row }) => supplierNameById.get(row.original.supplierId) ?? "—",
    },
    {
      id: "bill_date",
      accessorKey: "billDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Bill Date" />,
      cell: ({ row }) => formatDate(row.original.billDate),
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
        <Badge variant={PURCHASE_BILL_STATUS_BADGE_VARIANT[row.original.status]}>
          {PURCHASE_BILL_STATUS_LABELS[row.original.status]}
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
    createRowActionsColumn<PurchaseBill>(rowActions),
  ];
}
