"use client";

import {
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import type {
  ColumnPinningState,
  ColumnSizingState,
  OnChangeFn,
  Row,
  RowSelectionState,
  SortingState,
  Table,
  VisibilityState,
} from "@tanstack/react-table";

import type { DataTableColumn } from "../types";

export interface UseDataTableOptions<TData, TValue> {
  data: TData[];
  columns: DataTableColumn<TData, TValue>[];
  getRowId?: (row: TData, index: number) => string;

  /** Controlled sort state. Omit both this and `onSortingChange` to let the table manage sorting internally. */
  sorting?: SortingState;
  onSortingChange?: OnChangeFn<SortingState>;
  /** Server-side sorting by default, per `07_FRONTEND_ARCHITECTURE.md` §13 — the table reports the desired sort, it never re-orders `data` itself. Set `false` for a genuinely client-side table. */
  manualSorting?: boolean;
  enableMultiSort?: boolean;

  columnVisibility?: VisibilityState;
  onColumnVisibilityChange?: OnChangeFn<VisibilityState>;

  rowSelection?: RowSelectionState;
  onRowSelectionChange?: OnChangeFn<RowSelectionState>;
  enableRowSelection?: boolean | ((row: TData) => boolean);
  enableMultiRowSelection?: boolean;

  columnPinning?: ColumnPinningState;
  onColumnPinningChange?: OnChangeFn<ColumnPinningState>;

  columnSizing?: ColumnSizingState;
  onColumnSizingChange?: OnChangeFn<ColumnSizingState>;
  enableColumnResizing?: boolean;

  /** Server-side pagination by default — `data` is assumed to already be just the current page. */
  manualPagination?: boolean;
  pageCount?: number;
}

/**
 * The Enterprise Data Table's TanStack Table wiring, isolated behind one
 * hook so `DataTable.tsx` stays a rendering component, not a state-management
 * one. Every controlled slice (sorting/visibility/selection/pinning/sizing)
 * is genuinely optional: pass the state + its `onChange` to control it from
 * outside (e.g. syncing sort to the URL per `07_FRONTEND_ARCHITECTURE.md`
 * §7), or omit both to let TanStack manage that slice internally.
 *
 * Omitted controlled props are left out of the options object entirely
 * (never passed as explicit `undefined`) — TanStack merges options with
 * `{...defaults, ...options}`, so an explicit `undefined` would overwrite
 * its internal default state manager and silently break that slice.
 */
export function useDataTable<TData, TValue>({
  data,
  columns,
  getRowId,
  sorting,
  onSortingChange,
  manualSorting = true,
  enableMultiSort = true,
  columnVisibility,
  onColumnVisibilityChange,
  rowSelection,
  onRowSelectionChange,
  enableRowSelection = false,
  enableMultiRowSelection = true,
  columnPinning,
  onColumnPinningChange,
  columnSizing,
  onColumnSizingChange,
  enableColumnResizing = false,
  manualPagination = true,
  pageCount,
}: UseDataTableOptions<TData, TValue>): Table<TData> {
  return useReactTable<TData>({
    data,
    columns,
    getRowId,
    manualSorting,
    enableMultiSort,
    manualFiltering: true,
    manualPagination,
    pageCount,
    enableRowSelection:
      typeof enableRowSelection === "function"
        ? (row: Row<TData>) => (enableRowSelection as (row: TData) => boolean)(row.original)
        : enableRowSelection,
    enableMultiRowSelection,
    enableColumnResizing,
    columnResizeMode: "onChange",
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    state: {
      ...(sorting !== undefined && { sorting }),
      ...(columnVisibility !== undefined && { columnVisibility }),
      ...(rowSelection !== undefined && { rowSelection }),
      ...(columnPinning !== undefined && { columnPinning }),
      ...(columnSizing !== undefined && { columnSizing }),
    },
    ...(onSortingChange && { onSortingChange }),
    ...(onColumnVisibilityChange && { onColumnVisibilityChange }),
    ...(onRowSelectionChange && { onRowSelectionChange }),
    ...(onColumnPinningChange && { onColumnPinningChange }),
    ...(onColumnSizingChange && { onColumnSizingChange }),
  });
}
