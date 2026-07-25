import { NextResponse } from "next/server";

import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";
import { resolveSession } from "@/lib/auth/server-session";
import type { LoginResponse } from "@/features/auth/types/auth";

export async function GET() {
  try {
    const user = await resolveSession();

    if (!user) {
      return NextResponse.json(
        { error: { code: "NO_SESSION", message: "No active session." } },
        { status: 401 }
      );
    }

    const payload: LoginResponse = { user };
    return NextResponse.json(payload);
  } catch (error) {
    return authErrorResponse(error);
  }
}
