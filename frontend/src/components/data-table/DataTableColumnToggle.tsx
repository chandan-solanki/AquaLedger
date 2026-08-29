"use client";

import { isValidElement } from "react";
import { Settings2 } from "lucide-react";
import type { Column, Table } from "@tanstack/react-table";

import { ToolbarButton } from "@/components/layout/action-buttons";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface DataTableColumnToggleProps<TData> {
  table: Table<TData>;
  triggerLabel?: string;
}

/**
 * Every column in this codebase renders its header via
 * `<DataTableColumnHeader column={column} title="…" />` rather than a plain
 * string, so `columnDef.header` is almost always a function, not text — the
 * naive `typeof header === "string"` fallback used to land on `column.id`
 * (`"created_at"`, `"gstin"`) instead of a readable label. `DataTableColumnHeader`
 * always takes its display text as a `title` prop, so calling the header
 * function (a plain element-returning function, safe to invoke outside
 * TanStack's own render pass — it never touches anything beyond the
 * `column` it's given) and reading `.props.title` off the resulting element
 * recovers the real label without requiring every column definition to also
 * set `meta.label` by hand.
 */
function getColumnLabel<TData, TValue>(column: Column<TData, TValue>): string {
  const { meta, header } = column.columnDef;
  if (meta?.label) return meta.label;
  if (typeof header === "string") return header;
  if (typeof header === "function") {
    try {
      const element = header({ column } as Parameters<typeof header>[0]);
      if (isValidElement<{ title?: unknown }>(element) && typeof element.props.title === "string") {
        return element.props.title;
      }
    } catch {
      // Falls through to the column id below — some header functions may
      // depend on context (`table`/`header`) this probe doesn't provide.
    }
  }
  return column.id;
}

/**
 * The Toolbar's "View" trigger — a checklist of every hideable column, per
 * `06_COMPONENT_LIBRARY.md` §6 Column Selector. Visibility state itself is
 * owned by the table (see `useColumnVisibility`, which persists it to
 * `localStorage`); this component only renders the checklist and toggles it
 * through the table instance. Renders nothing if every column is fixed
 * (`enableHiding: false`) — e.g. a table with only a selection column and
 * two data columns.
 */
export function DataTableColumnToggle<TData>({
  table,
  triggerLabel = "View",
}: DataTableColumnToggleProps<TData>) {
  const columns = table
    .getAllColumns()
    .filter((column) => column.getCanHide() && !column.columnDef.meta?.hideFromToggle);

  if (columns.length === 0) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <ToolbarButton>
          <Settings2 />
          {triggerLabel}
        </ToolbarButton>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuLabel>Toggle columns</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {columns.map((column) => {
          const label = getColumnLabel(column);

          return (
            <DropdownMenuCheckboxItem
              key={column.id}
              checked={column.getIsVisible()}
              onCheckedChange={(value) => column.toggleVisibility(!!value)}
              onSelect={(event) => event.preventDefault()}
            >
              {label}
            </DropdownMenuCheckboxItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
