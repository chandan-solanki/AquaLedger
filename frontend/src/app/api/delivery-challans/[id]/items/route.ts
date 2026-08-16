import { NextResponse } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

/**
 * Proxy to the backend's `GET/POST /delivery-challans/{id}/items` - backs
 * the Delivery Challan Detail page's Items table
 * (`delivery-challan-item-table.tsx`), mirroring
 * `app/api/purchase-orders/[id]/items/route.ts` exactly.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const data = await authenticatedBackendRequest(`/delivery-challans/${id}/items`);
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const body = await request.json();
    const data = await authenticatedBackendRequest(`/delivery-challans/${id}/items`, {
      method: "POST",
      body,
    });
    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    return authErrorResponse(error);
  }
}
