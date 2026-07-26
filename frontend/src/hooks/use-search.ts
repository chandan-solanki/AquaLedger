import { useEffect, useState } from "react";

export interface UseSearchOptions {
  /** @defaultValue "" */
  initialValue?: string;
  /** Delay before `debouncedValue` catches up to `value`. @defaultValue 300 */
  debounceMs?: number;
}

export interface UseSearchResult {
  /** The raw, immediate value — update this on every keystroke. */
  value: string;
  /** `value`, settled after `debounceMs` of no further changes — the one to actually search/filter with. */
  debouncedValue: string;
  setValue: (value: string) => void;
  /** True between a keystroke and `debouncedValue` catching up — drive a loading indicator with this. */
  isDebouncing: boolean;
  clear: () => void;
}

/**
 * Debounced search-text state, with no opinion on where the text goes next
 * (a table filter, a list filter, nothing at all) and no API call of its
 * own — `SearchBar` (`components/filters/`) composes this rather than
 * reimplementing its own debounce timer, and any other component needing
 * the same debounce-a-string behavior can use it directly.
 */
export function useSearch({
  initialValue = "",
  debounceMs = 300,
}: UseSearchOptions = {}): UseSearchResult {
  const [value, setValue] = useState(initialValue);
  const [debouncedValue, setDebouncedValue] = useState(initialValue);

  useEffect(() => {
    if (value === debouncedValue) return;

    const timeout = setTimeout(() => setDebouncedValue(value), debounceMs);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, debounceMs]);

  function clear() {
    setValue("");
    setDebouncedValue("");
  }

  return {
    value,
    debouncedValue,
    setValue,
    isDebouncing: value !== debouncedValue,
    clear,
  };
}
