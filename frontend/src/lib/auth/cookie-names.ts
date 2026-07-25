/**
 * Cookie name constants only — no cookie I/O here. Shared between
 * session-cookies.ts (Route Handlers/Server Components, via next/headers)
 * and middleware.ts (via NextRequest/NextResponse's own cookie API, which
 * next/headers's cookies() isn't usable from) so the two never drift.
 */
export const ACCESS_TOKEN_COOKIE = "al_access_token";
export const REFRESH_TOKEN_COOKIE = "al_refresh_token";
export const REMEMBER_ME_COOKIE = "al_remember_me";
