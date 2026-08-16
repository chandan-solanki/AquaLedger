"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import {
  PURCHASE_ORDER_STATUS_BADGE_VARIANT,
  PURCHASE_ORDER_STATUS_LABELS,
} from "@/features/purchase-orders/constants/purchase-order-status";
import type { PurchaseOrder } from "@/features/purchase-orders/types/purchase-order";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";

/**
 * The Purchase Orders table's column set: PO Number, Supplier, PO Date,
 * Expected Delivery Date, Status, Total Amount, Created At, Actions,
 * mirroring `getPurchaseBillColumns`. Only order_date/po_number/created_at
 * are sortable - matching the backend's `_SORTABLE_FIELDS`
 * (app/modules/purchase_orders/schemas.py) exactly, since sorting is
 * server-side. `supplierNameById` resolves each row's `supplier_id` to a
 * display name - `PurchaseOrderResponse` carries no nested supplier object.
 * There is no Balance Amount column - a purchase order is never paid.
 */
export function getPurchaseOrderColumns(
  rowActions: (order: PurchaseOrder) => DataTableAction<PurchaseOrder>[],
  supplierNameById: Map<string, string>
): DataTableColumn<PurchaseOrder>[] {
  return [
    {
      id: "po_number",
      accessorKey: "poNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="PO Number" />,
      cell: ({ row }) => <span className="font-medium">{row.original.poNumber ?? "—"}</span>,
    },
    {
      id: "supplier",
      accessorKey: "supplierId",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Supplier" />,
      enableSorting: false,
      cell: ({ row }) => supplierNameById.get(row.original.supplierId) ?? "—",
    },
    {
      id: "order_date",
      accessorKey: "orderDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="PO Date" />,
      cell: ({ row }) => formatDate(row.original.orderDate),
    },
    {
      accessorKey: "expectedDeliveryDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Expected Delivery" />,
      enableSorting: false,
      cell: ({ row }) =>
        row.original.expectedDeliveryDate ? formatDate(row.original.expectedDeliveryDate) : "—",
    },
    {
      accessorKey: "status",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
      enableSorting: false,
      cell: ({ row }) => (
        <Badge variant={PURCHASE_ORDER_STATUS_BADGE_VARIANT[row.original.status]}>
          {PURCHASE_ORDER_STATUS_LABELS[row.original.status]}
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
      id: "created_at",
      accessorKey: "createdAt",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Created At" />,
      cell: ({ row }) => formatDate(row.original.createdAt),
    },
    createRowActionsColumn<PurchaseOrder>(rowActions),
  ];
}
