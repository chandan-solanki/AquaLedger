"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { TRIP_STATUS_BADGE_VARIANT, TRIP_STATUS_LABELS } from "@/features/trips/constants/trip-status";
import { TRIP_TYPE_LABELS } from "@/features/trips/constants/trip-type";
import type { Trip } from "@/features/trips/types/trip";
import { formatDateTime } from "@/utils/format-date";

/**
 * The Trips table's column set: Trip Number, Boat, Trip Type, Departure,
 * Expected Return, Actual Return, Status, Created At, Actions, mirroring
 * `getBoatColumns`. Only trip_number/departure_datetime/created_at are
 * sortable — matching the backend's `_SORTABLE_FIELDS`
 * (app/modules/trips/schemas.py) exactly, since sorting is server-side.
 * `boatNameById` resolves each row's `boat_id` to a display name —
 * `TripResponse` carries no nested boat object (see `use-boat-options.ts`).
 */
export function getTripColumns(
  rowActions: (trip: Trip) => DataTableAction<Trip>[],
  boatNameById: Map<string, string>
): DataTableColumn<Trip>[] {
  return [
    {
      // Explicit `id` (not left to default to the camelCase `accessorKey`)
      // because sorting state uses this column's `id` as the sort field,
      // and the backend's sortable fields are snake_case — without this,
      // clicking the header would send `sort=tripNumber` and the backend
      // would 422 it as an unrecognized field.
      id: "trip_number",
      accessorKey: "tripNumber",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Trip Number" />,
      cell: ({ row }) => <span className="font-medium">{row.original.tripNumber}</span>,
    },
    {
      id: "boat",
      accessorKey: "boatId",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Boat" />,
      enableSorting: false,
      cell: ({ row }) => boatNameById.get(row.original.boatId) ?? "—",
    },
    {
      accessorKey: "tripType",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Trip Type" />,
      enableSorting: false,
      cell: ({ row }) => TRIP_TYPE_LABELS[row.original.tripType],
    },
    {
      id: "departure_datetime",
      accessorKey: "departureDatetime",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Departure" />,
      cell: ({ row }) => formatDateTime(row.original.departureDatetime),
    },
    {
      accessorKey: "expectedReturnDatetime",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Expected Return" />,
      enableSorting: false,
      cell: ({ row }) =>
        row.original.expectedReturnDatetime ? formatDateTime(row.original.expectedReturnDatetime) : "—",
    },
    {
      accessorKey: "actualReturnDatetime",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Actual Return" />,
      enableSorting: false,
      cell: ({ row }) =>
        row.original.actualReturnDatetime ? formatDateTime(row.original.actualReturnDatetime) : "—",
    },
    {
      accessorKey: "status",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
      enableSorting: false,
      cell: ({ row }) => (
        <Badge variant={TRIP_STATUS_BADGE_VARIANT[row.original.status]}>
          {TRIP_STATUS_LABELS[row.original.status]}
        </Badge>
      ),
    },
    {
      id: "created_at",
      accessorKey: "createdAt",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Created At" />,
      cell: ({ row }) => formatDateTime(row.original.createdAt),
    },
    createRowActionsColumn<Trip>(rowActions),
  ];
}
