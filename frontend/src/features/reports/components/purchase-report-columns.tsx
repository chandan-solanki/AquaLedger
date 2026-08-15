"use client";

import { DataTableColumnHeader } from "@/components/data-table";
import type { DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import type {
  PurchaseReportBillStatus,
  PurchaseReportRow,
} from "@/features/reports/types/purchase-report";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";

/**
 * Local copy of `PURCHASE_BILL_STATUS_LABELS`/`_BADGE_VARIANT`
 * (features/purchase-bills/constants/purchase-bill-status.ts) - Reports
 * does not import another feature's internals, mirrors
 * `sales-report-columns.tsx`'s own local copy exactly.
 */
const PURCHASE_REPORT_STATUS_LABELS: Record<PurchaseReportBillStatus, string> = {
  draft: "Draft",
  posted: "Posted",
  partially_paid: "Partially Paid",
  paid: "Paid",
  cancelled: "Cancelled",
};

const PURCHASE_REPORT_STATUS_BADGE_VARIANT: Record<
  PurchaseReportBillStatus,
  "default" | "secondary" | "outline" | "destructive"
> = {
  draft: "outline",
  posted: "default",
  partially_paid: "secondary",
  paid: "secondary",
  cancelled: "destructive",
};

/**
 * The Purchase Report table's column set: Bill Number, Bill Date, Due Date,
 * Supplier, Bill Amount, Paid Amount, Outstanding Amount, Status. Mirrors
 * `getSalesReportColumns` exactly, on the buy side.
 */
export function getPurchaseReportColumns(): DataTableColumn<PurchaseReportRow>[] {
  return [
    {
      accessorKey: "billNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Bill Number" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{row.original.billNumber}</span>,
    },
    {
      accessorKey: "billDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Bill Date" />,
      enableSorting: false,
      cell: ({ row }) => formatDate(row.original.billDate),
    },
    {
      accessorKey: "dueDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Due Date" />,
      enableSorting: false,
      cell: ({ row }) => (row.original.dueDate ? formatDate(row.original.dueDate) : "—"),
    },
    {
      accessorKey: "supplierName",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Supplier" />,
      enableSorting: false,
    },
    {
      accessorKey: "billAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Bill Amount" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.billAmount),
      meta: { align: "right" },
    },
    {
      accessorKey: "paidAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Paid Amount" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.paidAmount),
      meta: { align: "right" },
    },
    {
      accessorKey: "outstandingAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Outstanding Amount" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.outstandingAmount),
      meta: { align: "right" },
    },
    {
      accessorKey: "status",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
      enableSorting: false,
      cell: ({ row }) => (
        <Badge variant={PURCHASE_REPORT_STATUS_BADGE_VARIANT[row.original.status]}>
          {PURCHASE_REPORT_STATUS_LABELS[row.original.status]}
        </Badge>
      ),
    },
  ];
}
