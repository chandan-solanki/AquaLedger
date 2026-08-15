import { NextResponse, type NextRequest } from "next/server";

import { authenticatedBackendBinaryRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

/** Thin proxy for GET /reports/export - unlike every other reports BFF
 * route, the backend's response here is PDF/Excel/CSV bytes, not JSON, so
 * this forwards the raw body plus its Content-Type/Content-Disposition
 * headers instead of calling NextResponse.json() (TASKS.md Sprint 11
 * Session 5 Phase B). */
export async function GET(request: NextRequest) {
  try {
    const backendResponse = await authenticatedBackendBinaryRequest(
      `/reports/export${request.nextUrl.search}`
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
