import { NextResponse, type NextRequest } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

export async function GET(request: NextRequest) {
  try {
    const data = await authenticatedBackendRequest(
      `/reports/fish-sales-history${request.nextUrl.search}`
    );
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}
