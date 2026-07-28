"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import {
  SUPPLIER_STATUS_BADGE_VARIANT,
  SUPPLIER_STATUS_LABELS,
} from "@/features/suppliers/constants/supplier-status";
import type { Supplier } from "@/features/suppliers/types/supplier";
import { formatDate } from "@/utils/format-date";

/**
 * The Suppliers table's column set: Supplier Name, Code, GSTIN, Phone, City,
 * Status, Created At, Actions, mirroring `getCompanyColumns`. Only
 * name/code/created_at are sortable - matching the backend's
 * `_SORTABLE_FIELDS` (app/modules/suppliers/schemas.py) exactly, since
 * sorting is server-side.
 */
export function getSupplierColumns(
  rowActions: (supplier: Supplier) => DataTableAction<Supplier>[]
): DataTableColumn<Supplier>[] {
  return [
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Supplier Name" />,
      cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
    },
    {
      accessorKey: "code",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Code" />,
    },
    {
      accessorKey: "gstin",
      header: ({ column }) => <DataTableColumnHeader column={column} title="GSTIN" />,
      enableSorting: false,
      cell: ({ row }) => row.original.gstin ?? "—",
    },
    {
      accessorKey: "phone",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Phone" />,
      enableSorting: false,
      cell: ({ row }) => row.original.phone ?? "—",
    },
    {
      accessorKey: "city",
      header: ({ column }) => <DataTableColumnHeader column={column} title="City" />,
      enableSorting: false,
      cell: ({ row }) => row.original.city ?? "—",
    },
    {
      accessorKey: "status",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
      enableSorting: false,
      cell: ({ row }) => (
        <Badge variant={SUPPLIER_STATUS_BADGE_VARIANT[row.original.status]}>
          {SUPPLIER_STATUS_LABELS[row.original.status]}
        </Badge>
      ),
    },
    {
      id: "created_at",
      accessorKey: "createdAt",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Created At" />,
      cell: ({ row }) => formatDate(row.original.createdAt),
    },
    createRowActionsColumn<Supplier>(rowActions),
  ];
}
