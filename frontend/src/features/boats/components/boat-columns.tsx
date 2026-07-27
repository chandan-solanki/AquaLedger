"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { BOAT_STATUS_BADGE_VARIANT, BOAT_STATUS_LABELS, toBoatStatus } from "@/features/boats/constants/boat-status";
import type { Boat } from "@/features/boats/types/boat";
import { formatDate } from "@/utils/format-date";
import { formatQuantity } from "@/utils/format-number";

/**
 * The Boats table's column set: Boat Name, Boat Number (code), Registration
 * Number, Boat Type, Capacity, Status, Created At, Actions, mirroring
 * `getFishColumns`/`getCompanyColumns`. Only name/code/created_at/updated_at
 * are sortable — matching the backend's `_SORTABLE_FIELDS`
 * (app/modules/boats/schemas.py) exactly, since sorting is server-side.
 */
export function getBoatColumns(rowActions: (boat: Boat) => DataTableAction<Boat>[]): DataTableColumn<Boat>[] {
  return [
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Boat Name" />,
      cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
    },
    {
      accessorKey: "code",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Boat Number" />,
    },
    {
      accessorKey: "registrationNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Registration Number" />,
      enableSorting: false,
    },
    {
      accessorKey: "boatType",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Boat Type" />,
      enableSorting: false,
      cell: ({ row }) => row.original.boatType ?? "—",
    },
    {
      accessorKey: "capacityKg",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Capacity (kg)" />,
      enableSorting: false,
      cell: ({ row }) => (row.original.capacityKg ? formatQuantity(row.original.capacityKg) : "—"),
    },
    {
      id: "status",
      accessorKey: "isActive",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
      enableSorting: false,
      cell: ({ row }) => {
        const status = toBoatStatus(row.original.isActive);
        return <Badge variant={BOAT_STATUS_BADGE_VARIANT[status]}>{BOAT_STATUS_LABELS[status]}</Badge>;
      },
    },
    {
      // `id` is explicit (not left to default to `accessorKey`) because
      // sorting state uses this column's `id` as the sort field, and the
      // backend's sortable fields are snake_case (`created_at`) while
      // `Boat`'s own field is camelCase (`createdAt`) — without this,
      // clicking the header would send `sort=createdAt` and the backend
      // would 422 it as an unrecognized field.
      id: "created_at",
      accessorKey: "createdAt",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Created At" />,
      cell: ({ row }) => formatDate(row.original.createdAt),
    },
    createRowActionsColumn<Boat>(rowActions),
  ];
}
