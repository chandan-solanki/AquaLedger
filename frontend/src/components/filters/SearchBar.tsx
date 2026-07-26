"use client";

import { useEffect, useRef } from "react";
import { Loader2, Search, X } from "lucide-react";

import { IconActionButton } from "@/components/layout/action-buttons";
import { Input } from "@/components/ui/input";
import { useSearch } from "@/hooks/use-search";
import { cn } from "@/lib/utils";

export interface SearchBarProps {
  /** Controlled raw value — omit to let the component manage its own text state (still reporting out via `onSearch`). */
  value?: string;
  defaultValue?: string;
  /** Fires on every keystroke, before debouncing. */
  onChange?: (value: string) => void;
  /** Fires `debounceMs` after the last keystroke — the one to actually filter/search with. */
  onSearch?: (value: string) => void;
  /** @defaultValue 300 */
  debounceMs?: number;
  placeholder?: string;
  isLoading?: boolean;
  disabled?: boolean;
  autoFocus?: boolean;
  "aria-label"?: string;
  className?: string;
}

/**
 * The Toolbar's free-text search field, per `06_COMPONENT_LIBRARY.md` §6 —
 * debounced, a clear button once there's text to clear, and a loading
 * indicator while the (externally-owned) search request is in flight.
 * Composes `useSearch` for the debounce timer rather than reimplementing
 * it. Fully keyboard-accessible: `Escape` clears and refocuses, same as any
 * native search input's expected behavior.
 */
export function SearchBar({
  value: controlledValue,
  defaultValue = "",
  onChange,
  onSearch,
  debounceMs = 300,
  placeholder = "Search…",
  isLoading = false,
  disabled = false,
  autoFocus = false,
  "aria-label": ariaLabel = "Search",
  className,
}: SearchBarProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const search = useSearch({ initialValue: controlledValue ?? defaultValue, debounceMs });
  const isControlled = controlledValue !== undefined;
  const displayValue = isControlled ? controlledValue : search.value;

  useEffect(() => {
    if (isControlled && controlledValue !== search.value) {
      search.setValue(controlledValue);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [controlledValue]);

  useEffect(() => {
    onSearch?.(search.debouncedValue);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search.debouncedValue]);

  function handleChange(next: string) {
    search.setValue(next);
    onChange?.(next);
  }

  function handleClear() {
    search.clear();
    onChange?.("");
    onSearch?.("");
    inputRef.current?.focus();
  }

  return (
    <div className={cn("relative", className)}>
      <Search
        className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
        aria-hidden
      />
      <Input
        ref={inputRef}
        type="search"
        value={displayValue}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus={autoFocus}
        aria-label={ariaLabel}
        onChange={(event) => handleChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Escape" && displayValue) {
            event.preventDefault();
            handleClear();
          }
        }}
        className="pr-8 pl-8"
      />
      <div className="absolute top-1/2 right-1 flex -translate-y-1/2 items-center">
        {isLoading ? (
          <Loader2 className="size-4 animate-spin text-muted-foreground motion-reduce:animate-none" aria-hidden />
        ) : (
          displayValue && (
            <IconActionButton icon={X} label="Clear search" size="icon-sm" onClick={handleClear} />
          )
        )}
      </div>
    </div>
  );
}
