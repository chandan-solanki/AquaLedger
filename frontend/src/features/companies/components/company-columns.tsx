"use client";

import { DataTableColumnHeader, createRowActionsColumn } from "@/components/data-table";
import type { DataTableAction, DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import {
  COMPANY_STATUS_BADGE_VARIANT,
  COMPANY_STATUS_LABELS,
} from "@/features/companies/constants/company-status";
import type { Company } from "@/features/companies/types/company";
import { formatDate } from "@/utils/format-date";

/**
 * The Companies table's column set, per this session's fixed spec: Company
 * Name, Code, GSTIN, Phone, City, Status, Created At, Actions. Only
 * name/code/created_at/updated_at are sortable — matching the backend's
 * `_SORTABLE_FIELDS` (app/modules/companies/schemas.py) exactly, since
 * sorting is server-side.
 */
export function getCompanyColumns(
  rowActions: (company: Company) => DataTableAction<Company>[]
): DataTableColumn<Company>[] {
  return [
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Company Name" />,
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
        <Badge variant={COMPANY_STATUS_BADGE_VARIANT[row.original.status]}>
          {COMPANY_STATUS_LABELS[row.original.status]}
        </Badge>
      ),
    },
    {
      // `id` is explicit (not left to default to `accessorKey`) because
      // sorting state uses this column's `id` as the sort field, and the
      // backend's sortable fields are snake_case (`created_at`) while
      // `Company`'s own field is camelCase (`createdAt`) — without this,
      // clicking the header would send `sort=createdAt` and the backend
      // would 422 it as an unrecognized field.
      id: "created_at",
      accessorKey: "createdAt",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Created At" />,
      cell: ({ row }) => formatDate(row.original.createdAt),
    },
    createRowActionsColumn<Company>(rowActions),
  ];
}
