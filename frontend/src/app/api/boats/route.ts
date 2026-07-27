import { NextResponse, type NextRequest } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

export async function GET(request: NextRequest) {
  try {
    const data = await authenticatedBackendRequest(`/boats${request.nextUrl.search}`);
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const data = await authenticatedBackendRequest("/boats", { method: "POST", body });
    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    return authErrorResponse(error);
  }
}
