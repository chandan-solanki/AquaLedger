import { NextResponse, type NextRequest } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

/** Thin JSON proxy for GET /audit-logs (list) - forwards every query param
 * through untouched, mirroring `/api/documents`'s own list proxy. Audit
 * Logs is read-only, so there is no POST/PUT/DELETE handler here. */
export async function GET(request: NextRequest) {
  try {
    const data = await authenticatedBackendRequest(`/audit-logs${request.nextUrl.search}`);
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}
