import { NextResponse, type NextRequest } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

/** Thin JSON proxy for GET /documents (list) - forwards every query param
 * through untouched, mirroring `/api/payments`'s own list proxy. The
 * Document Center is read-only, so unlike `/api/payments` there is no
 * POST handler here. */
export async function GET(request: NextRequest) {
  try {
    const data = await authenticatedBackendRequest(`/documents${request.nextUrl.search}`);
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}
