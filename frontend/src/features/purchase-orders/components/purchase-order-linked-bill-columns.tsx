"use client";

import Link from "next/link";

import { DataTableColumnHeader } from "@/components/data-table";
import type { DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import {
  PURCHASE_BILL_STATUS_BADGE_VARIANT,
  PURCHASE_BILL_STATUS_LABELS,
} from "@/features/purchase-bills/constants/purchase-bill-status";
import type { PurchaseBillStatus } from "@/features/purchase-bills/types/purchase-bill";
import type { PurchaseOrderLinkedBill } from "@/features/purchase-orders/types/purchase-order-linked-bill";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";

/**
 * The Purchase Order Detail page's "Purchase Bills" section column set:
 * Bill Number, Bill Date, Amount, Status (Sprint 12 Session 13). Read-only -
 * no Actions column, since this table offers nothing but navigation to the
 * bill itself.
 *
 * `status` is a plain `string` on the wire (`purchase_orders` never imports
 * `purchase`'s own `PurchaseStatus` enum - see
 * app/modules/purchase_orders/domain/billing.py's `PurchaseOrderLinkedBill`
 * docstring), so it's cast to `PurchaseBillStatus` here purely for the label/
 * badge lookup, with a same-string fallback if it's ever something the map
 * doesn't recognize.
 *
 * `canViewPurchaseBill` gates Bill Number as a link vs. plain text - the
 * same permission-gated pattern already used for the Supplier name on this
 * page and the Purchase Order reference on the Purchase Bill Detail page:
 * never render a link the caller can't actually follow.
 */
export function getPurchaseOrderLinkedBillColumns(
  canViewPurchaseBill: boolean
): DataTableColumn<PurchaseOrderLinkedBill>[] {
  return [
    {
      accessorKey: "billNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Bill Number" />,
      enableSorting: false,
      cell: ({ row }) => {
        const label = row.original.billNumber ?? "Draft";
        return canViewPurchaseBill ? (
          <Link href={`/purchase-bills/${row.original.id}`} className="font-medium hover:underline">
            {label}
          </Link>
        ) : (
          <span className="font-medium">{label}</span>
        );
      },
    },
    {
      accessorKey: "billDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Bill Date" />,
      enableSorting: false,
      cell: ({ row }) => formatDate(row.original.billDate),
    },
    {
      accessorKey: "totalAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Amount" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.totalAmount),
      meta: { align: "right" },
    },
    {
      accessorKey: "status",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
      enableSorting: false,
      cell: ({ row }) => {
        const status = row.original.status as PurchaseBillStatus;
        return (
          <Badge variant={PURCHASE_BILL_STATUS_BADGE_VARIANT[status] ?? "outline"}>
            {PURCHASE_BILL_STATUS_LABELS[status] ?? row.original.status}
          </Badge>
        );
      },
    },
  ];
}
