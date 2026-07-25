import "server-only";

import {
  BackendAuthError,
  backendGetMe,
  backendRefresh,
  type BackendUserProfile,
} from "@/lib/auth/backend-auth-client";
import {
  clearSessionCookies,
  getAccessToken,
  getRefreshToken,
  getRememberMe,
  setSessionCookies,
} from "@/lib/auth/session-cookies";
import type { User } from "@/features/auth/types/auth";

export function mapUserProfile(profile: BackendUserProfile, mustChangePassword = false): User {
  return {
    id: profile.id,
    tenantId: profile.tenant_id,
    email: profile.email,
    username: profile.username,
    fullName: profile.full_name,
    phone: profile.phone,
    status: profile.status,
    isSuperuser: profile.is_superuser,
    lastLoginAt: profile.last_login_at,
    roles: profile.roles,
    permissions: profile.permissions,
    // Only the login/refresh response carries this flag; /auth/me doesn't,
    // so a page-refresh session restore can't recover it and defaults to
    // false (the safer default — this session doesn't build the
    // change-password flow that would act on it anyway).
    mustChangePassword,
  };
}

function isUnauthorized(error: unknown): boolean {
  return error instanceof BackendAuthError && error.apiError.category === "unauthorized";
}

/**
 * Resolves the current session from the HttpOnly cookies: tries the access
 * token first, falls back to a silent refresh (rotating the refresh token)
 * on a 401, and only gives up — clearing cookies, returning null — when the
 * failure is itself an auth rejection rather than a transient/network error
 * (07_FRONTEND_ARCHITECTURE.md §10's Session Expiration flow).
 *
 * Callable only from Route Handlers / Server Actions — it may write cookies
 * on refresh, which Next.js forbids during a plain Server Component render.
 */
export async function resolveSession(): Promise<User | null> {
  const accessToken = await getAccessToken();

  if (accessToken) {
    try {
      const profile = await backendGetMe(accessToken);
      return mapUserProfile(profile);
    } catch (error) {
      if (!isUnauthorized(error)) throw error;
    }
  }

  const refreshToken = await getRefreshToken();
  if (!refreshToken) {
    await clearSessionCookies();
    return null;
  }

  try {
    const rememberMe = await getRememberMe();
    const tokens = await backendRefresh(refreshToken);
    await setSessionCookies({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      expiresInSeconds: tokens.expires_in,
      rememberMe,
    });
    return mapUserProfile(tokens.user, tokens.must_change_password);
  } catch (error) {
    if (!isUnauthorized(error)) throw error;
    await clearSessionCookies();
    return null;
  }
}
