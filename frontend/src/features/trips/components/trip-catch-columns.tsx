"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import type { Fish } from "@/features/fish";
import { FISH_UNIT_LABELS } from "@/features/fish";
import type { TripCatch } from "@/features/trips/types/trip-catch";
import { formatDate } from "@/utils/format-date";
import { formatQuantity } from "@/utils/format-number";

function formatCatchQuantity(value: string, fish: Fish | undefined): string {
  const quantity = formatQuantity(value);
  return fish ? `${quantity} ${FISH_UNIT_LABELS[fish.unit]}` : quantity;
}

/**
 * The Trip Catch sub-table's column set: Fish, Grade, Quantity Caught,
 * Available/Sold/Waste Quantity, Landing Date, Landing Port, Remarks - every
 * field `TripCatchResponse` carries (app/modules/trip_catches/schemas.py)
 * except id/tenant_id/trip_id (implicit - the table is already scoped to
 * one trip) and created_at/updated_at (audit detail, not this compact
 * embedded view's concern, unlike the Trip Detail page's own field lists).
 * Sorting is disabled on every column since this table has no sort UI (see
 * `TripCatchTable`).
 *
 * `fishById` resolves each row's `fish_id` to its name and unit (Fish's own
 * `unit`, not invented) - `TripCatchResponse` carries no nested fish object.
 */
export function getTripCatchColumns(
  fishById: Map<string, Fish>,
  rowActions: (tripCatch: TripCatch) => DataTableAction<TripCatch>[]
): DataTableColumn<TripCatch>[] {
  return [
    {
      id: "fish",
      accessorKey: "fishId",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Fish" />,
      enableSorting: false,
      cell: ({ row }) => fishById.get(row.original.fishId)?.name ?? "—",
    },
    {
      accessorKey: "grade",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Grade" />,
      enableSorting: false,
      cell: ({ row }) => row.original.grade ?? "—",
    },
    {
      accessorKey: "quantityCaught",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Quantity Caught" />,
      enableSorting: false,
      cell: ({ row }) => formatCatchQuantity(row.original.quantityCaught, fishById.get(row.original.fishId)),
      meta: { align: "right" },
    },
    {
      accessorKey: "availableQuantity",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Available" />,
      enableSorting: false,
      cell: ({ row }) => formatCatchQuantity(row.original.availableQuantity, fishById.get(row.original.fishId)),
      meta: { align: "right" },
    },
    {
      accessorKey: "soldQuantity",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Sold" />,
      enableSorting: false,
      cell: ({ row }) => formatCatchQuantity(row.original.soldQuantity, fishById.get(row.original.fishId)),
      meta: { align: "right" },
    },
    {
      accessorKey: "wasteQuantity",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Waste" />,
      enableSorting: false,
      cell: ({ row }) => formatCatchQuantity(row.original.wasteQuantity, fishById.get(row.original.fishId)),
      meta: { align: "right" },
    },
    {
      accessorKey: "landingDate",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Landing Date" />,
      enableSorting: false,
      cell: ({ row }) => formatDate(row.original.landingDate),
    },
    {
      accessorKey: "landingPort",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Landing Port" />,
      enableSorting: false,
      cell: ({ row }) => row.original.landingPort ?? "—",
    },
    {
      accessorKey: "remarks",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Remarks" />,
      enableSorting: false,
      cell: ({ row }) => row.original.remarks ?? "—",
    },
    createRowActionsColumn<TripCatch>(rowActions),
  ];
}
