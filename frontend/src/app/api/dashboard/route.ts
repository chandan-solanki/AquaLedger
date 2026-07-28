import { NextResponse } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

export async function GET() {
  try {
    const data = await authenticatedBackendRequest("/dashboard");
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}
