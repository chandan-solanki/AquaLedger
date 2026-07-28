"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { PAYMENT_METHOD_LABELS } from "@/features/payments/constants/payment-method";
import {
  PAYMENT_STATUS_BADGE_VARIANT,
  PAYMENT_STATUS_LABELS,
} from "@/features/payments/constants/payment-status";
import type { Payment } from "@/features/payments/types/payment";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";

/**
 * The Payments table's column set: Payment Number, Customer, Payment Date,
 * Amount, Allocated, Unallocated, Method, Reference, Status, Created At,
 * Actions, mirroring `getInvoiceColumns`. Only payment_date/payment_number/
 * amount/created_at are sortable - matching the backend's `_SORTABLE_FIELDS`
 * (app/modules/payments/schemas.py) exactly, since sorting is server-side.
 * `companyNameById` resolves each row's `company_id` to a display name -
 * `PaymentResponse` carries no nested company object (see
 * `use-company-options.ts`). The Actions column renders whatever
 * `payment-row-actions.tsx` supplies - currently View/Edit/Delete, the
 * latter two draft-only.
 */
export function getPaymentColumns(
  rowActions: (payment: Payment) => DataTableAction<Payment>[],
  companyNameById: Map<string, string>
): DataTableColumn<Payment>[] {
  return [
    {
      id: "payment_number",
      accessorKey: "paymentNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Payment Number" />,
      cell: ({ row }) => <span className="font-medium">{row.original.paymentNumber ?? "—"}</span>,
    },
    {
      id: "company",
      accessorKey: "companyId",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Customer" />,
      enableSorting: false,
      cell: ({ row }) => companyNameById.get(row.original.companyId) ?? "—",
    },
    {
      id: "payment_date",
      accessorKey: "paymentDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Payment Date" />,
      cell: ({ row }) => formatDate(row.original.paymentDate),
    },
    {
      id: "amount",
      accessorKey: "amount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Amount" />,
      cell: ({ row }) => formatCurrency(row.original.amount),
      meta: { align: "right" },
    },
    {
      accessorKey: "allocatedAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Allocated" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.allocatedAmount),
      meta: { align: "right" },
    },
    {
      accessorKey: "unallocatedAmount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Unallocated" />,
      enableSorting: false,
      cell: ({ row }) => formatCurrency(row.original.unallocatedAmount),
      meta: { align: "right" },
    },
    {
      accessorKey: "paymentMethod",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Method" />,
      enableSorting: false,
      cell: ({ row }) => PAYMENT_METHOD_LABELS[row.original.paymentMethod],
    },
    {
      accessorKey: "referenceNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Reference" />,
      enableSorting: false,
      cell: ({ row }) => row.original.referenceNumber ?? "—",
    },
    {
      accessorKey: "status",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
      enableSorting: false,
      cell: ({ row }) => (
        <Badge variant={PAYMENT_STATUS_BADGE_VARIANT[row.original.status]}>
          {PAYMENT_STATUS_LABELS[row.original.status]}
        </Badge>
      ),
    },
    {
      id: "created_at",
      accessorKey: "createdAt",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Created At" />,
      cell: ({ row }) => formatDate(row.original.createdAt),
    },
    createRowActionsColumn<Payment>(rowActions),
  ];
}
