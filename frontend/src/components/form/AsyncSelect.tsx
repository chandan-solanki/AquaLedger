"use client";

import { Combobox, type ComboboxOption, type ComboboxProps } from "./Combobox";

export type { ComboboxOption };

export type AsyncSelectProps<TValue extends string = string> = Omit<
  ComboboxProps<TValue>,
  "shouldFilter"
> & {
  /** Fires on every search-box keystroke — wire this to your own debounced fetch/TanStack Query hook and pass the result back in as `options`. This component never calls an API itself. */
  onSearchChange: (query: string) => void;
  isLoading: boolean;
};

/**
 * The Combobox configured for a server-sourced option list — Company/Supplier/
 * Fish selectors backed by a real search endpoint (`06_COMPONENT_LIBRARY.md`
 * §10 Entity Selector), per `06_COMPONENT_LIBRARY.md` §4's "shows a labeled
 * loading state while options resolve" requirement. `options` is generic and
 * supplied entirely by the caller — this component has no knowledge of any
 * entity shape or endpoint, and makes no network calls of its own; a future
 * feature wires `onSearchChange` to a debounced TanStack Query hook and
 * passes its `data`/`isLoading` straight through as `options`/`isLoading`.
 * Client-side filtering is disabled (`shouldFilter={false}`) since the
 * server has already narrowed `options` to match the query.
 */
export function AsyncSelect<TValue extends string = string>({
  emptyMessage = "No matches found.",
  ...props
}: AsyncSelectProps<TValue>) {
  return <Combobox {...props} emptyMessage={emptyMessage} shouldFilter={false} />;
}
