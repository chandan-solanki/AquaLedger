"use client";

import { flexRender } from "@tanstack/react-table";
import type { Column, Table } from "@tanstack/react-table";
import type { CSSProperties, KeyboardEvent, ReactNode } from "react";

import { cn } from "@/lib/utils";

import { DataTableEmpty } from "./DataTableEmpty";
import { DataTableError } from "./DataTableError";
import { DataTableLoading } from "./DataTableLoading";
import { DataTableNoResults } from "./DataTableNoResults";
import type { DataTableErrorInfo } from "./types";

export interface DataTableProps<TData> {
  /**
   * The TanStack Table instance — built by the consuming feature via
   * `useDataTable` (or `useReactTable` directly for full control) and shared
   * with any toolbar pieces that also need it (`DataTableColumnToggle`,
   * per-column `DataTableColumnHeader`s already receive their `column`
   * directly). `DataTable` never constructs its own table, so there's only
   * ever one instance for a given table on screen.
   */
  table: Table<TData>;

  /** Called when a row is clicked/activated (Enter/Space while focused) — typically navigation to the record's Detail page. */
  onRowClick?: (row: TData) => void;
  isRowDisabled?: (row: TData) => boolean;

  /** Keeps the header row visible while the table body scrolls, per `02_DESIGN_SYSTEM.md` §9. */
  stickyHeader?: boolean;
  /** Pins the first rendered column, per `02_DESIGN_SYSTEM.md` §15's "identifying first column stays visible during horizontal scroll" rule. For pinning more than one column, or pinning to the right beyond the last column, configure the table's real `columnPinning` state instead. */
  stickyFirstColumn?: boolean;
  /** Pins the last rendered column — the conventional home for a `createRowActionsColumn` actions column. */
  stickyActionColumn?: boolean;
  /** Caps the scroll container's height, enabling vertical scroll with the sticky header staying put. Omit for a table that simply grows with its content. */
  maxHeight?: string;

  isLoading?: boolean;
  loadingRowCount?: number;
  error?: DataTableErrorInfo | null;
  isEmpty?: boolean;
  emptyState?: ReactNode;
  /** True when the query succeeded but the *current filter* matched nothing — swaps in `DataTableNoResults` instead of `DataTableEmpty`, per `04_USER_FLOWS.md` §21. */
  isNoResults?: boolean;
  noResultsState?: ReactNode;

  /** Typically a `DataTableToolbar`, rendered above the table. */
  toolbar?: ReactNode;
  /** Typically a `DataTablePagination`, rendered below the table. */
  pagination?: ReactNode;

  caption?: string;
  "aria-label"?: string;
  className?: string;
}

function getPinningStyle<TData, TValue>(
  column: Column<TData, TValue>,
  isFirst: boolean,
  isLast: boolean,
  stickyFirstColumn: boolean,
  stickyActionColumn: boolean
): { style: CSSProperties; isPinned: boolean } {
  const pinned = column.getIsPinned();
  const pinnedLeft = pinned === "left" || (!pinned && stickyFirstColumn && isFirst);
  const pinnedRight = pinned === "right" || (!pinned && stickyActionColumn && isLast);

  const style: CSSProperties = {};
  if (pinnedLeft) {
    style.position = "sticky";
    style.left = pinned === "left" ? column.getStart("left") : 0;
  }
  if (pinnedRight) {
    style.position = "sticky";
    style.right = pinned === "right" ? column.getAfter("right") : 0;
  }

  return { style, isPinned: pinnedLeft || pinnedRight };
}

/**
 * The Enterprise Data Table — the single, standardized table implementation
 * underlying every List page and Related Records sub-table in AquaLedger,
 * per `06_COMPONENT_LIBRARY.md` §6 and `07_FRONTEND_ARCHITECTURE.md` §13.
 * Purely a renderer over a `Table<TData>` instance the caller supplies: no
 * business logic, no API calls — sorting/pagination are server-side by
 * default and reported upward through the table's own `on*Change` handlers,
 * never computed here.
 *
 * Column widths are always explicit (`column.getSize()`), because sticky
 * columns and resizing both depend on the table's declared sizes matching
 * its actual rendered widths — see the README for the full rationale.
 */
