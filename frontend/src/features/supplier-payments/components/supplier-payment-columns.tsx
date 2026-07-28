"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { SUPPLIER_PAYMENT_METHOD_LABELS } from "@/features/supplier-payments/constants/supplier-payment-method";
import {
  SUPPLIER_PAYMENT_STATUS_BADGE_VARIANT,
  SUPPLIER_PAYMENT_STATUS_LABELS,
} from "@/features/supplier-payments/constants/supplier-payment-status";
import type { SupplierPayment } from "@/features/supplier-payments/types/supplier-payment";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";

/**
 * The Supplier Payments table's column set: Payment Number, Supplier,
 * Payment Date, Amount, Allocated, Unallocated, Method, Reference, Status,
 * Created At, Actions, mirroring `getPaymentColumns`. Only payment_date/
 * payment_number/created_at are sortable - matching the backend's
 * `_SORTABLE_FIELDS` (app/modules/supplier_payments/schemas.py) exactly,
 * since sorting is server-side. `supplierNameById` resolves each row's
 * `supplier_id` to a display name - `SupplierPaymentResponse` carries no
 * nested supplier object (see `use-supplier-options.ts`). The Actions
 * column renders whatever `supplier-payment-row-actions.tsx` supplies -
 * empty this session (Sprint 9 Session 1 is list-foundation only).
 */
export function getSupplierPaymentColumns(
  rowActions: (payment: SupplierPayment) => DataTableAction<SupplierPayment>[],
  supplierNameById: Map<string, string>
): DataTableColumn<SupplierPayment>[] {
  return [
    {
      id: "payment_number",
      accessorKey: "paymentNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Payment Number" />,
      cell: ({ row }) => <span className="font-medium">{row.original.paymentNumber ?? "—"}</span>,
    },
    {
      id: "supplier",
      accessorKey: "supplierId",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Supplier" />,
      enableSorting: false,
      cell: ({ row }) => supplierNameById.get(row.original.supplierId) ?? "—",
    },
    {
      id: "payment_date",
      accessorKey: "paymentDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Payment Date" />,
      cell: ({ row }) => formatDate(row.original.paymentDate),
    },
    {
      accessorKey: "amount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Amount" />,
      enableSorting: false,
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
      cell: ({ row }) => SUPPLIER_PAYMENT_METHOD_LABELS[row.original.paymentMethod],
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
        <Badge variant={SUPPLIER_PAYMENT_STATUS_BADGE_VARIANT[row.original.status]}>
          {SUPPLIER_PAYMENT_STATUS_LABELS[row.original.status]}
        </Badge>
      ),
    },
    {
      id: "created_at",
      accessorKey: "createdAt",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Created At" />,
      cell: ({ row }) => formatDate(row.original.createdAt),
    },
    createRowActionsColumn<SupplierPayment>(rowActions),
  ];
}
