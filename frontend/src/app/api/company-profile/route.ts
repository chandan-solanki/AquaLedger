import { NextResponse, type NextRequest } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

export async function GET(_request: NextRequest) {
  try {
    const data = await authenticatedBackendRequest("/company-profile");
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const data = await authenticatedBackendRequest("/company-profile", { method: "PUT", body });
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}
