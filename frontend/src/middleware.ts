import { NextResponse, type NextRequest } from "next/server";

import { ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE } from "@/lib/auth/cookie-names";

/**
 * Fast, cookie-presence-only pre-filter — protects by default (everything
 * not explicitly public redirects to /login) and keeps genuinely
 * unauthenticated visitors from even loading the app shell. This does NOT
 * validate the token; the authoritative check (with silent refresh) happens
 * client-side via AuthGuard -> /api/auth/session, since only Route Handlers
 * can rotate cookies (07_FRONTEND_ARCHITECTURE.md §4, §10).
 */
const PUBLIC_PATHS = ["/login"];

function hasSessionCookie(request: NextRequest): boolean {
  return request.cookies.has(ACCESS_TOKEN_COOKIE) || request.cookies.has(REFRESH_TOKEN_COOKIE);
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isPublicPath = PUBLIC_PATHS.includes(pathname);
  const authenticated = hasSessionCookie(request);

  if (!isPublicPath && !authenticated) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (isPublicPath && authenticated) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  // Everything except API routes, Next internals, and files with an
  // extension (static assets) — /api/auth/* must stay reachable while
  // logged out (it's how login itself happens).
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