export function DataTable<TData>({
  table,
  onRowClick,
  isRowDisabled,
  stickyHeader = true,
  stickyFirstColumn = false,
  stickyActionColumn = false,
  maxHeight,
  isLoading = false,
  loadingRowCount = 8,
  error = null,
  isEmpty = false,
  emptyState,
  isNoResults = false,
  noResultsState,
  toolbar,
  pagination,
  caption,
  "aria-label": ariaLabel,
  className,
}: DataTableProps<TData>) {
  const rows = table.getRowModel().rows;
  const columnCount = table.getVisibleLeafColumns().length;
  // Pagination stays visible across a loading refetch (avoids it flickering away on every sort/filter
  // change) but hides once a fetch has actually settled into an error or a genuinely empty result.
  const hidePagination = Boolean(error) || (!isLoading && (isEmpty || rows.length === 0));

  function handleRowKeyDown(event: KeyboardEvent<HTMLTableRowElement>, original: TData) {
    if (!onRowClick) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onRowClick(original);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {toolbar}

      <div
        className={cn("w-full overflow-auto rounded-lg border", className)}
        style={maxHeight ? { maxHeight } : undefined}
      >
        <table
          role="table"
          aria-label={ariaLabel}
          className="w-full border-collapse text-sm"
          style={{ width: table.getTotalSize() }}
        >
          {caption && <caption className="sr-only">{caption}</caption>}

          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="border-b">
                {headerGroup.headers.map((header, index) => {
                  const isFirst = index === 0;
                  const isLast = index === headerGroup.headers.length - 1;
                  const align = header.column.columnDef.meta?.align;
                  const sorted = header.column.getIsSorted();
                  const { style: pinStyle, isPinned } = getPinningStyle(
                    header.column,
                    isFirst,
                    isLast,
                    stickyFirstColumn,
                    stickyActionColumn
                  );

                  const style: CSSProperties = {
                    width: header.getSize(),
                    ...pinStyle,
                    ...(stickyHeader && { position: "sticky", top: 0 }),
                  };

                  return (
                    <th
                      key={header.id}
                      scope="col"
                      aria-sort={
                        !header.column.getCanSort()
                          ? undefined
                          : sorted === "asc"
                            ? "ascending"
                            : sorted === "desc"
                              ? "descending"
                              : "none"
                      }
                      style={style}
                      className={cn(
                        "relative h-10 whitespace-nowrap bg-background px-4 text-left align-middle font-medium text-muted-foreground",
                        align === "right" && "text-right",
                        align === "center" && "text-center",
                        (stickyHeader || isPinned) && "z-20"
                      )}
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(header.column.columnDef.header, header.getContext())}

                      {header.column.getCanResize() && (
                        <div
                          onMouseDown={header.getResizeHandler()}
                          onTouchStart={header.getResizeHandler()}
                          className={cn(
                            "absolute top-0 right-0 h-full w-1.5 cursor-col-resize touch-none select-none bg-transparent hover:bg-border",
                            header.column.getIsResizing() && "bg-primary"
                          )}
                          aria-hidden
                        />
                      )}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>

          <tbody>
            {error ? (
              <tr>
                <td colSpan={columnCount} className="p-0">
                  <DataTableError
                    title={error.title}
                    description={error.description}
                    onRetry={error.onRetry}
                  />
                </td>
              </tr>
            ) : isLoading ? (
              <tr>
                <td colSpan={columnCount} className="p-0">
                  <DataTableLoading columnCount={columnCount} rowCount={loadingRowCount} />
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={columnCount} className="p-0">
                  {isNoResults
                    ? (noResultsState ?? <DataTableNoResults />)
                    : (emptyState ?? <DataTableEmpty />)}
                </td>
              </tr>
            ) : (
              rows.map((row) => {
                const disabled = isRowDisabled?.(row.original) ?? false;
                const clickable = Boolean(onRowClick) && !disabled;

                return (
                  <tr
                    key={row.id}
                    data-state={row.getIsSelected() ? "selected" : undefined}
                    aria-selected={row.getIsSelected()}
                    aria-disabled={disabled || undefined}
                    tabIndex={clickable ? 0 : undefined}
                    onClick={clickable ? () => onRowClick?.(row.original) : undefined}
                    onKeyDown={clickable ? (event) => handleRowKeyDown(event, row.original) : undefined}
                    className={cn(
                      "border-b transition-colors last:border-b-0 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-inset",
                      clickable && "cursor-pointer hover:bg-muted/50",
                      row.getIsSelected() && "bg-muted/50",
                      disabled && "pointer-events-none opacity-50"
                    )}
                  >
                    {row.getVisibleCells().map((cell, index) => {
                      const isFirst = index === 0;
                      const isLast = index === row.getVisibleCells().length - 1;
                      const align = cell.column.columnDef.meta?.align;
                      const { style: pinStyle, isPinned } = getPinningStyle(
                        cell.column,
                        isFirst,
                        isLast,
                        stickyFirstColumn,
                        stickyActionColumn
                      );

                      return (
                        <td
                          key={cell.id}
                          style={{ width: cell.column.getSize(), ...pinStyle }}
                          className={cn(
                            "whitespace-nowrap px-4 py-2.5 align-middle",
                            align === "right" && "text-right tabular-nums",
                            align === "center" && "text-center",
                            isPinned && "z-10 bg-background",
                            row.getIsSelected() && isPinned && "bg-muted/50"
                          )}
                        >
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      );
                    })}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {!hidePagination && pagination}
    </div>
  );
}
