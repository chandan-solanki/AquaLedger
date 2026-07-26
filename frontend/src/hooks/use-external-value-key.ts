import { useEffect, useRef, useState } from "react";

/**
 * A `key` that only changes when `value` changes for a reason *other* than
 * the owning component reporting its own write via `report()`.
 *
 * Built for the "debounce a text filter, then sync it to the URL" pattern:
 * remounting an uncontrolled input (via `key={...}`) is the standard way to
 * resync it to an externally-changed value (Back/Forward, a cleared filter
 * chip, Clear All) without fighting React over controlled-vs-uncontrolled
 * state. But remounting on *every* debounced write — the naive
 * `key={value}` version — unmounts the input as the user types, which
 * drops keyboard focus mid-sentence. This hook fixes that: the input's own
 * debounced-change handler calls `report(value)` right before writing the
 * value out (e.g. to the URL), so the resulting `value` change is
 * recognized as self-inflicted and does not remount. A value that changes
 * *without* a matching `report()` call first — Back/Forward, a chip's
 * "remove" button, Clear All — is a genuine external change and does.
 */
export function useExternalValueKey(value: string) {
  const lastReported = useRef(value);
  const [key, setKey] = useState(0);

  useEffect(() => {
    if (value !== lastReported.current) {
      lastReported.current = value;
      setKey((current) => current + 1);
    }
  }, [value]);

  function report(next: string) {
    lastReported.current = next;
  }

  return [key, report] as const;
}
