import { NextResponse } from "next/server";

import { backendLogin } from "@/lib/auth/backend-auth-client";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";
import { mapUserProfile } from "@/lib/auth/server-session";
import { setSessionCookies } from "@/lib/auth/session-cookies";
import type { LoginResponse } from "@/features/auth/types/auth";

interface LoginRequestBody {
  email?: unknown;
  password?: unknown;
  rememberMe?: unknown;
}

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as LoginRequestBody | null;

  if (typeof body?.email !== "string" || typeof body?.password !== "string") {
    return NextResponse.json(
      { error: { code: "VALIDATION_ERROR", message: "Email and password are required." } },
      { status: 422 }
    );
  }

  const rememberMe = body.rememberMe === true;

  try {
    const tokens = await backendLogin(body.email, body.password);

    await setSessionCookies({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      expiresInSeconds: tokens.expires_in,
      rememberMe,
    });

    const payload: LoginResponse = {
      user: mapUserProfile(tokens.user, tokens.must_change_password),
    };
    return NextResponse.json(payload);
  } catch (error) {
    return authErrorResponse(error);
  }
}
