import { NextResponse, type NextRequest } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

/**
 * Forwards to the existing POST /auth/change-password - password logic
 * stays owned by Auth (app/modules/auth); this route exists only so the
 * frontend's Profile feature has a `/api/profile/*` route matching every
 * other profile BFF route, not a second backend endpoint.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    await authenticatedBackendRequest("/auth/change-password", { method: "POST", body });
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    return authErrorResponse(error);
  }
}
