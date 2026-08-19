"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { USER_STATUS_BADGE_VARIANT, USER_STATUS_LABELS } from "@/features/users/constants/user-status";
import type { ManagedUser } from "@/features/users/types/user";
import { formatDateTime } from "@/utils/format-date";

/**
 * The Users table's column set, per `05_PAGE_CATALOG.md` §13: Name, Email,
 * Role, Status, Last Active, Actions. Role/Status aren't sortable server-side
 * (role is a join, status has no useful ordering); Name/Email/Last Active
 * match the backend's `_SORTABLE_FIELDS` (app/modules/users/schemas.py).
 */
export function getUserColumns(
  rowActions: (user: ManagedUser) => DataTableAction<ManagedUser>[]
): DataTableColumn<ManagedUser>[] {
  return [
    {
      // Explicit id: the backend's sortable field is `full_name`, while
      // ManagedUser's own field is `fullName` - without this, clicking the
      // header would send `sort=fullName` and the backend would 422 it.
      id: "full_name",
      accessorKey: "fullName",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Name" />,
      cell: ({ row }) => <span className="font-medium">{row.original.fullName}</span>,
    },
    {
      accessorKey: "email",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Email" />,
    },
    {
      id: "role",
      header: "Role",
      enableSorting: false,
      cell: ({ row }) => row.original.role?.name ?? "—",
    },
    {
      accessorKey: "status",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
      enableSorting: false,
      cell: ({ row }) => (
        <Badge variant={USER_STATUS_BADGE_VARIANT[row.original.status]}>
          {USER_STATUS_LABELS[row.original.status]}
        </Badge>
      ),
    },
    {
      id: "last_login_at",
      accessorKey: "lastLoginAt",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Last Active" />,
      cell: ({ row }) => (row.original.lastLoginAt ? formatDateTime(row.original.lastLoginAt) : "Never"),
    },
    createRowActionsColumn<ManagedUser>(rowActions),
  ];
}
