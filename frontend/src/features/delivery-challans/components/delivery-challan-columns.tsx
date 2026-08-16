"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import {
  DELIVERY_CHALLAN_STATUS_BADGE_VARIANT,
  DELIVERY_CHALLAN_STATUS_LABELS,
} from "@/features/delivery-challans/constants/delivery-challan-status";
import type { DeliveryChallan } from "@/features/delivery-challans/types/delivery-challan";
import type { Invoice } from "@/features/invoices";
import { formatDate } from "@/utils/format-date";

/**
 * The Delivery Challans table's column set: Challan Number, Challan Date,
 * Customer, Invoice, Status, Created At, Actions, mirroring
 * `getPurchaseOrderColumns`. Only challan_date/challan_number/created_at
 * are sortable - matching the backend's `_SORTABLE_FIELDS`
 * (app/modules/delivery_challans/schemas.py) exactly, since sorting is
 * server-side. There is deliberately no Total Quantity column -
 * `DeliveryChallanResponse` carries no item summary of any kind, and this
 * table never invents one. `invoiceById`/`companyNameById` resolve each
 * row's `invoice_id` to its invoice number and billed customer name -
 * `DeliveryChallanResponse` carries only `invoice_id`, never a nested
 * invoice or company.
 */
export function getDeliveryChallanColumns(
  rowActions: (challan: DeliveryChallan) => DataTableAction<DeliveryChallan>[],
  invoiceById: Map<string, Invoice>,
  companyNameById: Map<string, string>
): DataTableColumn<DeliveryChallan>[] {
  return [
    {
      id: "challan_number",
      accessorKey: "challanNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Challan Number" />,
      cell: ({ row }) => <span className="font-medium">{row.original.challanNumber ?? "—"}</span>,
    },
    {
      id: "challan_date",
      accessorKey: "challanDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Challan Date" />,
      cell: ({ row }) => formatDate(row.original.challanDate),
    },
    {
      id: "customer",
      accessorKey: "invoiceId",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Customer" />,
      enableSorting: false,
      cell: ({ row }) => {
        const invoice = invoiceById.get(row.original.invoiceId);
        return (invoice && companyNameById.get(invoice.companyId)) ?? "—";
      },
    },
    {
      id: "invoice",
      accessorKey: "invoiceId",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Invoice" />,
      enableSorting: false,
      cell: ({ row }) => invoiceById.get(row.original.invoiceId)?.invoiceNumber ?? "—",
    },
    {
      accessorKey: "status",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
      enableSorting: false,
      cell: ({ row }) => (
        <Badge variant={DELIVERY_CHALLAN_STATUS_BADGE_VARIANT[row.original.status]}>
          {DELIVERY_CHALLAN_STATUS_LABELS[row.original.status]}
        </Badge>
      ),
    },
    {
      id: "created_at",
      accessorKey: "createdAt",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Created At" />,
      cell: ({ row }) => formatDate(row.original.createdAt),
    },
    createRowActionsColumn<DeliveryChallan>(rowActions),
  ];
}
