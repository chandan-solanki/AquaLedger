"use client";

import type { DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { TENANT_STATUS_BADGE_VARIANT, TENANT_STATUS_LABELS } from "@/features/platform/constants/tenant-status";
import type { Tenant } from "@/features/platform/types/tenant";
import { formatDate } from "@/utils/format-date";

/**
 * The Platform Tenants table's column set — no sorting (the backend list
 * endpoint has no `sort` param, always newest-first) and no row-action menu:
 * the only action on this list is opening a tenant's detail page, wired
 * through `DataTable`'s own `onRowClick`, not a per-row Actions column —
 * lifecycle status changes are high-impact enough to deserve the full detail
 * page's context rather than a quick list-row shortcut.
 */
export function getTenantColumns(): DataTableColumn<Tenant>[] {
  return [
    {
      accessorKey: "name",
      header: "Tenant Name",
      cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
      enableHiding: false,
    },
    {
      accessorKey: "slug",
      header: "Slug",
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={TENANT_STATUS_BADGE_VARIANT[row.original.status]}>
          {TENANT_STATUS_LABELS[row.original.status]}
        </Badge>
      ),
    },
    {
      accessorKey: "createdAt",
      header: "Created At",
      cell: ({ row }) => formatDate(row.original.createdAt),
    },
    {
      accessorKey: "updatedAt",
      header: "Updated At",
      cell: ({ row }) => formatDate(row.original.updatedAt),
    },
  ];
}
