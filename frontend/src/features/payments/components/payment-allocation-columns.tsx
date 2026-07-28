"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import type { Invoice } from "@/features/invoices";
import type { PaymentAllocation } from "@/features/payments/types/payment-allocation";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";

/**
 * The Payment Allocations sub-table's column set: Invoice Number, Invoice
 * Date, Invoice Total, Allocated Amount, Invoice Balance, Actions - every
 * money/date value rendered straight from the server's own response, never
 * recalculated here, per "the backend owns financial calculations."
 * `PaymentAllocationResponse` carries only `invoice_id`
 * (app/modules/payments/schemas.py) - no invoice_number/invoice_date/
 * total_amount/balance_amount of its own - so `invoiceById` resolves each
 * row's `invoice_id` to the referenced `Invoice` (fetched through the
 * Invoices feature's own public API, see `payment-allocation-table.tsx`).
 * "Invoice Balance" is that invoice's own current `balance_amount`, exactly
 * as the backend returns it - not a point-in-time "balance before this
 * allocation" snapshot, which the backend does not expose anywhere. No
 * sorting - this table has no sort UI, mirroring `getInvoiceItemColumns`.
 */
export function getPaymentAllocationColumns(
  rowActions: (allocation: PaymentAllocation) => DataTableAction<PaymentAllocation>[],
  invoiceById: Map<string, Invoice>
): DataTableColumn<PaymentAllocation>[] {
  return [
    {
      accessorKey: "invoiceId",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Invoice Number" />,
      enableSorting: false,
      cell: ({ row }) => (
        <span className="font-medium">
          {invoiceById.get(row.original.invoiceId)?.invoiceNumber ?? "—"}
        </span>
      ),
    },
    {
      id: "invoice_date",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Invoice Date" />,
      enableSorting: false,
      cell: ({ row }) => {
        const invoice = invoiceById.get(row.original.invoiceId);
        return invoice ? formatDate(invoice.invoiceDate) : "—";
      },
    },
    {
      id: "invoice_total",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Invoice Total" />,
      enableSorting: false,
      cell: ({ row }) => {
        const invoice = invoiceById.get(row.original.invoiceId);
        return invoice ? formatCurrency(invoice.totalAmount) : "—";
      },
      meta: { align: "right" },
    },
    {
      accessorKey: "allocatedAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Allocated Amount" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.allocatedAmount),
      meta: { align: "right" },
    },
    {
      id: "invoice_balance",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Invoice Balance" />,
      enableSorting: false,
      cell: ({ row }) => {
        const invoice = invoiceById.get(row.original.invoiceId);
        return invoice ? formatCurrency(invoice.balanceAmount) : "—";
      },
      meta: { align: "right" },
    },
    createRowActionsColumn<PaymentAllocation>(rowActions),
  ];
}
