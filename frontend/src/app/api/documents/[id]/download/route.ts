import { NextResponse } from "next/server";

import { authenticatedBackendBinaryRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

/** Thin proxy for GET /documents/{id}/download - the backend's response
 * here is the raw file's bytes, not JSON, so this forwards the raw body
 * plus its Content-Type/Content-Disposition headers instead of calling
 * NextResponse.json(), mirroring /api/payments/[id]/document's own binary
 * passthrough. */
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const backendResponse = await authenticatedBackendBinaryRequest(`/documents/${id}/download`);
    const body = await backendResponse.arrayBuffer();
    return new NextResponse(body, {
      status: backendResponse.status,
      headers: {
        "Content-Type": backendResponse.headers.get("content-type") ?? "application/octet-stream",
        "Content-Disposition":
          backendResponse.headers.get("content-disposition") ?? "attachment",
      },
    });
  } catch (error) {
    return authErrorResponse(error);
  }
}
