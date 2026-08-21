import { NextResponse, type NextRequest } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ tripCatchId: string }> }
) {
  try {
    const { tripCatchId } = await params;
    const data = await authenticatedBackendRequest(
      `/invoices/trip-catches/${tripCatchId}/conflicts${request.nextUrl.search}`
    );
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}
