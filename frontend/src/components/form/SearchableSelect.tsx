"use client";

import { Combobox, type ComboboxOption, type ComboboxProps } from "./Combobox";

export type { ComboboxOption };

export type SearchableSelectProps<TValue extends string = string> = Omit<
  ComboboxProps<TValue>,
  "onSearchChange" | "isLoading" | "shouldFilter"
>;

/**
 * The Combobox configured for a small, fully-in-memory option list — Single
 * Select's searchable sibling for lists too long to scan unaided (`06_COMPONENT_LIBRARY.md`
 * §4: "avoid Single Select when the list is long — use Combobox instead").
 * Filtering happens entirely client-side via cmdk's own match against each
 * option's label; there is no search callback or loading state because
 * every option is already available.
 */
export function SearchableSelect<TValue extends string = string>(
  props: SearchableSelectProps<TValue>
) {
  return <Combobox {...props} shouldFilter />;
}
