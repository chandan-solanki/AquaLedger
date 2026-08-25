import { NextResponse } from "next/server";

import { authenticatedBackendBinaryRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

/** Thin proxy for GET /payments/{id}/document - the backend's response
 * here is PDF bytes, not JSON, so this forwards the raw body plus its
 * Content-Type/Content-Disposition headers instead of calling
 * NextResponse.json(), mirroring /api/invoices/[id]/document's own
 * binary passthrough (Sprint 12 Session 2-4). */
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const backendResponse = await authenticatedBackendBinaryRequest(`/payments/${id}/document`);
    const body = await backendResponse.arrayBuffer();
    return new NextResponse(body, {
      status: backendResponse.status,
      headers: {
        "Content-Type": backendResponse.headers.get("content-type") ?? "application/octet-stream",
        "Content-Disposition":
          backendResponse.headers.get("content-disposition") ?? "attachment",
        // Every caller's URL is identical regardless of which receipt's PDF
        // they get back - an explicit signal so no browser/intermediate
        // cache reuses one tenant's receipt for another (mirrors
        // /api/company-profile/logo's Session 1 fix).
        "Cache-Control": "private, no-store",
      },
    });
  } catch (error) {
    return authErrorResponse(error);
  }
}
