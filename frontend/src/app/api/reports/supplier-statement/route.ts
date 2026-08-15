import { NextResponse, type NextRequest } from "next/server";

import { authenticatedBackendBinaryRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

/** Thin proxy for GET /reports/supplier-statement (TASKS.md Sprint 11
 * Session 5 Phase C) - mirrors /api/reports/customer-statement exactly,
 * on the buy side. */
export async function GET(request: NextRequest) {
  try {
    const backendResponse = await authenticatedBackendBinaryRequest(
      `/reports/supplier-statement${request.nextUrl.search}`
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
