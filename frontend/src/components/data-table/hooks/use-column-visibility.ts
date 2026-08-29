"use client";

import { useEffect, useState } from "react";
import type { VisibilityState } from "@tanstack/react-table";

/**
 * Column visibility, persisted to `localStorage` under a caller-supplied key
 * so each table (Companies, Invoices, ...) keeps its own remembered layout,
 * per `06_COMPONENT_LIBRARY.md` §6 Column Selector / this session's "View
 * Options" spec.
 *
 * Initial render always returns `initialState` unchanged (matching what the
 * server would have rendered) — the persisted value, if any, is applied in
 * an effect after mount. This trades a one-frame flash for avoiding a
 * hydration mismatch, the same tradeoff `next-themes`-style providers make
 * for theme persistence (`07_FRONTEND_ARCHITECTURE.md` §17).
 */
export function useColumnVisibility(
  storageKey: string,
  initialState: VisibilityState = {}
) {
  const [columnVisibility, setColumnVisibility] =
    useState<VisibilityState>(initialState);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (raw) {
        // `JSON.parse` must run here, synchronously inside the `try`, not
        // inside the `setColumnVisibility` updater below — React defers
        // running a functional updater to the render phase, by which point
        // this `try/catch`'s stack frame is long gone, so a parse error
        // thrown from inside the updater would crash the render instead of
        // being caught here (confirmed live: corrupt JSON in localStorage
        // took down the whole page despite this catch block existing).
        const parsed = JSON.parse(raw) as VisibilityState;
        setColumnVisibility((current) => ({ ...current, ...parsed }));
      }
    } catch {
      // localStorage unavailable (private browsing, disabled) or its stored
      // value is corrupt — ignore and keep `initialState` for this session.
    }
    // Only re-read when the key itself changes; `initialState` is a fresh object per render by nature of most callers.
  }, [storageKey]);

  useEffect(() => {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(columnVisibility));
    } catch {
      // Ignore write failures for the same reason as above.
    }
  }, [storageKey, columnVisibility]);

  return [columnVisibility, setColumnVisibility] as const;
}
