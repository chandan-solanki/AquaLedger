"use client";

import { DataTableColumnHeader } from "@/components/data-table";
import type { DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import type { RoleListItem } from "@/features/roles/types/role";

/**
 * The Roles table's column set, per `05_PAGE_CATALOG.md` Sec 13 / this
 * session's mockup: Role, Users, Permissions. Fully client-side sortable
 * (the backend never paginates or sorts this list server-side - the whole
 * dataset is a handful of rows) - no `enableSorting: false`/explicit `id`
 * remapping needed, unlike the server-sorted Users/Companies tables.
 */
export function getRoleColumns(): DataTableColumn<RoleListItem>[] {
  return [
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Role" />,
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <span className="font-medium">{row.original.name}</span>
          {row.original.isSystem && (
            <Badge variant="outline" className="text-xs">
              System
            </Badge>
          )}
        </div>
      ),
    },
    {
      accessorKey: "userCount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Users" />,
    },
    {
      accessorKey: "permissionCount",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Permissions" />,
    },
  ];
}
