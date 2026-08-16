import { NextResponse } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

/**
 * Proxy to the backend's `GET/PUT/DELETE /purchase-orders/{id}` - backs the
 * Purchase Orders feature's own Detail/Edit pages and the List page's
 * Delete action. Confirm/cancel/fulfill live on their own sibling routes.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const data = await authenticatedBackendRequest(`/purchase-orders/${id}`);
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}

export async function PUT(request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const body = await request.json();
    const data = await authenticatedBackendRequest(`/purchase-orders/${id}`, { method: "PUT", body });
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}

export async function DELETE(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    await authenticatedBackendRequest(`/purchase-orders/${id}`, { method: "DELETE" });
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    return authErrorResponse(error);
  }
}
