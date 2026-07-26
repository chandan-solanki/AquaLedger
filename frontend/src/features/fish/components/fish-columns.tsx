"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { FISH_STATUS_BADGE_VARIANT, FISH_STATUS_LABELS, toFishStatus } from "@/features/fish/constants/fish-status";
import { FISH_UNIT_LABELS } from "@/features/fish/types/fish";
import type { Fish } from "@/features/fish/types/fish";
import { formatDate } from "@/utils/format-date";

/**
 * The Fish table's column set: Code, Fish Name, Scientific Name, Category,
 * Unit, Status, Created At, Actions, mirroring `getCompanyColumns`. Only
 * name/code/created_at/updated_at are sortable — matching the backend's
 * `_SORTABLE_FIELDS` (app/modules/fish/schemas.py) exactly, since sorting is
 * server-side.
 */
export function getFishColumns(rowActions: (fish: Fish) => DataTableAction<Fish>[]): DataTableColumn<Fish>[] {
  return [
    {
      accessorKey: "code",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Code" />,
    },
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Fish Name" />,
      cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
    },
    {
      accessorKey: "scientificName",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Scientific Name" />,
      enableSorting: false,
      cell: ({ row }) => row.original.scientificName ?? "—",
    },
    {
      accessorKey: "category",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Category" />,
      enableSorting: false,
      cell: ({ row }) => row.original.category ?? "—",
    },
    {
      accessorKey: "unit",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Unit" />,
      enableSorting: false,
      cell: ({ row }) => FISH_UNIT_LABELS[row.original.unit],
    },
    {
      id: "status",
      accessorKey: "isActive",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
      enableSorting: false,
      cell: ({ row }) => {
        const status = toFishStatus(row.original.isActive);
        return <Badge variant={FISH_STATUS_BADGE_VARIANT[status]}>{FISH_STATUS_LABELS[status]}</Badge>;
      },
    },
    {
      // `id` is explicit (not left to default to `accessorKey`) because
      // sorting state uses this column's `id` as the sort field, and the
      // backend's sortable fields are snake_case (`created_at`) while
      // `Fish`'s own field is camelCase (`createdAt`) — without this,
      // clicking the header would send `sort=createdAt` and the backend
      // would 422 it as an unrecognized field.
      id: "created_at",
      accessorKey: "createdAt",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Created At" />,
      cell: ({ row }) => formatDate(row.original.createdAt),
    },
    createRowActionsColumn<Fish>(rowActions),
  ];
}
