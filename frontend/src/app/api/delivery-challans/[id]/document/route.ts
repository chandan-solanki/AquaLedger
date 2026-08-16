import { NextResponse } from "next/server";

import { authenticatedBackendBinaryRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

/**
 * Binary proxy to the backend's `GET /delivery-challans/{id}/document` -
 * mirrors `app/api/purchase-orders/[id]/document/route.ts` exactly.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const backendResponse = await authenticatedBackendBinaryRequest(
      `/delivery-challans/${id}/document`
    );
    const body = await backendResponse.arrayBuffer();
    return new NextResponse(body, {
      status: backendResponse.status,
      headers: {
        "Content-Type": backendResponse.headers.get("content-type") ?? "application/octet-stream",
        "Content-Disposition": backendResponse.headers.get("content-disposition") ?? "attachment",
      },
    });
  } catch (error) {
    return authErrorResponse(error);
  }
}
