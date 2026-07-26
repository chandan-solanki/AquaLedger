import { Checkbox } from "@/components/ui/checkbox";

import { DataTableRowActions } from "./DataTableRowActions";
import type { DataTableAction, DataTableColumn } from "./types";

/**
 * The standard checkbox column: a select-all-on-page header (indeterminate
 * when only some of the current page's rows are selected) plus a per-row
 * checkbox, per `06_COMPONENT_LIBRARY.md` §6 Row Selection /
 * `02_DESIGN_SYSTEM.md` §9. A factory rather than something `DataTable`
 * renders unconditionally, per the component library's explicit "avoid when
 * no bulk action exists" guidance (§6) — a table only gets this column when
 * the consuming feature actually adds it to its `columns` array.
 *
 * "Select all" only ever selects the current page's rows: under this
 * table's server-side-pagination model, `data` already *is* just that page,
 * so `table.toggleAllPageRowsSelected()` and "select every row" are the same
 * operation — there is no separate, larger row model to over-select from.
 */
export function createSelectionColumn<TData>(): DataTableColumn<TData, unknown> {
  return {
    id: "select",
    header: ({ table }) => (
      <Checkbox
        checked={
          table.getIsAllPageRowsSelected()
            ? true
            : table.getIsSomePageRowsSelected()
              ? "indeterminate"
              : false
        }
        onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
        onClick={(event) => event.stopPropagation()}
        aria-label="Select all rows on this page"
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(value) => row.toggleSelected(!!value)}
        onClick={(event) => event.stopPropagation()}
        disabled={!row.getCanSelect()}
        aria-label="Select row"
      />
    ),
    enableSorting: false,
    enableHiding: false,
    enableResizing: false,
    size: 40,
    meta: { hideFromToggle: true },
  };
}

/**
 * The standard row-actions (kebab) column, per `06_COMPONENT_LIBRARY.md` §6
 * Row Actions. `actions` is a function of the row so a feature can vary the
 * menu per record (e.g. no "Reopen" action on an already-open Invoice) and
 * apply RBAC filtering (`07_FRONTEND_ARCHITECTURE.md` §11) at the point
 * where it already has the current user's permission set in scope.
 */
export function createRowActionsColumn<TData>(
  actions: (row: TData) => DataTableAction<TData>[],
  options?: { triggerLabel?: string }
): DataTableColumn<TData, unknown> {
  return {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <DataTableRowActions
        row={row.original}
        actions={actions(row.original)}
        triggerLabel={options?.triggerLabel}
      />
    ),
    enableSorting: false,
    enableHiding: false,
    enableResizing: false,
    size: 48,
    meta: { align: "right", hideFromToggle: true },
  };
}
