import { NextResponse, type NextRequest } from "next/server";

import { authenticatedBackendBinaryRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

/** Thin proxy for GET /reports/customer-statement (TASKS.md Sprint 11
 * Session 5 Phase C) - mirrors /api/reports/export's own binary
 * passthrough exactly: the backend's response here is PDF/Excel bytes,
 * not JSON. */
export async function GET(request: NextRequest) {
  try {
    const backendResponse = await authenticatedBackendBinaryRequest(
      `/reports/customer-statement${request.nextUrl.search}`
    );
    const body = await backendResponse.arrayBuffer();
    return new NextResponse(body, {
      status: backendResponse.status,
      headers: {
        "Content-Type": backendResponse.headers.get("content-type") ?? "application/octet-stream",
        "Content-Disposition":
          backendResponse.headers.get("content-disposition") ?? "attachment",
      },
    });
  } catch (error) {
    return authErrorResponse(error);
  }
}
