import { useCallback, useRef, useState } from "react";

import { toastError, toastSuccess } from "@/lib/toast";
import type { ApiError } from "@/types/api";
import { normalizeApiError } from "@/utils/api-error";

interface UseAsyncActionOptions<R> {
  onSuccess?: (result: R) => void;
  onError?: (error: ApiError) => void;
  successMessage?: string;
  /** Defaults to true — most callers want a failure surfaced immediately without a per-call try/catch. */
  toastOnError?: boolean;
}

/**
 * Wraps an async function (a business-API call, once Sprint 3+ wires those
 * in) with a standard loading/error lifecycle, so pages don't each
 * reimplement their own `isSaving` state + try/catch + toast. Financial
 * writes never auto-retry (`lib/query-client.ts`'s mutation default) —
 * `execute` is always an explicit, user-triggered call.
 */
export function useAsyncAction<Args extends unknown[], R>(
  action: (...args: Args) => Promise<R>,
  options?: UseAsyncActionOptions<R>
) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const execute = useCallback(
    async (...args: Args): Promise<R | undefined> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await action(...args);
        if (optionsRef.current?.successMessage) {
          toastSuccess(optionsRef.current.successMessage);
        }
        optionsRef.current?.onSuccess?.(result);
        return result;
      } catch (caught) {
        const normalized = normalizeApiError(caught);
        setError(normalized);
        if (optionsRef.current?.toastOnError ?? true) {
          toastError(normalized.message);
        }
        optionsRef.current?.onError?.(normalized);
        return undefined;
      } finally {
        setIsLoading(false);
      }
    },
    [action]
  );

  return { execute, isLoading, error };
}
