import { NextResponse, type NextRequest } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

/** Proxies GET /api/v1/fish-stock only - the backend resource is read-only (Sprint 15 Session 2), so no POST/PUT/DELETE handler exists here. */
export async function GET(request: NextRequest) {
  try {
    const data = await authenticatedBackendRequest(`/fish-stock${request.nextUrl.search}`);
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}
