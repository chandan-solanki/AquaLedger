import type { ApiError, ApiErrorCategory } from "@/types/api";

/** Mirrors the backend's ErrorResponse/ErrorDetail shape (app/common/schemas.py). */
export interface BackendErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown> | null;
    field_errors?: Record<string, string[]> | null;
    request_id?: string | null;
  };
}

function categoryForStatus(status: number | undefined): ApiErrorCategory {
  switch (status) {
    case 401:
      return "unauthorized";
    case 403:
      return "forbidden";
    case 404:
      return "not_found";
    case 409:
      return "conflict";
    case 422:
      return "validation";
    default:
      if (status === undefined) return "network";
      if (status >= 500) return "server";
      return "unknown";
  }
}

/**
 * Builds a typed ApiError from an HTTP status + the backend's error
 * envelope. Shared by every place that talks to the backend — the client
 * Axios interceptor (api-client.ts) and the server-side fetch client
 * (lib/auth/backend-auth-client.ts) — so error classification never drifts
 * between the two transports.
 */
export function buildApiError(
  status: number,
  body: BackendErrorEnvelope | null | undefined
): ApiError {
  const detail = body?.error;

  return {
    category: categoryForStatus(status),
    status,
    code: detail?.code ?? "UNKNOWN_ERROR",
    message: detail?.message ?? "An unexpected error occurred.",
    fieldErrors: detail?.field_errors ?? undefined,
    requestId: detail?.request_id ?? null,
  };
}

/**
 * The inverse of buildApiError — used by BFF route handlers to re-emit an
 * ApiError as a response body, so the client's HTTP client (which expects
 * the same {error:{...}} envelope the real backend uses) parses BFF errors
 * identically to backend errors.
 */
export function apiErrorToEnvelope(error: ApiError): BackendErrorEnvelope {
  return {
    error: {
      code: error.code,
      message: error.message,
      field_errors: error.fieldErrors ?? null,
      request_id: error.requestId ?? null,
    },
  };
}

export function buildNetworkError(message: string, code = "NETWORK_ERROR"): ApiError {
  return {
    category: "network",
    status: null,
    code,
    message,
  };
}
