import "server-only";

import { cookies } from "next/headers";

import { ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE, REMEMBER_ME_COOKIE } from "@/lib/auth/cookie-names";

/**
 * HttpOnly cookies are the only place access/refresh tokens live — never
 * client-readable storage (07_FRONTEND_ARCHITECTURE.md §10, §20). Usable
 * only from Route Handlers and Server Actions here (next/headers's
 * cookies() specifically — middleware.ts reads the same cookie names via
 * NextRequest/NextResponse's own cookie API instead).
 */
const REFRESH_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7; // 7 days, matches backend refresh TTL

const baseCookieOptions = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "strict" as const,
  path: "/",
};

export interface SessionTokens {
  accessToken: string;
  refreshToken: string;
  expiresInSeconds: number;
  rememberMe: boolean;
}

export async function setSessionCookies({
  accessToken,
  refreshToken,
  expiresInSeconds,
  rememberMe,
}: SessionTokens): Promise<void> {
  const store = await cookies();

  store.set(ACCESS_TOKEN_COOKIE, accessToken, {
    ...baseCookieOptions,
    maxAge: expiresInSeconds,
  });

  store.set(REFRESH_TOKEN_COOKIE, refreshToken, {
    ...baseCookieOptions,
    // Omitting maxAge makes it a session cookie (cleared when the browser
    // closes) when the user didn't check "Remember me".
    ...(rememberMe ? { maxAge: REFRESH_TOKEN_MAX_AGE_SECONDS } : {}),
  });

  if (rememberMe) {
    store.set(REMEMBER_ME_COOKIE, "1", {
      ...baseCookieOptions,
      maxAge: REFRESH_TOKEN_MAX_AGE_SECONDS,
    });
  } else {
    store.delete(REMEMBER_ME_COOKIE);
  }
}

export async function getRememberMe(): Promise<boolean> {
  const store = await cookies();
  return store.get(REMEMBER_ME_COOKIE)?.value === "1";
}

export async function getAccessToken(): Promise<string | undefined> {
  const store = await cookies();
  return store.get(ACCESS_TOKEN_COOKIE)?.value;
}

export async function getRefreshToken(): Promise<string | undefined> {
  const store = await cookies();
  return store.get(REFRESH_TOKEN_COOKIE)?.value;
}

export async function clearSessionCookies(): Promise<void> {
  const store = await cookies();
  store.delete(ACCESS_TOKEN_COOKIE);
  store.delete(REFRESH_TOKEN_COOKIE);
  store.delete(REMEMBER_ME_COOKIE);
}

export async function hasAnySessionCookie(): Promise<boolean> {
  const store = await cookies();
  return store.has(ACCESS_TOKEN_COOKIE) || store.has(REFRESH_TOKEN_COOKIE);
}
