"use client";

import { Settings2 } from "lucide-react";
import type { Table } from "@tanstack/react-table";

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
          const label =
            column.columnDef.meta?.label ??
            (typeof column.columnDef.header === "string" ? column.columnDef.header : column.id);

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
