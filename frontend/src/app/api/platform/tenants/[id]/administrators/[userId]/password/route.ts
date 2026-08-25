import { NextResponse } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string; userId: string }> }
) {
  try {
    const { id, userId } = await params;
    const body = await request.json();
    const data = await authenticatedBackendRequest(
      `/platform/tenants/${id}/administrators/${userId}/password`,
      { method: "PATCH", body }
    );
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}
