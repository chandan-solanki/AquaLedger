import { NextResponse } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

/**
 * Proxy to the backend's `GET /purchase-orders/{id}/purchase-bills`
 * (Sprint 12 Session 13) - backs the Purchase Order Detail page's "Purchase
 * Bills" section, mirroring `app/api/purchase-orders/[id]/items/route.ts`
 * exactly.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const data = await authenticatedBackendRequest(`/purchase-orders/${id}/purchase-bills`);
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}
