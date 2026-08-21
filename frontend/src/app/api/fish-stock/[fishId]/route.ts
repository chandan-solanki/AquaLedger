import { NextResponse } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

/** Proxies GET /api/v1/fish-stock/{fish_id} only - read-only resource. */
export async function GET(_request: Request, { params }: { params: Promise<{ fishId: string }> }) {
  try {
    const { fishId } = await params;
    const data = await authenticatedBackendRequest(`/fish-stock/${fishId}`);
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}
