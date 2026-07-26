"use client";

import { useCallback, useMemo, useState } from "react";
import type { RowSelectionState } from "@tanstack/react-table";

/**
 * Standalone row-selection state for tables that don't otherwise need URL-
 * synced state — hands back the selection map, a derived count (what
 * `DataTableToolbar`'s Bulk Actions bar and `DataTablePagination` both want
 * to display), and a `clearSelection` helper for after a bulk action
 * completes.
 */
export function useRowSelection(initialState: RowSelectionState = {}) {
  const [rowSelection, setRowSelection] =
    useState<RowSelectionState>(initialState);

  const selectedCount = useMemo(
    () => Object.values(rowSelection).filter(Boolean).length,
    [rowSelection]
  );

  const clearSelection = useCallback(() => setRowSelection({}), []);

  return { rowSelection, setRowSelection, selectedCount, clearSelection } as const;
}
