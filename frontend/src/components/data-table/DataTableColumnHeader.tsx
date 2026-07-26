"use client";

import { ArrowDown, ArrowUp, ChevronsUpDown, EyeOff, MoreVertical } from "lucide-react";
import type { Column } from "@tanstack/react-table";
import type { HTMLAttributes } from "react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

interface DataTableColumnHeaderProps<TData, TValue>
  extends HTMLAttributes<HTMLDivElement> {
  column: Column<TData, TValue>;
  title: string;
}

/**
 * The Data Table's sortable column header, per `06_COMPONENT_LIBRARY.md` §6
 * Sort. Clicking the label toggles sort via TanStack's own handler (which
 * honors Shift-click for Multi-column sorting when `enableMultiSort` is on);
 * the chevron opens an explicit Ascending/Descending/Hide menu for users who
 * prefer not to guess at click-cycling behavior. Columns that can neither
 * sort nor hide render as plain static text — the category default, no
 * interactive chrome where there's nothing to interact with.
 */
export function DataTableColumnHeader<TData, TValue>({
  column,
  title,
  className,
  ...props
}: DataTableColumnHeaderProps<TData, TValue>) {
  const canSort = column.getCanSort();
  const canHide = column.getCanHide();

  if (!canSort && !canHide) {
    return (
      <div className={cn("text-sm font-medium", className)} {...props}>
        {title}
      </div>
    );
  }

  const sorted = column.getIsSorted();
  const SortIcon = sorted === "desc" ? ArrowDown : sorted === "asc" ? ArrowUp : ChevronsUpDown;

  return (
    <div className={cn("flex items-center gap-1", className)} {...props}>
      {canSort ? (
        <button
          type="button"
          onClick={column.getToggleSortingHandler()}
          className="-ml-1.5 flex items-center gap-1.5 rounded-md px-1.5 py-1 text-sm font-medium outline-none hover:bg-accent hover:text-accent-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50"
          aria-label={`Sort by ${title}${
            sorted ? `, currently sorted ${sorted === "asc" ? "ascending" : "descending"}` : ""
          }`}
        >
          <span>{title}</span>
          <SortIcon className={cn("size-3.5", !sorted && "text-muted-foreground")} aria-hidden />
        </button>
      ) : (
        <span className="px-1.5 text-sm font-medium">{title}</span>
      )}

      {(canSort || canHide) && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="rounded-md p-1 text-muted-foreground outline-none hover:bg-accent hover:text-accent-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 data-[state=open]:bg-accent data-[state=open]:text-accent-foreground"
              aria-label={`Column options for ${title}`}
            >
              <MoreVertical className="size-3.5" aria-hidden />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            {canSort && (
              <>
                <DropdownMenuItem onClick={() => column.toggleSorting(false)}>
                  <ArrowUp className="text-muted-foreground" aria-hidden />
                  Sort ascending
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => column.toggleSorting(true)}>
                  <ArrowDown className="text-muted-foreground" aria-hidden />
                  Sort descending
                </DropdownMenuItem>
              </>
            )}
            {canSort && canHide && <DropdownMenuSeparator />}
            {canHide && (
              <DropdownMenuItem onClick={() => column.toggleVisibility(false)}>
                <EyeOff className="text-muted-foreground" aria-hidden />
                Hide column
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
}
