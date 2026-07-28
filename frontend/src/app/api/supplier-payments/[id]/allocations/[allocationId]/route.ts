import { NextResponse } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string; allocationId: string }> }
) {
  try {
    const { id, allocationId } = await params;
    const body = await request.json();
    const data = await authenticatedBackendRequest(
      `/supplier-payments/${id}/allocations/${allocationId}`,
      { method: "PUT", body }
    );
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string; allocationId: string }> }
) {
  try {
    const { id, allocationId } = await params;
    await authenticatedBackendRequest(`/supplier-payments/${id}/allocations/${allocationId}`, {
      method: "DELETE",
    });
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    return authErrorResponse(error);
  }
}
