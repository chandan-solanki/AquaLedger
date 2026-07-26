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
        setColumnVisibility((current) => ({
          ...current,
          ...(JSON.parse(raw) as VisibilityState),
        }));
      }
    } catch {
      // localStorage unavailable (private browsing, disabled) — visibility still works for this session.
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
