import { useCallback, useMemo, useState } from "react";

export type FilterValues = object;

export interface UseFiltersResult<TFilters extends FilterValues> {
  filters: TFilters;
  setFilter: <K extends keyof TFilters>(key: K, value: TFilters[K]) => void;
  removeFilter: (key: keyof TFilters) => void;
  setFilters: (filters: TFilters) => void;
  /** Resets every filter back to its value in the hook's initial `initialFilters` — never an unrelated hardcoded "empty" shape. */
  clearFilters: () => void;
  /** Count of filters currently different from their initial value — what a `ClearFiltersButton`/`FilterBadge` would display. */
  activeCount: number;
  isActive: (key: keyof TFilters) => boolean;
}

function isEmptyValue(value: unknown): boolean {
  if (value === undefined || value === null || value === "") return true;
  if (Array.isArray(value)) return value.length === 0;
  return false;
}

/**
 * Local state for a set of named filter values — no URL sync, no API call,
 * no opinion on what the filters mean. The owning feature reacts to
 * `filters` changing to refetch its own list; this hook only tracks
 * "what's currently selected" and "how many filters differ from their
 * defaults," per this session's explicit "no business state" scope.
 */
export function useFilters<TFilters extends FilterValues>(
  initialFilters: TFilters
): UseFiltersResult<TFilters> {
  const [filters, setFiltersState] = useState<TFilters>(initialFilters);

  const setFilter = useCallback(<K extends keyof TFilters>(key: K, value: TFilters[K]) => {
    setFiltersState((current) => ({ ...current, [key]: value }));
  }, []);

  const removeFilter = useCallback(
    (key: keyof TFilters) => {
      setFiltersState((current) => ({ ...current, [key]: initialFilters[key] }));
    },
    [initialFilters]
  );

  const clearFilters = useCallback(() => {
    setFiltersState(initialFilters);
  }, [initialFilters]);

  const isActive = useCallback(
    (key: keyof TFilters) => !isEmptyValue(filters[key]) && filters[key] !== initialFilters[key],
    [filters, initialFilters]
  );

  const activeCount = useMemo(
    () => (Object.keys(filters) as (keyof TFilters)[]).filter((key) => isActive(key)).length,
    [filters, isActive]
  );

  return {
    filters,
    setFilter,
    removeFilter,
    setFilters: setFiltersState,
    clearFilters,
    activeCount,
    isActive,
  };
}
