"use client";

import { DataTableColumnHeader } from "@/components/data-table";
import type { DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import type { SalesReportInvoiceStatus, SalesReportRow } from "@/features/reports/types/sales-report";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";

/**
 * Local copy of `INVOICE_STATUS_LABELS`/`INVOICE_STATUS_BADGE_VARIANT`
 * (features/invoices/constants/invoice-status.ts) - Reports does not import
 * another feature's internals (mirrors `useCustomerOptions`'s own stated
 * rule), so this small map is duplicated here rather than shared.
 */
const SALES_REPORT_STATUS_LABELS: Record<SalesReportInvoiceStatus, string> = {
  draft: "Draft",
  issued: "Issued",
  partially_paid: "Partially Paid",
  paid: "Paid",
  cancelled: "Cancelled",
};

const SALES_REPORT_STATUS_BADGE_VARIANT: Record<
  SalesReportInvoiceStatus,
  "default" | "secondary" | "outline" | "destructive"
> = {
  draft: "outline",
  issued: "default",
  partially_paid: "secondary",
  paid: "secondary",
  cancelled: "destructive",
};

/**
 * The Sales Report table's column set: Invoice Number, Invoice Date, Due
 * Date, Customer, Invoice Amount, Paid Amount, Outstanding Amount, Status
 * (TASKS.md Sprint 11 Session 3). No sorting - the backend always orders
 * `invoice_date DESC, invoice_number DESC`, a fixed order. Row click
 * navigates to the existing Invoice Detail page (wired by the page
 * component via `onRowClick`), so there is no dedicated actions column.
 */
export function getSalesReportColumns(): DataTableColumn<SalesReportRow>[] {
  return [
    {
      accessorKey: "invoiceNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Invoice Number" />,
      enableSorting: false,
      cell: ({ row }) => <span className="font-medium">{row.original.invoiceNumber}</span>,
    },
    {
      accessorKey: "invoiceDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Invoice Date" />,
      enableSorting: false,
      cell: ({ row }) => formatDate(row.original.invoiceDate),
    },
    {
      accessorKey: "dueDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Due Date" />,
      enableSorting: false,
      cell: ({ row }) => (row.original.dueDate ? formatDate(row.original.dueDate) : "—"),
    },
    {
      accessorKey: "customerName",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Customer" />,
      enableSorting: false,
    },
    {
      accessorKey: "invoiceAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Invoice Amount" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.invoiceAmount),
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
        <Badge variant={SALES_REPORT_STATUS_BADGE_VARIANT[row.original.status]}>
          {SALES_REPORT_STATUS_LABELS[row.original.status]}
        </Badge>
      ),
    },
  ];
}
