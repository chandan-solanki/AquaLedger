import "server-only";

import { env } from "@/config/env";
import { BackendAuthError, backendRefresh } from "@/lib/auth/backend-auth-client";
import {
  clearSessionCookies,
  getAccessToken,
  getRefreshToken,
  getRememberMe,
  setSessionCookies,
} from "@/lib/auth/session-cookies";
import { buildApiError, buildNetworkError, type BackendErrorEnvelope } from "@/lib/http-error";

export interface AuthenticatedBackendRequestInit {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
}

/** Builds the actual `RequestInit` from an access token - parameterized so
 * `performAuthenticatedRequest` can share its retry/refresh logic across
 * JSON, binary and (now) multipart form request shapes without each one
 * reimplementing that contract. */
type BuildRequestInit = (accessToken: string) => RequestInit;

function jsonRequestInit(init: AuthenticatedBackendRequestInit): BuildRequestInit {
  return (accessToken) => ({
    method: init.method ?? "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      ...(init.body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
    cache: "no-store",
  });
}

async function fetchBackend(path: string, buildInit: BuildRequestInit, accessToken: string): Promise<Response> {
  return fetch(`${env.NEXT_PUBLIC_API_URL}${path}`, buildInit(accessToken));
}

async function toBackendAuthError(response: Response): Promise<BackendAuthError> {
  const body = (await response.json().catch(() => null)) as BackendErrorEnvelope | null;
  return new BackendAuthError(buildApiError(response.status, body));
}

/** A 204 (DELETE's response) has no body - `.json()` would throw on the empty string. */
async function parseJsonBody<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/**
 * Forwards a request to the FastAPI backend with the caller's HttpOnly
 * access token, transparently rotating it once via the refresh cookie on a
 * 401 - the same silent-refresh contract `resolveSession` gives page loads
 * (`lib/auth/server-session.ts`), extended to business-data BFF routes
 * (companies, and every module after it) since the browser never holds a
 * bearer token to attach itself (ARCHITECTURE.md §1.2, §8.1).
 *
 * `parse` lets a caller consume the successful response differently -
 * `authenticatedBackendRequest` parses it as JSON (the shape every
 * existing BFF route needs); `authenticatedBackendBinaryRequest` returns
 * the raw `Response` instead (a report export's PDF/Excel/CSV bytes
 * aren't JSON) - both share this one retry/refresh implementation rather
 * than duplicating it.
 */
async function performAuthenticatedRequest<T>(
  path: string,
  buildInit: BuildRequestInit,
  parse: (response: Response) => Promise<T>
): Promise<T> {
  const accessToken = await getAccessToken();

  if (accessToken) {
    let response: Response;
    try {
      response = await fetchBackend(path, buildInit, accessToken);
    } catch (cause) {
      throw new BackendAuthError(
        buildNetworkError(cause instanceof Error ? cause.message : "Unable to reach the backend.")
      );
    }
    if (response.ok) return await parse(response);
    if (response.status !== 401) throw await toBackendAuthError(response);
  }

  const refreshToken = await getRefreshToken();
  if (!refreshToken) {
    await clearSessionCookies();
    throw new BackendAuthError(buildApiError(401, null));
  }

  let nextAccessToken: string;
  try {
    const rememberMe = await getRememberMe();
    const tokens = await backendRefresh(refreshToken);
    await setSessionCookies({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      expiresInSeconds: tokens.expires_in,
      rememberMe,
    });
    nextAccessToken = tokens.access_token;
  } catch (error) {
    await clearSessionCookies();
    if (error instanceof BackendAuthError) throw error;
    throw new BackendAuthError(buildNetworkError("Unable to refresh session."));
  }

  let retryResponse: Response;
  try {
    retryResponse = await fetchBackend(path, buildInit, nextAccessToken);
  } catch (cause) {
    throw new BackendAuthError(
      buildNetworkError(cause instanceof Error ? cause.message : "Unable to reach the backend.")
    );
  }
  if (!retryResponse.ok) {
    if (retryResponse.status === 401) await clearSessionCookies();
    throw await toBackendAuthError(retryResponse);
  }
  return await parse(retryResponse);
}

export async function authenticatedBackendRequest<T>(
  path: string,
  init: AuthenticatedBackendRequestInit = {}
): Promise<T> {
  return performAuthenticatedRequest(path, jsonRequestInit(init), parseJsonBody<T>);
}

/** Same auth/refresh/retry contract as `authenticatedBackendRequest`, but
 * returns the raw successful `Response` instead of parsing it as JSON -
 * for binary downloads (report export's PDF/Excel/CSV), whose caller
 * needs the response body as bytes plus its Content-Type/Content-
 * Disposition headers, not a parsed object. */
export async function authenticatedBackendBinaryRequest(
  path: string,
  init: AuthenticatedBackendRequestInit = {}
): Promise<Response> {
  return performAuthenticatedRequest(path, jsonRequestInit(init), async (response) => response);
}

/** Same auth/refresh/retry contract as `authenticatedBackendRequest`, for
 * the one shape those two don't cover: a multipart file upload (Sprint 14's
 * Company Profile logo, the first upload this codebase has needed). No
 * `Content-Type` header is set here - `fetch` derives
 * `multipart/form-data; boundary=...` itself from the `FormData` body, the
 * same reason `jsonRequestInit` only sets `Content-Type` when a JSON body
 * is actually present. */
export async function authenticatedBackendFormRequest<T>(path: string, formData: FormData): Promise<T> {
  return performAuthenticatedRequest(
    path,
    (accessToken) => ({
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}` },
      body: formData,
      cache: "no-store",
    }),
    parseJsonBody<T>
  );
}
