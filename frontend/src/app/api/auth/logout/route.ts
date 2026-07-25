import { NextResponse } from "next/server";

import { backendLogout } from "@/lib/auth/backend-auth-client";
import { clearSessionCookies, getAccessToken, getRefreshToken } from "@/lib/auth/session-cookies";

export async function POST() {
  const accessToken = await getAccessToken();
  const refreshToken = await getRefreshToken();

  if (accessToken && refreshToken) {
    // Best-effort revoke — the browser's session is cleared regardless of
    // whether this succeeds; logout must never leave the client believing
    // it's still logged in (07_FRONTEND_ARCHITECTURE.md §10).
    await backendLogout(accessToken, refreshToken).catch(() => undefined);
  }

  await clearSessionCookies();
  return new NextResponse(null, { status: 204 });
}
