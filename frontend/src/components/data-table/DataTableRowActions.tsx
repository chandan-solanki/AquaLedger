"use client";

import { Fragment } from "react";
import { MoreHorizontal } from "lucide-react";

import { IconActionButton } from "@/components/layout/action-buttons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import type { DataTableAction } from "./types";

interface DataTableRowActionsProps<TData> {
  row: TData;
  actions: DataTableAction<TData>[];
  triggerLabel?: string;
}

/**
 * The row's kebab menu — View/Edit/Delete-style inline actions in the
 * table's final column, per `06_COMPONENT_LIBRARY.md` §6 Row Actions /
 * `02_DESIGN_SYSTEM.md` §9. Actions (including any RBAC filtering, per
 * `07_FRONTEND_ARCHITECTURE.md` §11) are supplied entirely by the consuming
 * feature — this component only renders whatever it's given, and renders
 * nothing at all if every action is hidden for this row.
 *
 * Clicks are stopped from bubbling to the row itself so opening the menu (or
 * choosing an item) never also triggers `onRowClick`.
 */
export function DataTableRowActions<TData>({
  row,
  actions,
  triggerLabel = "Open row actions",
}: DataTableRowActionsProps<TData>) {
  const visibleActions = actions.filter((action) => !action.hidden?.(row));

  if (visibleActions.length === 0) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <IconActionButton
          icon={MoreHorizontal}
          label={triggerLabel}
          onClick={(event) => event.stopPropagation()}
        />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" onClick={(event) => event.stopPropagation()}>
        {visibleActions.map((action, index) => (
          <Fragment key={action.label}>
            {action.separatorBefore && index > 0 && <DropdownMenuSeparator />}
            <DropdownMenuItem
              variant={action.variant === "destructive" ? "destructive" : "default"}
              disabled={action.disabled?.(row)}
              onClick={() => action.onClick(row)}
            >
              {action.icon && <action.icon aria-hidden />}
              {action.label}
            </DropdownMenuItem>
          </Fragment>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
