"use client";

import { DataTableColumnHeader } from "@/components/data-table";
import type { DataTableColumn } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  AUDIT_LOG_ACTION_BADGE_VARIANT,
  humanizeAuditAction,
  humanizeAuditEntityType,
} from "@/features/audit-logs/constants/audit-log-action";
import type { AuditLogEntry } from "@/features/audit-logs/types/audit-log";
import { formatDateTime } from "@/utils/format-date";

/** A single `changes` entry can be either a plain snapshot value (creation
 * events) or an `{old, new}` diff (update/status/role-change events) - see
 * app/modules/users/service.py's audit calls. Rendered as `key: value` or
 * `key: old → new` accordingly. */
function summarizeChanges(changes: Record<string, unknown> | null): string {
  if (!changes || Object.keys(changes).length === 0) return "—";
  return Object.entries(changes)
    .map(([key, value]) => {
      if (value && typeof value === "object" && "old" in value && "new" in value) {
        const diff = value as { old: unknown; new: unknown };
        return `${key}: ${String(diff.old)} → ${String(diff.new)}`;
      }
      return `${key}: ${String(value)}`;
    })
    .join(", ");
}

function ChangesCell({ changes }: { changes: Record<string, unknown> | null }) {
  const summary = summarizeChanges(changes);
  if (!changes || Object.keys(changes).length === 0) {
    return <span className="text-muted-foreground">—</span>;
  }
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          onClick={(event) => event.stopPropagation()}
          className="max-w-72 truncate text-left text-sm text-muted-foreground underline-offset-4 outline-none hover:text-foreground hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50"
        >
          {summary}
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-96">
        <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-all text-xs">
          {JSON.stringify(changes, null, 2)}
        </pre>
      </PopoverContent>
    </Popover>
  );
}

/**
 * The Audit Logs table's column set, per this session's mockup: Date, User,
 * Action, Resource, Details. Only `created_at` is sortable, matching the
 * backend's sortable field set (app/modules/audit_logs/schemas.py) exactly -
 * User/Action/Resource are all either a join or a low-cardinality code with
 * no useful ordering, and Details is a JSONB blob.
 */
export function getAuditLogColumns(): DataTableColumn<AuditLogEntry>[] {
  return [
    {
      id: "created_at",
      accessorKey: "createdAt",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Date" />,
      cell: ({ row }) => formatDateTime(row.original.createdAt),
    },
    {
      id: "actor",
      header: "User",
      enableSorting: false,
      cell: ({ row }) => {
        const { actor } = row.original;
        if (!actor) return <span className="text-muted-foreground">System</span>;
        return (
          <div className="flex flex-col">
            <span className="font-medium">{actor.fullName}</span>
            <span className="text-xs text-muted-foreground">{actor.email}</span>
          </div>
        );
      },
    },
    {
      accessorKey: "action",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Action" />,
      enableSorting: false,
      cell: ({ row }) => (
        <Badge variant={AUDIT_LOG_ACTION_BADGE_VARIANT[row.original.action] ?? "outline"}>
          {humanizeAuditAction(row.original.action)}
        </Badge>
      ),
    },
    {
      id: "entity_type",
      accessorKey: "entityType",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Resource" />,
      enableSorting: false,
      cell: ({ row }) => humanizeAuditEntityType(row.original.entityType),
    },
    {
      id: "changes",
      header: "Details",
      enableSorting: false,
      cell: ({ row }) => <ChangesCell changes={row.original.changes} />,
    },
  ];
}
