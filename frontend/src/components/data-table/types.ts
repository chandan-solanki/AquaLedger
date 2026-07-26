import type {
  ColumnDef,
  ColumnPinningState,
  ColumnSizingState,
  OnChangeFn,
  RowSelectionState,
  SortingState,
  VisibilityState,
} from "@tanstack/react-table";
import type { LucideIcon } from "lucide-react";

declare module "@tanstack/react-table" {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface ColumnMeta<TData, TValue> {
    /** Text alignment for the column's header and cells — right-align money/quantity/rate columns per `02_DESIGN_SYSTEM.md` §4. */
    align?: "left" | "center" | "right";
    /** Label shown in `DataTableColumnToggle` when it should differ from the rendered header (e.g. the header is an icon, not text). */
    label?: string;
    /** Excludes an otherwise-hideable column from the Column Visibility toggle list. */
    hideFromToggle?: boolean;
  }
}

/** A single column definition — a thin, documented alias over TanStack's `ColumnDef` so feature code never imports `@tanstack/react-table` directly for this type. */
export type DataTableColumn<TData, TValue = unknown> = ColumnDef<TData, TValue>;

/** One entry in a row's kebab/Dropdown Button menu, per `06_COMPONENT_LIBRARY.md` §6 Row Actions. RBAC filtering (e.g. hiding "Edit" for a read-only role) is the consuming feature's responsibility — pass an already-filtered `actions` array. */
export interface DataTableAction<TData> {
  label: string;
  icon?: LucideIcon;
  onClick: (row: TData) => void;
  /** "destructive" styles the item in the Danger color, per `06_COMPONENT_LIBRARY.md` §3 — reserve for Delete/Deactivate-style actions. */
  variant?: "default" | "destructive";
  disabled?: (row: TData) => boolean;
  hidden?: (row: TData) => boolean;
  /** Renders a separator immediately above this item — used to set a destructive action apart from the rest. */
  separatorBefore?: boolean;
}

/** The current page/page-size the table is showing — owned by the consuming feature (typically synced to URL state per `07_FRONTEND_ARCHITECTURE.md` §7), never derived internally. */
export interface DataTablePaginationState {
  pageIndex: number;
  pageSize: number;
}

/** `DataTablePaginationState` plus the server-reported total — everything `DataTablePagination` needs to render, and nothing it needs to fetch. */
export interface DataTablePaginationInfo extends DataTablePaginationState {
  totalCount: number;
}

export type DataTableSortingState = SortingState;
export type DataTableSelectionState = RowSelectionState;
export type DataTableVisibilityState = VisibilityState;
export type DataTableColumnPinningState = ColumnPinningState;
export type DataTableColumnSizingState = ColumnSizingState;
export type { OnChangeFn };

/** The shape every `error` prop across the Data Table system takes — mirrors the category-classified error the Axios interceptor produces (`07_FRONTEND_ARCHITECTURE.md` §8), never a raw exception. */
export interface DataTableErrorInfo {
  title: string;
  description?: string;
  onRetry?: () => void;
}
