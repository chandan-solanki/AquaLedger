import { useCallback } from "react";

import { toastError } from "@/lib/toast";
import type { ApiError } from "@/types/api";
import { normalizeApiError } from "@/utils/api-error";

interface HandleErrorOptions {
  /** Defaults to true — most callers want the failure surfaced immediately. */
  toast?: boolean;
  /** Overrides the normalized error's own message in the toast, when a call site needs more specific copy. */
  message?: string;
}

/**
 * A stable `handleError` callback for call sites that want manual control
 * over a catch block (as opposed to `useAsyncAction`'s fully-wrapped
 * execute/isLoading/error API) — normalizes the error, optionally toasts
 * it, and returns the normalized `ApiError` for further use (e.g. mapping
 * `fieldErrors` onto a form via `mapServerErrorsToForm`).
 */
export function useErrorHandler() {
  return useCallback((error: unknown, options?: HandleErrorOptions): ApiError => {
    const normalized = normalizeApiError(error);
    if (options?.toast ?? true) {
      toastError(options?.message ?? normalized.message);
    }
    return normalized;
  }, []);
}
