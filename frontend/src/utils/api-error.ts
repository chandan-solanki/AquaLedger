import type { ApiError } from "@/types/api";

const DEFAULT_MESSAGE = "Something went wrong. Please try again.";

function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === "object" &&
    error !== null &&
    "category" in error &&
    "code" in error &&
    "message" in error
  );
}

/**
 * Normalizes anything a `catch` block might see into an `ApiError`.
 * `apiClient`/`bffClient` (via `lib/create-http-client.ts`) already reject
 * with a real `ApiError`, so this is mostly a pass-through for those — its
 * job is the edge cases: a thrown `Error` from client-side code, or a
 * non-Error value thrown by something outside our control.
 */
export function normalizeApiError(error: unknown): ApiError {
  if (isApiError(error)) return error;

  if (error instanceof Error) {
    return { category: "unknown", status: null, code: "UNKNOWN_ERROR", message: error.message || DEFAULT_MESSAGE };
  }

  return { category: "unknown", status: null, code: "UNKNOWN_ERROR", message: DEFAULT_MESSAGE };
}

/** The user-facing message for any caught error — never the raw exception, per `01_PRODUCT_VISION.md`'s API standard. */
export function getErrorMessage(error: unknown, fallback: string = DEFAULT_MESSAGE): string {
  const normalized = normalizeApiError(error);
  return normalized.message || fallback;
}
