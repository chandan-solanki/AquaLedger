import "server-only";

import { env } from "@/config/env";
import { buildApiError, buildNetworkError, type BackendErrorEnvelope } from "@/lib/http-error";
import type { ApiError } from "@/types/api";
import type { AccountStatus } from "@/features/auth/types/auth";

/**
 * The ONLY module that talks to the real FastAPI backend for auth. Every
 * BFF route handler and the server-session resolver goes through here, so
 * there is exactly one place that knows the backend's auth request/response
 * shapes (07_FRONTEND_ARCHITECTURE.md §8: no duplicated request logic).
 */

// Raw backend shapes (snake_case), matching app/modules/auth/schemas.py exactly.
export interface BackendUserProfile {
  id: string;
  tenant_id: string;
  email: string;
  username: string;
  full_name: string;
  phone: string | null;
  status: AccountStatus;
  is_superuser: boolean;
  last_login_at: string | null;
  roles: string[];
  permissions: string[];
}

export interface BackendTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  must_change_password: boolean;
  user: BackendUserProfile;
}

export class BackendAuthError extends Error {
  constructor(public readonly apiError: ApiError) {
    super(apiError.message);
    this.name = "BackendAuthError";
  }
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${env.NEXT_PUBLIC_API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init.headers },
      cache: "no-store",
    });
  } catch (cause) {
    throw new BackendAuthError(
      buildNetworkError(cause instanceof Error ? cause.message : "Unable to reach the backend.")
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const body = (await response.json().catch(() => null)) as T | BackendErrorEnvelope | null;

  if (!response.ok) {
    throw new BackendAuthError(buildApiError(response.status, body as BackendErrorEnvelope | null));
  }

  return body as T;
}

export function backendLogin(email: string, password: string): Promise<BackendTokenResponse> {
  return request<BackendTokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function backendRefresh(refreshToken: string): Promise<BackendTokenResponse> {
  return request<BackendTokenResponse>("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export function backendLogout(accessToken: string, refreshToken: string): Promise<void> {
  return request<void>("/auth/logout", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export function backendGetMe(accessToken: string): Promise<BackendUserProfile> {
  return request<BackendUserProfile>("/auth/me", {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
